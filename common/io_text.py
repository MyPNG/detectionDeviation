from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def normalize_spaces(value: Any) -> str:
    """Collapse repeated whitespace into a stable single-space form."""
    return " ".join(str(value).split()).strip()


def load_json(path: Path) -> Any:
    """Read JSON file and return parsed payload."""
    return json.loads(path.read_text(encoding="utf-8"))


def build_clause(article: Any, paragraph: Any) -> str:
    """Format clause label as ArtX(Y) when article/paragraph values are available."""
    article_str = normalize_spaces(article)
    paragraph_str = normalize_spaces(paragraph)
    if not article_str:
        return ""
    if paragraph_str:
        return f"Art{article_str}({paragraph_str})"
    return f"Art{article_str}"
