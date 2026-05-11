from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def build_reg_to_article_map(reg_metadata_json: Path) -> dict[str, str]:
    payload = json.loads(reg_metadata_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("REG metadata JSON must be a list.")

    mapping: dict[str, str] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        reg_id = str(row.get("ID", "")).strip().upper()
        article = str(row.get("Article", "")).strip().replace("Art", "")
        paragraph = str(row.get("Paragraph", "")).strip()
        if not reg_id or not article:
            continue
        mapping[reg_id] = f"Art{article}({paragraph})" if paragraph else f"Art{article}"
    return mapping


def normalize_references_in_file(json_path: Path, reg_to_article: dict[str, str]) -> bool:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return False

    changed = False
    for row in payload:
        if not isinstance(row, dict):
            continue
        refs = row.get("considered_references")
        if not isinstance(refs, list):
            continue
        new_refs: list[str] = []
        for ref in refs:
            ref_str = str(ref).strip()
            reg_key = ref_str.upper()
            if re.fullmatch(r"REG-\d+", reg_key):
                mapped = reg_to_article.get(reg_key, ref_str)
                new_refs.append(mapped)
                if mapped != ref_str:
                    changed = True
            else:
                new_refs.append(ref_str)
        if new_refs != refs:
            row["considered_references"] = new_refs
            changed = True

    if changed:
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return changed


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    goldstandard_root = project_root / "goldstandard"
    reg_metadata_json = project_root / "intermediate_results" / "reg" / "gdpr_requirements_with_additional_references.json"

    reg_to_article = build_reg_to_article_map(reg_metadata_json)
    json_files = sorted(goldstandard_root.rglob("*.json"))

    changed_files: list[Path] = []
    for json_file in json_files:
        if normalize_references_in_file(json_file, reg_to_article):
            changed_files.append(json_file)

    print(f"Scanned {len(json_files)} file(s). Updated {len(changed_files)} file(s).")
    for path in changed_files:
        print(f"Updated: {path}")


if __name__ == "__main__":
    main()

