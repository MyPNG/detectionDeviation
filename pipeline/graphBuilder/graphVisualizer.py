from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
from pyvis.network import Network


class graphVisualizer:
    """
    Visualize graph outputs created by RequirementsGraphBuilder.
    """

    def __init__(
        self,
        graphml_path: str | Path | None = None,
        graph_json_path: str | Path | None = None,
    ):
        self.graphml_path = Path(graphml_path).expanduser().resolve() if graphml_path else None
        self.graph_json_path = Path(graph_json_path).expanduser().resolve() if graph_json_path else None
        self.graph = nx.DiGraph()

    def _load_from_json(self, json_path: Path) -> nx.DiGraph:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        nodes = payload.get("nodes", [])
        edges = payload.get("edges", [])

        graph = nx.DiGraph()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue
            attrs = {k: v for k, v in node.items() if k != "id"}
            graph.add_node(node_id, **attrs)

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("source", "")).strip()
            target = str(edge.get("target", "")).strip()
            if not source or not target:
                continue
            attrs = {k: v for k, v in edge.items() if k not in {"source", "target"}}
            graph.add_edge(source, target, **attrs)
        return graph

    def load_graph(self) -> nx.DiGraph:
        if self.graphml_path and self.graphml_path.exists():
            self.graph = nx.read_graphml(self.graphml_path)
            return self.graph
        if self.graph_json_path and self.graph_json_path.exists():
            self.graph = self._load_from_json(self.graph_json_path)
            return self.graph
        raise FileNotFoundError("No graph input found. Provide an existing graphml_path or graph_json_path.")

    @staticmethod
    def _node_color(node_type: str) -> str:
        if node_type == "Provision":
            return "#2b6cb0"
        if node_type == "Article":
            return "#c53030"
        return "#4a5568"

    @staticmethod
    def _node_size(node_type: str) -> int:
        if node_type == "Provision":
            return 20
        if node_type == "Article":
            return 28
        return 16

    @staticmethod
    def _node_title(node_id: str, attrs: dict[str, Any]) -> str:
        lines = [f"id: {node_id}"]
        for key in sorted(attrs):
            lines.append(f"{key}: {attrs[key]}")
        return "\n".join(lines)

    def visualize(
        self,
        output_html_path: str | Path,
        max_nodes: int | None = None,
        max_edges: int | None = None,
    ) -> Path:
        if self.graph.number_of_nodes() == 0:
            self.load_graph()

        nodes_with_data = list(self.graph.nodes(data=True))
        edges_with_data = list(self.graph.edges(data=True))

        if max_nodes is not None and max_nodes > 0:
            nodes_with_data = nodes_with_data[:max_nodes]
            allowed_ids = {node_id for node_id, _ in nodes_with_data}
            edges_with_data = [
                (src, dst, attrs)
                for src, dst, attrs in edges_with_data
                if src in allowed_ids and dst in allowed_ids
            ]
        if max_edges is not None and max_edges > 0:
            edges_with_data = edges_with_data[:max_edges]

        net = Network(height="900px", width="100_20_4%", directed=True)

        for node_id, attrs in nodes_with_data:
            node_type = str(attrs.get("node_type", "")).strip()
            label = str(node_id)
            net.add_node(
                node_id,
                label=label,
                color=self._node_color(node_type),
                size=self._node_size(node_type),
                title=self._node_title(str(node_id), dict(attrs)),
            )

        for source, target, attrs in edges_with_data:
            relation = str(attrs.get("relation", "")).strip()
            net.add_edge(
                source,
                target,
                label=relation,
                title=f"relation: {relation}" if relation else "",
            )

        net.set_options(
            """
var options = {
  "physics": {
    "enabled": true,
    "solver": "barnesHut",
    "barnesHut": {
      "gravitationalConstant": -8000,
      "springLength": 180
    }
  }
}
"""
        )

        output = Path(output_html_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        net.write_html(str(output), open_browser=False, notebook=False)
        return output


def main() -> None:
    graphml_path = "/Users/my/Documents/projects/detectionDeviation/gdpr_clause/gdpr_requirements_graph.graphml"
    graph_json_path = "/intermediate_results/reg/gdpr_requirements_graph.json"
    output_html = "/Users/my/Documents/projects/detectionDeviation/gdpr_clause/gdpr_requirements_graph.html"

    visualizer = graphVisualizer(
        graphml_path=graphml_path,
        graph_json_path=graph_json_path,
    )
    graph = visualizer.load_graph()
    saved_html = visualizer.visualize(output_html_path=output_html)
    print(f"Nodes: {graph.number_of_nodes()} Edges: {graph.number_of_edges()}")
    print(f"Saved visualization: {saved_html}")


if __name__ == "__main__":
    main()
