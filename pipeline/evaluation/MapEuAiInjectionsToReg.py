from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _normalize_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\s+", " ", text)
    return text


def _reg_sort_key(reg_id: str) -> tuple[int, str]:
    m = re.search(r"(\d+)$", reg_id)
    if not m:
        return (10**9, reg_id)
    return (int(m.group(1)), reg_id)


def _clause(article: Any, paragraph: Any) -> str:
    a = str(article or "").strip()
    p = str(paragraph or "").strip()
    return f"Art{a}({p})" if p else f"Art{a}"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def update_injections_with_requirements(
    injections_json: str | Path,
    requirements_json: str | Path,
    output_json: str | Path | None = None,
) -> dict[str, Any]:
    injections_path = Path(injections_json).expanduser().resolve()
    requirements_path = Path(requirements_json).expanduser().resolve()
    save_path = Path(output_json).expanduser().resolve() if output_json else injections_path

    injections = _load_json(injections_path)
    requirements = _load_json(requirements_path)

    if not isinstance(injections, list):
        raise ValueError(f"Expected list in {injections_path}")
    if not isinstance(requirements, list):
        raise ValueError(f"Expected list in {requirements_path}")

    indexed_reqs: list[dict[str, str]] = []
    for row in requirements:
        if not isinstance(row, dict):
            continue
        reg_id = str(row.get("ID", "")).strip()
        text = str(row.get("Text", "")).strip()
        article = row.get("Article", "")
        paragraph = row.get("Paragraph", "")
        if not reg_id or not text:
            continue
        indexed_reqs.append(
            {
                "reg_id": reg_id,
                "clause": _clause(article, paragraph),
                "text": text,
                "norm": _normalize_text(text),
            }
        )

    updated_count = 0
    unmatched_count = 0
    for item in injections:
        if not isinstance(item, dict):
            continue
        regulatory_text = str(item.get("regulatory_text", "")).strip()
        norm_reg = _normalize_text(regulatory_text)
        if not norm_reg:
            item["reg_id"] = ""
            item["clause"] = ""
            unmatched_count += 1
            continue

        matches: list[tuple[str, str]] = []
        for req in indexed_reqs:
            norm_req = req["norm"]
            # Main rule: regulatory text inside requirement text.
            # Also allow reverse containment for split or shortened units.
            if norm_reg in norm_req or norm_req in norm_reg:
                matches.append((req["reg_id"], req["clause"]))

        # Deduplicate while preserving stable sorted order by REG id.
        unique = sorted(set(matches), key=lambda pair: (_reg_sort_key(pair[0]), pair[1]))
        reg_ids = [pair[0] for pair in unique]
        clauses = [pair[1] for pair in unique]

        if reg_ids:
            item["reg_id"] = " | ".join(reg_ids)
            item["clause"] = " | ".join(clauses)
            updated_count += 1
        else:
            item["reg_id"] = ""
            item["clause"] = ""
            unmatched_count += 1

        # Keep schema minimal: only top-level reg_id/clause are needed.
        item.pop("matched_reg_ids", None)
        item.pop("matched_clauses", None)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(json.dumps(injections, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "saved_to": str(save_path),
        "total_items": len(injections),
        "updated_items": updated_count,
        "unmatched_items": unmatched_count,
        "requirements_used": len(indexed_reqs),
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    injections_json = project_root / "goldstandard" / "eu_ai_injections.json"
    requirements_json = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements.json"
    result = update_injections_with_requirements(
        injections_json=injections_json,
        requirements_json=requirements_json,
        output_json=injections_json,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
