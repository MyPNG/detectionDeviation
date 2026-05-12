from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class GraphTraversal:
    """
    Build prompt-oriented REG graph context from reranked REA retrieval outputs.

    Main flow:
    - take top-k reranked REG candidates
    - deduplicate them by REG id
    - treat them as main constraints
    - expand graph context around each main constraint using controlled edge rules

    Traversal semantics:
    - AND: bidirectional
    - REFERENCES: outgoing only
    - SEQUENCE: bidirectional
    - PARENT_CHILD:
      - parent -> children
      - child -> parent
      - special case: if the main node is a child and its parent is included,
        expand that parent to its children too, even though those sibling nodes
        are effectively 2 hops away from the main node
    - OR and BELONGS_TO are intentionally excluded from prompt graph context
    """

    ALLOWED_RELATIONS = {"AND", "REFERENCES", "SEQUENCE", "PARENT_CHILD"}

    def __init__(self, graph_json_path: str | Path):
        self.graph_json_path = Path(graph_json_path).expanduser().resolve()
        self.node_by_id: dict[str, dict[str, Any]] = {}
        self.out_edges_by_source: dict[str, list[dict[str, str]]] = {}
        self.in_edges_by_target: dict[str, list[dict[str, str]]] = {}
        self._load_graph()

    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _split_relations(raw_relation: Any) -> list[str]:
        relation = str(raw_relation).strip()
        if not relation:
            return []
        return [part.strip().upper() for part in relation.split("|") if part.strip()]

    @staticmethod
    def _build_clause(article: Any, paragraph: Any) -> str:
        article_str = " ".join(str(article or "").split()).strip()
        paragraph_str = " ".join(str(paragraph or "").split()).strip()
        if not article_str:
            return ""
        if paragraph_str:
            return f"Art{article_str}({paragraph_str})"
        return f"Art{article_str}"

    @staticmethod
    def _sort_top_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def _key(row: dict[str, Any]) -> tuple[int, float]:
            rank_raw = row.get("rerank rank", "")
            try:
                rank = int(rank_raw)
            except Exception:
                rank = 10**9
            score_raw = row.get("rerank score", row.get("similarity score", 0.0))
            try:
                score = float(score_raw)
            except Exception:
                score = 0.0
            return rank, -score

        return sorted(matches, key=_key)

    def _load_graph(self) -> None:
        payload = json.loads(self.graph_json_path.read_text(encoding="utf-8"))
        nodes = payload.get("nodes", []) if isinstance(payload, dict) else []
        edges = payload.get("edges", []) if isinstance(payload, dict) else []
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError(f"Graph JSON must contain list fields 'nodes' and 'edges': {self.graph_json_path}")

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = self._normalize_spaces(node.get("id", ""))
            if not node_id:
                continue
            self.node_by_id[node_id] = node

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = self._normalize_spaces(edge.get("source", ""))
            target = self._normalize_spaces(edge.get("target", ""))
            if not source or not target:
                continue
            for relation in self._split_relations(edge.get("relation", "")):
                edge_row = {
                    "source": source,
                    "target": target,
                    "relation": relation,
                }
                self.out_edges_by_source.setdefault(source, []).append(edge_row)
                self.in_edges_by_target.setdefault(target, []).append(edge_row)

    def _is_textual_reg_node(self, node_id: str) -> bool:
        row = self.node_by_id.get(node_id, {})
        node_type = self._normalize_spaces(row.get("node_type", ""))
        text = self._normalize_spaces(row.get("text", ""))
        return bool(node_id.startswith("REG-") and node_type == "Provision" and text)

    def _build_node_context(
        self,
        main_id: str,
        neighbor_id: str,
        edge_type: str,
        direction: str,
        hop_count: int,
        relation_path: str,
    ) -> dict[str, Any]:
        row = self.node_by_id.get(neighbor_id, {})
        article = self._normalize_spaces(row.get("article", row.get("article_number", "")))
        paragraph = self._normalize_spaces(row.get("paragraph", ""))
        return {
            "id": neighbor_id,
            "main_reg_id": main_id,
            "edge_type": edge_type,
            "direction": direction,
            "hop_count": hop_count,
            "relation_path": relation_path,
            "text": self._normalize_spaces(row.get("text", "")),
            "article": article,
            "paragraph": paragraph,
            "clause": self._build_clause(article, paragraph),
        }

    def _extract_main_constraints(self, reranked_payload: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        matches = reranked_payload.get("top matches", [])
        if not isinstance(matches, list):
            matches = []

        sorted_matches = self._sort_top_matches([row for row in matches if isinstance(row, dict)])
        out: list[dict[str, Any]] = []
        seen: set[str] = set()

        for row in sorted_matches:
            reg_id = self._normalize_spaces(row.get("ID", ""))
            if not reg_id or reg_id in seen:
                continue
            seen.add(reg_id)
            graph_row = self.node_by_id.get(reg_id, {})
            out.append(
                {
                    "id": reg_id,
                    "clause": self._normalize_spaces(row.get("article", "")),
                    "text": self._normalize_spaces(
                        graph_row.get("text", row.get("text", ""))
                    ),
                    "rerank_rank": row.get("rerank rank"),
                    "rerank_score": row.get("rerank score"),
                    "similarity_score": row.get("similarity score"),
                }
            )
            if len(out) >= max(1, top_k):
                break

        return out

    def _collect_direct_neighbors(
        self,
        main_id: str,
        max_hop: int,
        globally_visited: set[str],
        local_seen: set[tuple[str, str, str, int]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        contexts: list[dict[str, Any]] = []
        parent_ids: list[str] = []

        if max_hop < 1:
            return contexts, parent_ids

        for edge in self.out_edges_by_source.get(main_id, []):
            relation = edge["relation"]
            if relation not in self.ALLOWED_RELATIONS:
                continue
            if relation not in {"AND", "REFERENCES", "SEQUENCE", "PARENT_CHILD"}:
                continue
            neighbor_id = edge["target"]
            if not self._is_textual_reg_node(neighbor_id):
                continue
            signature = (main_id, neighbor_id, relation, 1)
            if signature in local_seen or neighbor_id in globally_visited:
                continue
            local_seen.add(signature)
            globally_visited.add(neighbor_id)
            contexts.append(
                self._build_node_context(
                    main_id=main_id,
                    neighbor_id=neighbor_id,
                    edge_type=relation,
                    direction="outgoing",
                    hop_count=1,
                    relation_path=f"{main_id} -> {neighbor_id}",
                )
            )

        for edge in self.in_edges_by_target.get(main_id, []):
            relation = edge["relation"]
            if relation not in self.ALLOWED_RELATIONS:
                continue
            if relation not in {"AND", "SEQUENCE", "PARENT_CHILD"}:
                continue
            neighbor_id = edge["source"]
            if not self._is_textual_reg_node(neighbor_id):
                continue
            signature = (neighbor_id, main_id, relation, 1)
            if signature in local_seen or neighbor_id in globally_visited:
                continue
            local_seen.add(signature)
            globally_visited.add(neighbor_id)
            contexts.append(
                self._build_node_context(
                    main_id=main_id,
                    neighbor_id=neighbor_id,
                    edge_type=relation,
                    direction="incoming",
                    hop_count=1,
                    relation_path=f"{neighbor_id} -> {main_id}",
                )
            )
            if relation == "PARENT_CHILD":
                parent_ids.append(neighbor_id)

        return contexts, parent_ids

    def _collect_parent_child_siblings(
        self,
        main_id: str,
        parent_ids: list[str],
        globally_visited: set[str],
        local_seen: set[tuple[str, str, str, int]],
    ) -> list[dict[str, Any]]:
        """
        Special case:
        if the main node is a child and its parent is reached, also expand
        that parent to its children. This can surface sibling constraints
        that are effectively 2 hops from the main node.
        """
        contexts: list[dict[str, Any]] = []

        for parent_id in parent_ids:
            for edge in self.out_edges_by_source.get(parent_id, []):
                if edge["relation"] != "PARENT_CHILD":
                    continue
                child_id = edge["target"]
                if child_id == main_id:
                    continue
                if not self._is_textual_reg_node(child_id):
                    continue
                signature = (parent_id, child_id, "PARENT_CHILD", 2)
                if signature in local_seen or child_id in globally_visited:
                    continue
                local_seen.add(signature)
                globally_visited.add(child_id)
                contexts.append(
                    self._build_node_context(
                        main_id=main_id,
                        neighbor_id=child_id,
                        edge_type="PARENT_CHILD",
                        direction="via_parent_outgoing",
                        hop_count=2,
                        relation_path=f"{main_id} <- {parent_id} -> {child_id}",
                    )
                )

        return contexts

    def build_graph_context_for_reranked(
        self,
        reranked_json_path: str | Path,
        top_k: int = 9,
        max_hop: int = 1,
    ) -> dict[str, Any]:
        reranked_path = Path(reranked_json_path).expanduser().resolve()
        payload = json.loads(reranked_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Reranked JSON must be an object: {reranked_path}")

        rea_sub_id = self._normalize_spaces(payload.get("id", ""))
        main_constraints = self._extract_main_constraints(payload, top_k=max(1, top_k))

        globally_visited: set[str] = set()
        main_blocks: list[dict[str, Any]] = []

        for main in main_constraints:
            main_id = self._normalize_spaces(main.get("id", ""))
            if not main_id:
                continue

            already_visited = main_id in globally_visited
            if not already_visited:
                globally_visited.add(main_id)

            local_seen: set[tuple[str, str, str, int]] = set()
            graph_context: list[dict[str, Any]] = []

            if not already_visited:
                one_hop, parent_ids = self._collect_direct_neighbors(
                    main_id=main_id,
                    max_hop=max_hop,
                    globally_visited=globally_visited,
                    local_seen=local_seen,
                )
                graph_context.extend(one_hop)
                if parent_ids:
                    graph_context.extend(
                        self._collect_parent_child_siblings(
                            main_id=main_id,
                            parent_ids=parent_ids,
                            globally_visited=globally_visited,
                            local_seen=local_seen,
                        )
                    )

            main_blocks.append(
                {
                    "id": main_id,
                    "clause": main.get("clause", ""),
                    "text": main.get("text", ""),
                    "rerank_rank": main.get("rerank_rank"),
                    "rerank_score": main.get("rerank_score"),
                    "similarity_score": main.get("similarity_score"),
                    "already_visited_before_expansion": already_visited,
                    "graph_context": graph_context,
                }
            )

        return {
            "rea_sub_id": rea_sub_id,
            "reranked_json": str(reranked_path),
            "top_k": max(1, top_k),
            "max_hop": max(0, int(max_hop)),
            "allowed_relations": sorted(self.ALLOWED_RELATIONS),
            "main_constraints": main_blocks,
            "visited_reg_ids": sorted(globally_visited),
        }

    def save_graph_context_for_reranked(
        self,
        reranked_json_path: str | Path,
        output_json_path: str | Path,
        top_k: int = 9,
        max_hop: int = 1,
    ) -> Path:
        output_path = Path(output_json_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.build_graph_context_for_reranked(
            reranked_json_path=reranked_json_path,
            top_k=top_k,
            max_hop=max_hop,
        )
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def process_reranked_root(
        self,
        reranked_root: str | Path,
        output_root: str | Path,
        top_k: int = 9,
        max_hop: int = 1,
    ) -> dict[str, Any]:
        reranked_dir = Path(reranked_root).expanduser().resolve()
        out_root = Path(output_root).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        if not reranked_dir.exists() or not reranked_dir.is_dir():
            raise FileNotFoundError(f"Reranked root not found or not a directory: {reranked_dir}")

        reranked_files = sorted(
            path for path in reranked_dir.rglob("*.json")
            if path.is_file() and not path.name.endswith("_prompt.json")
        )

        outputs: list[dict[str, Any]] = []
        for reranked_file in reranked_files:
            relative_parent = reranked_file.parent.relative_to(reranked_dir)
            out_dir = out_root / relative_parent / reranked_file.stem
            out_dir.mkdir(parents=True, exist_ok=True)
            output_json = out_dir / "step3_graph_context.json"
            try:
                saved = self.save_graph_context_for_reranked(
                    reranked_json_path=reranked_file,
                    output_json_path=output_json,
                    top_k=top_k,
                    max_hop=max_hop,
                )
                outputs.append(
                    {
                        "input_reranked_json": str(reranked_file),
                        "relative_path": str(reranked_file.relative_to(reranked_dir)),
                        "output_json": str(saved),
                    }
                )
            except Exception as exc:
                outputs.append(
                    {
                        "input_reranked_json": str(reranked_file),
                        "relative_path": str(reranked_file.relative_to(reranked_dir)),
                        "error": str(exc),
                    }
                )

        return {
            "reranked_root": str(reranked_dir),
            "output_root": str(out_root),
            "top_k": max(1, top_k),
            "max_hop": max(0, int(max_hop)),
            "file_count": len(reranked_files),
            "outputs": outputs,
        }


def main() -> None:
    # -------------------------------
    # Edit config here (code-first)
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    reg_input_name = "reg_for_injectiontest"

    # Required: set this to either a reranked folder or one reranked json file.
    input_path = project_root / "intermediate_outputs" / "artifact_01_rea_with_injections__reg_for_injectiontest_reranked"

    # Optional:
    # - For folder input: set an output root dir (or leave None for default).
    # - For file input: set an output json file (or leave None for default).
    output_path: Path | None = None

    # Traversal knobs
    top_k = 3
    max_hop = 1

    # Optional: override graph path directly. If None, auto-resolve from project defaults.
    graph_json_path: Path | None = None

    def _resolve_graph_json() -> Path:
        if graph_json_path is not None:
            path = Path(graph_json_path).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(f"graph_json not found: {path}")
            return path

        candidate_primary = (
            project_root
            / "intermediate_results"
            / reg_input_name
            / f"{reg_input_name}_requirements_graph.json"
        )
        if candidate_primary.exists():
            return candidate_primary

        fallback_candidates = [
            project_root / "intermediate_results" / "reg_for_injectiontest" / "reg_for_injectiontest_requirements_graph.json",
            project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_graph.json",
        ]
        for path in fallback_candidates:
            if path.exists():
                return path

        discovered = sorted((project_root / "intermediate_results").rglob("*requirements_graph.json"))
        if len(discovered) == 1:
            return discovered[0].resolve()
        if discovered:
            raise FileNotFoundError(
                "Multiple graph JSON files found; set graph_json_path explicitly. "
                f"Candidates: {[str(p) for p in discovered[:8]]}"
            )
        raise FileNotFoundError("No graph JSON found. Run REG graph builder first.")

    graph_path = _resolve_graph_json()
    traversal = GraphTraversal(graph_path)
    input_path = Path(input_path).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_dir():
        output_root = (
            Path(output_path).expanduser().resolve()
            if output_path is not None
            else project_root / "intermediate_outputs" / f"graph_context_{input_path.name}"
        )
        result = traversal.process_reranked_root(
            reranked_root=input_path,
            output_root=output_root,
            top_k=max(1, top_k),
            max_hop=max(0, max_hop),
        )
        print(
            json.dumps(
                {
                    "graph_json": str(graph_path),
                    "input_root": str(input_path),
                    "output_root": str(output_root),
                    "top_k": max(1, top_k),
                    "max_hop": max(0, max_hop),
                    "file_count": result.get("file_count", 0),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    output_json = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else input_path.with_name(f"{input_path.stem}_graph_context.json")
    )
    saved = traversal.save_graph_context_for_reranked(
        reranked_json_path=input_path,
        output_json_path=output_json,
        top_k=max(1, top_k),
        max_hop=max(0, max_hop),
    )
    print(
        json.dumps(
            {
                "graph_json": str(graph_path),
                "input_json": str(input_path),
                "output_json": str(saved),
                "top_k": max(1, top_k),
                "max_hop": max(0, max_hop),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
