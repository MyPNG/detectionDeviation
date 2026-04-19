from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import TypedDict


class GDPRClause(TypedDict):
    id: str
    text: str
    article: str
    location: str
    type: str


LINE_PATTERN = re.compile(r"^(REG-\d+)\s+\[(Art\.\s*\d+(?:\([^)]*\))*)[^\]]*\]\s*(.+)$")
LOCATION_PATTERN = re.compile(r"^Art\.\s*(\d+)((?:\([^)]*\))*)$")
REF_PATTERN = re.compile(r"\s*\[Ref:[^\]]+\]")


def discover_dataset_files(dataset_root: Path) -> list[Path]:
    preferred_patterns = ("**/dataset_*.txt", "**/dataset_*txt")
    candidates = {
        file_path
        for pattern in preferred_patterns
        for file_path in dataset_root.glob(pattern)
        if file_path.is_file()
    }

    if not candidates:
        # Fallback for repositories where datasets are not named with dataset_*txt.
        candidates = {
            file_path
            for file_path in dataset_root.rglob("*")
            if file_path.is_file() and (file_path.suffix == ".txt" or file_path.name.endswith("_txt"))
        }

    return sorted(candidates)


def infer_clause_type(location_suffix: str) -> str:
    parts = re.findall(r"\(([^)]+)\)", location_suffix)
    if not parts:
        return "article"

    last_part = parts[-1].strip()
    if re.fullmatch(r"[A-Za-z]+", last_part):
        return "point"
    return "paragraph"


def parse_line(raw_line: str) -> GDPRClause | None:
    line = raw_line.strip()
    if not line.startswith("REG-"):
        return None

    match = LINE_PATTERN.match(line)
    if not match:
        return None

    reg_id, raw_location, raw_text = match.groups()
    location_match = LOCATION_PATTERN.match(raw_location)
    if not location_match:
        return None

    article_number, suffix = location_match.groups()
    clean_text = REF_PATTERN.sub("", raw_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    article = f"Art{article_number}"
    location = f"{article}{suffix}"

    return GDPRClause(
        id=reg_id,
        text=clean_text,
        article=article,
        location=location,
        type=infer_clause_type(suffix),
    )


def extract_clauses(files: list[Path]) -> list[GDPRClause]:
    clauses: list[GDPRClause] = []
    seen: set[tuple[str, str, str]] = set()

    for file_path in files:
        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            clause = parse_line(raw_line)
            if clause is None:
                continue

            key = (clause["id"], clause["location"], clause["text"])
            if key in seen:
                continue

            seen.add(key)
            clauses.append(clause)

    return clauses


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    default_input_file = root / "datasets" / "reg" / "test_data" / "test_5_6_13_14.txt"

    parser = argparse.ArgumentParser(description="Build GDPR clauses JSON from dataset text files.")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=default_input_file,
        help="Specific dataset text file to parse (preferred when available).",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=root / "datasets",
        help="Directory containing dataset text files (fallback discovery).",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=root / "gdpr_clause" / "gdpr_clauses.json",
        help="Path to generated JSON file.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_file: Path = args.input_file
    input_root: Path = args.input_root
    output_file: Path = args.output_file

    if input_file and input_file.is_file():
        dataset_files = [input_file]
    else:
        dataset_files = discover_dataset_files(input_root)

    clauses = extract_clauses(dataset_files)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(clauses, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Found {len(dataset_files)} dataset file(s).")
    print(f"Extracted {len(clauses)} clause(s).")
    print(f"Saved JSON to: {output_file}")


if __name__ == "__main__":
    main()
