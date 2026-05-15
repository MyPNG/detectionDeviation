from __future__ import annotations

from typing import Any


class DeonticModalDetection:
    """
    Modal anchor detection and deontic force mapping.
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation for behavior-preserving delegation."""
        self.legacy = legacy

    def find_modal_anchor(self, text: str) -> dict[str, Any]:
        """Detect the strongest modal anchor phrase in text."""
        return self.legacy._find_modal_anchor(text)

    def detect_deontic_from_text(self, text: str) -> str:
        """Map raw text to deontic force label."""
        return self.legacy._detect_deontic_from_text(text)

    def detect_deontic_from_anchor(self, anchor_phrase: str) -> str:
        """Map anchor phrase to deontic force label."""
        return self.legacy._detect_deontic_from_anchor(anchor_phrase)

    def normalize_stage1_modal_phrases(self, text: str) -> str:
        """Normalize modal phrase variants in stage1 outputs."""
        return self.legacy._normalize_stage1_modal_phrases(text)
