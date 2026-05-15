from __future__ import annotations

from typing import Any


class DeonticSplitting:
    """
    Clause/sentence/action splitting and connector-based subject handling.
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation for behavior-preserving delegation."""
        self.legacy = legacy

    def has_explicit_subject_before_modal(self, text: str, modal_terms: list[str]) -> bool:
        """Check whether subject is explicitly present before modal anchor."""
        return self.legacy._has_explicit_subject_before_modal(text, modal_terms)

    def inject_missing_subject_for_connector_rows(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        """Inject inherited subject for connector-led rows when missing."""
        return self.legacy._inject_missing_subject_for_connector_rows(rows)

    def resolve_anaphora_in_chain(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve anaphora across a chain of adjacent nodes."""
        return self.legacy._resolve_anaphora_in_chain(nodes)
