from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import networkx as nx


ARTICLE_REF_RE = re.compile(r"^Art\s*(\d+)", flags=re.IGNORECASE)
FULL_REF_RE = re.compile(r"^Art\s*(\d+)((?:\([^)]*\))*)$", flags=re.IGNORECASE)


class RequirementsGraphBuilder:
    """
    Build a lightweight GDPR requirements graph.

    Node types:
    - Provision (REG-xxx)
    - Article (ArtX)

    Edge types:
    - BELONGS_TO: Provision -> Article
    - REFERENCES: Provision -> (Provision | Article)
    - PARENT_CHILD: Parent provision -> Child provision
    - SEQUENCE / AND / OR: Provision -> Provision (logic relations)
    """

    def __init__(self, requirements_json_path: str | Path):
        self.requirements_json_path = Path(requirements_json_path).expanduser().resolve()
        self.graph = nx.DiGraph()

    @staticmethod
    def _normalize_article_number(value: Any) -> str:
        text = str(value).strip()
        match = re.search(r"\d+", text)
        if not match:
            return text
        return str(int(match.group(0)))

    @staticmethod
    def _normalize_paragraph(value: Any) -> str:
        return str(value).strip()

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

    def _build_system_name(self, article_number: str, paragraph: str) -> str:
        if paragraph:
            return f"Art{article_number}({paragraph})"
        return f"Art{article_number}"

    def _ensure_article_node(self, article_number: str) -> str:
        article_id = f"Art{article_number}"
        if not self.graph.has_node(article_id):
            self.graph.add_node(
                article_id,
                node_type="Article",
                article_number=article_number,
            )
        return article_id

    def _add_provision_node(self, item: dict[str, Any]) -> tuple[str, str]:
        provision_id = str(item.get("ID", "")).strip()
        article_number = self._normalize_article_number(item.get("Article", ""))
        paragraph = self._normalize_paragraph(item.get("Paragraph", ""))
        text = str(item.get("Text", "")).strip()
        system_name = self._build_system_name(article_number, paragraph)

        self.graph.add_node(
            provision_id,
            node_type="Provision",
            article=article_number,
            paragraph=paragraph,
            text=text,
            system_name=system_name,
        )
        return provision_id, system_name

    def _add_relation_edge(self, source: str, target: str, relation: str) -> None:
        """
        Keep one directed edge per node pair in DiGraph while preserving
        multiple semantic relation types in a pipe-separated relation field.
        """
        if not source or not target or source == target:
            return
        if not self.graph.has_node(source) or not self.graph.has_node(target):
            return

        relation = str(relation).strip().upper()
        if not relation:
            return

        existing = self.graph.get_edge_data(source, target, default={}) or {}
        existing_rel = str(existing.get("relation", "")).strip()
        rels = {r for r in existing_rel.split("|") if r} if existing_rel else set()
        rels.add(relation)
        self.graph.add_edge(source, target, relation="|".join(sorted(rels)))

    def _load_requirements(self) -> list[dict[str, Any]]:
        payload = json.loads(self.requirements_json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Input JSON must be an array of requirement objects.")
        out: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                out.append(item)
        return out

    def build_graph(self) -> nx.DiGraph:
        requirements = self._load_requirements()

        # Map system_name -> provision node ids to resolve references.
        system_name_to_provisions: dict[str, list[str]] = {}

        # Pass 1: add provision + article nodes + BELONGS_TO edges.
        for item in requirements:
            provision_id, system_name = self._add_provision_node(item)
            article_number = self._normalize_article_number(item.get("Article", ""))
            article_id = self._ensure_article_node(article_number)
            self._add_relation_edge(provision_id, article_id, "BELONGS_TO")
            system_name_to_provisions.setdefault(system_name, []).append(provision_id)

        # Pass 2: add REFERENCES edges.
        for item in requirements:
            source_id = str(item.get("ID", "")).strip()
            references = item.get("references", [])
            if not isinstance(references, list):
                continue

            for raw_ref in references:
                canonical_ref = self._canonical_reference(str(raw_ref))
                if not canonical_ref:
                    continue

                target_provisions = system_name_to_provisions.get(canonical_ref, [])
                if target_provisions:
                    for target_id in target_provisions:
                        self._add_relation_edge(source_id, target_id, "REFERENCES")
                    continue

                article_target = self._article_id_from_reference(canonical_ref)
                if article_target is None:
                    continue
                if not self.graph.has_node(article_target):
                    article_number = article_target.replace("Art", "", 1)
                    self._ensure_article_node(article_number)
                self._add_relation_edge(source_id, article_target, "REFERENCES")

        # Pass 3: add PARENT_CHILD + logical edges (SEQUENCE/AND/OR).
        valid_logic = {"SEQUENCE", "AND", "OR"}
        for item in requirements:
            source_id = str(item.get("ID", "")).strip()
            if not source_id:
                continue

            parent = str(item.get("parent", "")).strip()
            if parent and parent.lower() != "none":
                self._add_relation_edge(parent, source_id, "PARENT_CHILD")

            children = item.get("children", [])
            if isinstance(children, list):
                for child in children:
                    child_id = str(child).strip()
                    if child_id:
                        self._add_relation_edge(source_id, child_id, "PARENT_CHILD")

            logic_relations = item.get("logic_relations", [])
            if not isinstance(logic_relations, list):
                continue
            for rel in logic_relations:
                if not isinstance(rel, dict):
                    continue
                rel_type = str(rel.get("type", "")).strip().upper()
                target_id = str(rel.get("target", "")).strip()
                if rel_type in valid_logic and target_id:
                    self._add_relation_edge(source_id, target_id, rel_type)

        return self.graph

    def save_graph_graphml(self, output_path: str | Path) -> Path:
        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(self.graph, output)
        return output

    def save_graph_json(self, output_path: str | Path) -> Path:
        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [
                {"id": node_id, **attrs}
                for node_id, attrs in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": src, "target": dst, **attrs}
                for src, dst, attrs in self.graph.edges(data=True)
            ],
        }
        output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return output


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    reg_input_name = "reg_for_injectiontest"
    input_json = (
        project_root
        / "intermediate_results"
        / "01_preprocessing"
        / "reg_prep"
        / "01_extracting"
        / "requirementsextractor"
        / reg_input_name
        / f"{reg_input_name}_requirements_extended.json"
    )
    output_graphml = (
        project_root
        / "intermediate_results"
        / "01_preprocessing"
        / "reg_prep"
        / "03_graphbuilder"
        / "requirementsgraphbuilder"
        / reg_input_name
        / f"{reg_input_name}_requirements_graph.graphml"
    )
    output_json = output_graphml.with_suffix(".json")

    builder = RequirementsGraphBuilder(input_json)
    graph = builder.build_graph()
    graphml_path = builder.save_graph_graphml(output_graphml)
    json_path = builder.save_graph_json(output_json)

    print(f"Nodes: {graph.number_of_nodes()} Edges: {graph.number_of_edges()}")
    print(f"Saved GraphML: {graphml_path}")
    print(f"Saved JSON: {json_path}")


if __name__ == "__main__":
    main()
