from __future__ import annotations

from typing import Any


class DeonticTextNormalization:
    """
    Normalize/cleanup helpers, placeholder cleanup, and shared regex utilities.
    Delegates to legacy implementation to preserve behavior.
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation for behavior-preserving delegation."""
        self.legacy = legacy

    def normalize_text(self, value: str) -> str:
        """Normalize free text with legacy tokenizer/whitespace rules."""
        return self.legacy._normalize_text(value)

    def tokenize_words(self, value: str) -> set[str]:
        """Tokenize text to normalized word set for overlap checks."""
        return self.legacy._tokenize_words(value)

    def normalize_slot_rows(
        self,
        raw_rows: list[dict[str, Any]],
        expected_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Normalize and align slot rows against expected REG IDs."""
        return self.legacy._normalize_slot_rows(raw_rows, expected_ids)

    def build_group_source_vocab(self, group: dict[str, Any]) -> set[str]:
        """Build source vocabulary for invented-word audits."""
        return self.legacy._build_group_source_vocab(group)

    def annotate_invented_words(
        self,
        rows: list[dict[str, Any]],
        source_vocab: set[str],
    ) -> list[dict[str, Any]]:
        """Annotate invented/new words by comparing row text against source vocab."""
        return self.legacy._annotate_invented_words(rows, source_vocab)
