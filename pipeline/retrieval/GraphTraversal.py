from __future__ import annotations

import csv
import json
import re
from collections import deque
from pathlib import Path
from typing import Any


ARTICLE_REF_RE = re.compile(r"^Art\s*(\d+)", flags=re.IGNORECASE)
FULL_REF_RE = re.compile(r"^Art\s*(\d+)((?:\([^)]*\))*)$", flags=re.IGNORECASE)


class GraphTraversal:
    """
    Traverse REG reference graph from REA retrieval entry points.
    """

    def __init__(self, reg_json_path: str | Path):
        self.reg_json_path = Path(reg_json_path).expanduser().resolve()
        self.reg_by_id: dict[str, dict[str, Any]] = {}
        self.system_name_to_reg_ids: dict[str, list[str]] = {}
        self.article_to_reg_ids: dict[str, list[str]] = {}
        self._load_reg_nodes()

    @staticmethod
    def _norm_spaces(value: str) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _canonical_reference(value: str) -> str | None:
        cleaned = str(value).strip().replace(" ", "")
        if not cleaned:
            return None
        match = FULL_REF_RE.match(cleaned)
        if not match:
            return None
        article_number, suffix = match.groups()
        return f"Art{int(article_number)}{suffix}"

    @staticmethod
    def _article_id_from_reference(reference: str) -> str | None:
        match = ARTICLE_REF_RE.match(reference)
        if not match:
            return None
        return f"Art{int(match.group(1))}"

    @staticmethod
    def _build_system_name(article: str, paragraph: str) -> str:
        article_number = str(article).replace("Art", "").strip()
        paragraph_value = str(paragraph).strip()
        return f"Art{article_number}({paragraph_value})" if paragraph_value else f"Art{article_number}"

    def _load_reg_nodes(self) -> None:
        payload = json.loads(self.reg_json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("REG JSON must be a list.")

        for item in payload:
            if not isinstance(item, dict):
                continue
            reg_id = self._norm_spaces(str(item.get("ID", "")))
            if not reg_id:
                continue
            article = self._norm_spaces(str(item.get("Article", "")))
            paragraph = self._norm_spaces(str(item.get("Paragraph", "")))
            text = self._norm_spaces(str(item.get("Text", "")))
            references_raw = item.get("references", [])
            references = [self._norm_spaces(str(ref)) for ref in references_raw] if isinstance(references_raw, list) else []

            reg_row = {
                "ID": reg_id,
                "Article": article,
                "Paragraph": paragraph,
                "Text": text,
                "references": references,
                "system_name": self._build_system_name(article, paragraph),
            }
            self.reg_by_id[reg_id] = reg_row

            self.system_name_to_reg_ids.setdefault(reg_row["system_name"], []).append(reg_id)
            article_key = f"Art{str(article).replace('Art', '').strip()}"
            self.article_to_reg_ids.setdefault(article_key, []).append(reg_id)

    def _resolve_reference_targets(self, reference: str) -> list[str]:
        canonical_ref = self._canonical_reference(reference)
        if canonical_ref is None:
            return []

        # 1) exact provision match
        exact = self.system_name_to_reg_ids.get(canonical_ref, [])
        if exact:
            return list(dict.fromkeys(exact))

        # 2) paragraph-level prefix (ArtX(Y) -> all ArtX(Y)(...)) if such nodes exist
        if "(" in canonical_ref:
            prefixed: list[str] = []
            prefix = canonical_ref + "("
            for system_name, reg_ids in self.system_name_to_reg_ids.items():
                if system_name.startswith(prefix):
                    prefixed.extend(reg_ids)
            if prefixed:
                return list(dict.fromkeys(prefixed))

        # 3) article-level fallback
        article_id = self._article_id_from_reference(canonical_ref)
        if article_id is None:
            return []
        return list(dict.fromkeys(self.article_to_reg_ids.get(article_id, [])))

    @staticmethod
    def _extract_entry_points(file_payload: dict[str, Any]) -> list[str]:
        matches = file_payload.get("top matches", [])
        if not isinstance(matches, list):
            return []
        out: list[str] = []
        for row in matches:
            if not isinstance(row, dict):
                continue
            reg_id = str(row.get("ID", "")).strip()
            if reg_id:
                out.append(reg_id)
        return out

    @staticmethod
    def _extract_entry_points_from_reg_main_csv(csv_path: Path) -> list[str]:
        if not csv_path.exists():
            return []
        out: list[str] = []
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                reg_id = str(row.get("reg_id", "")).strip()
                if reg_id:
                    out.append(reg_id)
        return out

    def _traverse_from_entry_points(self, entry_points: list[str], max_hop: int) -> tuple[set[str], list[dict[str, Any]]]:
        visited: set[str] = set()
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        queue: deque[tuple[str, int]] = deque()

        for entry_id in entry_points:
            if entry_id not in self.reg_by_id:
                continue
            if entry_id in visited:
                continue
            visited.add(entry_id)
            queue.append((entry_id, 0))

        while queue:
            source_id, hop = queue.popleft()
            if hop >= max_hop:
                continue

            source_row = self.reg_by_id.get(source_id)
            if source_row is None:
                continue
            references = source_row.get("references", [])
            if not isinstance(references, list):
                continue

            for ref in references:
                for target_id in self._resolve_reference_targets(str(ref)):
                    edge_key = (source_id, "REFERENCES", target_id)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append(
                            {
                                "source": source_id,
                                "relation": "REFERENCES",
                                "target": target_id,
                                "hop_from_source": hop + 1,
                                "reference": str(ref),
                            }
                        )

                    if target_id in visited:
                        continue
                    visited.add(target_id)
                    queue.append((target_id, hop + 1))

        return visited, edges

    def process_artifact_chunks(
        self,
        artifact_01_dir: str | Path,
        artifact_02_dir: str | Path,
        max_hop: int = 1,
    ) -> dict[str, Any]:
        if max_hop < 0:
            raise ValueError("max_hop must be >= 0")

        input_root = Path(artifact_01_dir).expanduser().resolve()
        output_root = Path(artifact_02_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)

        chunk_dirs = sorted(path for path in input_root.iterdir() if path.is_dir())
        outputs: list[dict[str, Any]] = []

        for chunk_dir in chunk_dirs:
            # Prefer curated main clauses from CSV for each chunk.
            reg_main_csv = chunk_dir / "reg_main_clauses.csv"
            all_entry_points = self._extract_entry_points_from_reg_main_csv(reg_main_csv)
            entry_source = "reg_main_clauses.csv"

            # Fallback to JSON-based entry extraction only if CSV is unavailable/empty.
            if not all_entry_points:
                entry_source = "rea_top_matches_json"
                for file_path in sorted(chunk_dir.glob("*.json")):
                    payload = json.loads(file_path.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict):
                        continue
                    all_entry_points.extend(self._extract_entry_points(payload))

            visited_nodes, relationship_edges = self._traverse_from_entry_points(all_entry_points, max_hop=max_hop)

            text_nodes = []
            for reg_id in sorted(visited_nodes):
                row = self.reg_by_id.get(reg_id)
                if row is None:
                    continue
                text_nodes.append(
                    {
                        "ID": row["ID"],
                        "Article": row["Article"],
                        "Paragraph": row["Paragraph"],
                        "Text": row["Text"],
                        "system_name": row["system_name"],
                    }
                )

            chunk_output_dir = output_root / chunk_dir.name
            chunk_output_dir.mkdir(parents=True, exist_ok=True)
            relationships_path = chunk_output_dir / "subgraph_relationships.json"
            texts_path = chunk_output_dir / "subgraph_texts.json"

            relationships_payload = {
                "chunk": chunk_dir.name,
                "entry_source": entry_source,
                "max_hop": max_hop,
                "entry_points_count": len(all_entry_points),
                "visited_nodes_count": len(visited_nodes),
                "relationships": relationship_edges,
            }
            texts_payload = {
                "chunk": chunk_dir.name,
                "max_hop": max_hop,
                "visited_nodes_count": len(visited_nodes),
                "nodes": text_nodes,
            }

            relationships_path.write_text(json.dumps(relationships_payload, indent=2, ensure_ascii=False), encoding="utf-8")
            texts_path.write_text(json.dumps(texts_payload, indent=2, ensure_ascii=False), encoding="utf-8")

            outputs.append(
                {
                    "chunk": chunk_dir.name,
                    "entry_source": entry_source,
                    "relationships_file": str(relationships_path),
                    "texts_file": str(texts_path),
                    "visited_nodes_count": len(visited_nodes),
                    "relationships_count": len(relationship_edges),
                }
            )

        return {
            "artifact_01_dir": str(input_root),
            "artifact_02_dir": str(output_root),
            "chunk_count": len(chunk_dirs),
            "max_hop": max_hop,
            "outputs": outputs,
        }


def main() -> None:
    reg_json = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/reg/gdpr_requirements_with_additional_references.json"
    #artifact_01 = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01"
    #artifact_02 = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_02"

    #artifact_01 = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_reranked"
    #artifact_02 = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_02_reranked"

    artifact_01 = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_reranked_100"
    artifact_02 = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_02_reranked_100"

    traversal = GraphTraversal(reg_json)
    result = traversal.process_artifact_chunks(
        artifact_01_dir=artifact_01,
        artifact_02_dir=artifact_02,
        max_hop=1,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
