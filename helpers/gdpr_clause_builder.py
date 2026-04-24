from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from collections import defaultdict
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gdpr_compliance.concept_extractor import extract_concepts
from gdpr_compliance.reference_resolver import extract_precise_references
from gdpr_compliance.schema import normalize_clause_record


class GDPRClause(TypedDict):
    id: str
    text: str
    article: str
    location: str
    type: str
    concepts: list[str]
    actors: list[str]
    modality: str
    references: list[str]
    reference_clause_ids: list[str]


LINE_PATTERN = re.compile(r"^(REG-\d+)\s+\[(Art\.\s*\d+(?:\([^)]*\))*)[^\]]*\]\s*(.+)$")
LOCATION_PATTERN = re.compile(r"^Art\.\s*(\d+)((?:\([^)]*\))*)$")
REF_PATTERN = re.compile(r"\s*\[Ref:[^\]]+\]")
REG_AND_LOCATION_PATTERN = re.compile(r"^(REG-\d+)\s+\[(Art\.\s*\d+(?:\([^)]*\))*)", flags=re.IGNORECASE)


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


def _reference_to_article_root(reference: str) -> str | None:
    match = re.match(r"^Art(\d+)", reference)
    if not match:
        return None
    return f"Art{int(match.group(1))}"


def _canonical_location(raw_location: str) -> str | None:
    location_match = LOCATION_PATTERN.match(raw_location)
    if not location_match:
        return None
    article_number, suffix = location_match.groups()
    return f"Art{int(article_number)}{suffix}"


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


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
    references = extract_precise_references(
        clean_text,
        {
            "id": reg_id,
            "article": article,
            "location": location,
        },
    )
    concepts = extract_concepts(clean_text)

    normalized = normalize_clause_record(
        {
            "id": reg_id,
            "text": clean_text,
            "article": article,
            "location": location,
            "type": infer_clause_type(suffix),
            "concepts": concepts,
        }
    )
    return GDPRClause(
        id=reg_id,
        text=normalized.text,
        article=normalized.article,
        location=normalized.location,
        type=normalized.type,
        concepts=normalized.concepts,
        actors=normalized.actors,
        modality=normalized.modality,
        references=references,
        reference_clause_ids=[],
    )


def build_article_to_clause_ids(clauses: list[GDPRClause]) -> dict[str, list[str]]:
    article_to_clause_ids: dict[str, list[str]] = defaultdict(list)
    for clause in clauses:
        article_to_clause_ids[clause["article"]].append(clause["id"])
    return article_to_clause_ids


def build_location_to_clause_ids(clauses: list[GDPRClause]) -> dict[str, list[str]]:
    location_to_clause_ids: dict[str, list[str]] = defaultdict(list)
    for clause in clauses:
        location_to_clause_ids[clause["location"]].append(clause["id"])
    return location_to_clause_ids


def load_external_indexes(paths: list[Path]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    article_to_clause_ids: dict[str, list[str]] = defaultdict(list)
    location_to_clause_ids: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line.startswith("REG-"):
                continue
            match = REG_AND_LOCATION_PATTERN.match(line)
            if not match:
                continue
            reg_id, raw_location = match.groups()
            canonical_location = _canonical_location(raw_location)
            if canonical_location is None:
                continue
            article = _reference_to_article_root(canonical_location)
            if article is None:
                continue
            article_to_clause_ids[article].append(reg_id)
            location_to_clause_ids[canonical_location].append(reg_id)

    # Ensure deterministic ordering and deduplication.
    normalized_article_index = {article: _dedupe_keep_order(ids) for article, ids in article_to_clause_ids.items()}
    normalized_location_index = {loc: _dedupe_keep_order(ids) for loc, ids in location_to_clause_ids.items()}
    return normalized_article_index, normalized_location_index


def _resolve_reference_targets(
    reference: str,
    article_index: dict[str, list[str]],
    location_index: dict[str, list[str]],
    exclude_clause_id: str | None = None,
) -> list[str]:
    # 1) Exact location match (best precision).
    exact_targets = location_index.get(reference, [])
    if exclude_clause_id is not None:
        exact_targets = [reg_id for reg_id in exact_targets if reg_id != exclude_clause_id]
    if exact_targets:
        return _dedupe_keep_order(exact_targets)

    # 2) Prefix location match for paragraph-level refs, e.g. Art49(1) -> Art49(1)(a)/(b)/...
    if "(" in reference:
        prefixed_targets: list[str] = []
        prefix = f"{reference}("
        for location, reg_ids in location_index.items():
            if location.startswith(prefix):
                prefixed_targets.extend(reg_ids)
        if exclude_clause_id is not None:
            prefixed_targets = [reg_id for reg_id in prefixed_targets if reg_id != exclude_clause_id]
        if prefixed_targets:
            return _dedupe_keep_order(prefixed_targets)

    # 3) Article-level fallback.
    article_root = _reference_to_article_root(reference)
    if not article_root:
        return []

    article_targets = article_index.get(article_root, [])
    if exclude_clause_id is not None:
        article_targets = [reg_id for reg_id in article_targets if reg_id != exclude_clause_id]
    return _dedupe_keep_order(article_targets)


def resolve_reference_clause_ids(
    clauses: list[GDPRClause],
    local_article_index: dict[str, list[str]],
    local_location_index: dict[str, list[str]],
    external_article_index: dict[str, list[str]],
    external_location_index: dict[str, list[str]],
) -> None:
    for clause in clauses:
        targets: list[str] = []
        for reference in clause.get("references", []):
            local_targets = _resolve_reference_targets(
                reference=reference,
                article_index=local_article_index,
                location_index=local_location_index,
                exclude_clause_id=clause["id"],
            )
            if local_targets:
                targets.extend(local_targets)
                continue

            # Fallback: resolve from external cleaned corpus when article missing in local JSON scope.
            targets.extend(
                _resolve_reference_targets(
                    reference=reference,
                    article_index=external_article_index,
                    location_index=external_location_index,
                )
            )

        clause["reference_clause_ids"] = _dedupe_keep_order(targets)


def discover_sentence_files(dataset_root: Path) -> list[Path]:
    return sorted(
        {
            file_path
            for file_path in dataset_root.rglob("sentences_cleaned.txt")
            if file_path.is_file()
        }
    )


def extract_clauses(files: list[Path], external_reference_files: list[Path] | None = None) -> list[GDPRClause]:
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

    local_article_index = build_article_to_clause_ids(clauses)
    local_location_index = build_location_to_clause_ids(clauses)
    external_article_index, external_location_index = load_external_indexes(external_reference_files or [])
    resolve_reference_clause_ids(
        clauses=clauses,
        local_article_index=local_article_index,
        local_location_index=local_location_index,
        external_article_index=external_article_index,
        external_location_index=external_location_index,
    )

    return clauses


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    default_input_file = root / "datasets" / "reg" / "test_data" / "test_reg.txt"

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
    parser.add_argument(
        "--sentences-file",
        type=Path,
        default=None,
        help="Optional explicit sentences_cleaned.txt for fallback cross-reference resolution.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_file: Path = args.input_file
    input_root: Path = args.input_root
    output_file: Path = args.output_file
    sentences_file: Path | None = args.sentences_file

    if input_file and input_file.is_file():
        dataset_files = [input_file]
    else:
        dataset_files = discover_dataset_files(input_root)

    if sentences_file is not None:
        external_reference_files = [sentences_file]
    else:
        external_reference_files = discover_sentence_files(input_root)
        if not external_reference_files:
            external_reference_files = discover_sentence_files(ROOT / "datasets")

    clauses = extract_clauses(dataset_files, external_reference_files=external_reference_files)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(clauses, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Found {len(dataset_files)} dataset file(s).")
    print(f"Extracted {len(clauses)} clause(s).")
    print(f"Loaded {len(external_reference_files)} fallback reference source file(s).")
    print(f"Saved JSON to: {output_file}")


if __name__ == "__main__":
    main()
