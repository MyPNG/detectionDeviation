from __future__ import annotations

from pathlib import Path
from typing import Any


class DeonticStage4Slots:
    """
    Stage 4 slot extraction:
    rule-first + LLM fallback hybrid.
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation for behavior-preserving delegation."""
        self.legacy = legacy

    def extract_slots_for_group(self, group: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract slot rows for a grouped article/paragraph unit."""
        return self.legacy.extract_slots_for_group(group)

    def run(self, input_json: str | Path, output_json: str | Path) -> Path:
        """Run full stage4 extraction on input JSON and save output report."""
        return self.legacy.run(input_json=input_json, output_json=output_json)
