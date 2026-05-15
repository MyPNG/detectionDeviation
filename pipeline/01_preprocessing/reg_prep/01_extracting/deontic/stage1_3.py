from __future__ import annotations

from pathlib import Path
from typing import Any


class DeonticStage13:
    """
    Stage 1-3 pipeline:
    - anaphora + missing actor normalization
    - passive->active conversion
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation for behavior-preserving delegation."""
        self.legacy = legacy

    def resolve_anaphora_and_missing_actor(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run stage1 normalization: anaphora + missing actor resolution."""
        return self.legacy.resolve_anaphora_and_missing_actor(nodes)

    def make_passive_to_active(self, nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Run stage3 passive->active conversion."""
        return self.legacy.make_passive_to_active(nodes)

    def make_passive_to_active_two_calls(self, nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Run stage3 conversion with two-call fallback strategy."""
        return self.legacy.make_passive_to_active_two_calls(nodes)

    def run_passive_active_pipeline_on_file(self, input_json: str | Path, output_json: str | Path) -> Path:
        """Execute stage1-3 file-level pipeline and persist report."""
        return self.legacy.run_passive_active_pipeline_on_file(input_json=input_json, output_json=output_json)

    def test_passive_to_active(self, output_json: str | Path | None = None) -> dict[str, Any]:
        """Run built-in passive->active test harness."""
        return self.legacy.test_passive_to_active(output_json=output_json)
