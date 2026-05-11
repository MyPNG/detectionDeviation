from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def normalize_chunk_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())


def load_target_policy_chunk_text(requirements_json: Path) -> str:
    payload = json.loads(requirements_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list in: {requirements_json}")

    parts: list[str] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        text = " ".join(str(row.get("text", "")).split()).strip()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def index_rea_chunk_dirs(rea_root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for chunk_dir in sorted(path for path in rea_root.iterdir() if path.is_dir()):
        key = normalize_chunk_name(chunk_dir.name)
        if key:
            mapping[key] = chunk_dir
    return mapping


def find_requirements_json_for_chunk(gold_chunk_dir: Path, rea_index: dict[str, Path]) -> Path | None:
    key = normalize_chunk_name(gold_chunk_dir.name)
    rea_chunk_dir = rea_index.get(key)
    if rea_chunk_dir is None:
        return None

    preferred = rea_chunk_dir / f"{rea_chunk_dir.name}_requirements.json"
    if preferred.exists():
        return preferred

    candidates = sorted(rea_chunk_dir.glob("*_requirements.json"))
    return candidates[0] if candidates else None


def create_chunk_text_files(
    goldstandard_root: Path,
    rea_intermediate_root: Path,
    output_filename: str = "target_policy_chunk.txt",
) -> tuple[list[Path], list[str]]:
    saved_files: list[Path] = []
    warnings: list[str] = []

    rea_index = index_rea_chunk_dirs(rea_intermediate_root)
    gold_chunks = sorted(path for path in goldstandard_root.iterdir() if path.is_dir())

    for gold_chunk in gold_chunks:
        req_json = find_requirements_json_for_chunk(gold_chunk, rea_index)
        if req_json is None:
            warnings.append(f"No matching requirements JSON found for: {gold_chunk}")
            continue

        chunk_text = load_target_policy_chunk_text(req_json)
        out_path = gold_chunk / output_filename
        out_path.write_text(chunk_text + "\n", encoding="utf-8")
        saved_files.append(out_path)

    return saved_files, warnings


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    goldstandard_root = project_root / "goldstandard"
    rea_intermediate_root = project_root / "intermediate_results" / "rea"

    saved_files, warnings = create_chunk_text_files(
        goldstandard_root=goldstandard_root,
        rea_intermediate_root=rea_intermediate_root,
        output_filename="target_policy_chunk.txt",
    )

    print(f"Created {len(saved_files)} chunk text file(s).")
    for file_path in saved_files:
        print(f"Saved: {file_path}")

    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings:
            print(warning)


if __name__ == "__main__":
    main()
