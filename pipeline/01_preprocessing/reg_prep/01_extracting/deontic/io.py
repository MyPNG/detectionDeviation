from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DeonticIO:
    """
    JSON/report/path helpers plus direct I/O delegation to legacy extractor.
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation used for behavior-preserving delegation."""
        self.legacy = legacy

    @staticmethod
    def resolve_path(path: str | Path) -> Path:
        """Resolve path to absolute expanded path."""
        return Path(path).expanduser().resolve()

    @staticmethod
    def ensure_parent(path: Path) -> None:
        """Ensure parent directory exists before writing."""
        path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def load_json(path: str | Path) -> Any:
        """Load JSON payload from disk."""
        p = DeonticIO.resolve_path(path)
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def save_json(path: str | Path, payload: Any) -> Path:
        """Write JSON payload to disk and return resolved output path."""
        p = DeonticIO.resolve_path(path)
        DeonticIO.ensure_parent(p)
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    def load_requirements(self, input_json: str | Path) -> list[dict[str, Any]]:
        """Delegate requirements loading to legacy parser."""
        return self.legacy._load_requirements(self.resolve_path(input_json))

    def group_by_article_paragraph(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Delegate grouping logic to legacy extractor."""
        return self.legacy._group_by_article_paragraph(rows)

    def build_pipeline_nodes_from_group(self, group: dict[str, Any]) -> list[dict[str, Any]]:
        """Delegate node-building logic to legacy extractor."""
        return self.legacy._build_pipeline_nodes_from_group(group)

    def write_report(self, output_path: str | Path, payload: Any) -> Path:
        """Write a report JSON artifact."""
        return self.save_json(output_path, payload)
