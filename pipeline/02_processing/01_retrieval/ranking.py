from __future__ import annotations

from typing import Any


def get_top_matches_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated top-match candidate rows from a reranked payload."""
    matches = payload.get("top matches", [])
    if not isinstance(matches, list):
        return []
    return [row for row in matches if isinstance(row, dict)]


def sort_top_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort candidates by rerank rank and fallback score (descending)."""
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


def get_sorted_top_matches_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract + sort top-match candidates from reranked payload."""
    return sort_top_matches(get_top_matches_from_payload(payload))
