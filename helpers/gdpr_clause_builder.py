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
REF_CONTENT_PATTERN = re.compile(r"\[Ref:\s*([^\]]+?)\]", flags=re.IGNORECASE)
ARTICLE_FROM_REF_CONTENT_PATTERN = re.compile(r"\bArticle\s+(\d+)(\([^)]*\))?", flags=re.IGNORECASE)
ARTICLE_LIST_PATTERN = re.compile(
    r"\bArticle(?:s)?\s+((?:\d+(?:\([^)]*\))?(?:\s*(?:,|and|or)\s*)?)+)",
    flags=re.IGNORECASE,
)
ARTICLE_DIRECT_PATTERN = re.compile(r"\bArticle\s+(\d+(?:\([^)]*\))*)", flags=re.IGNORECASE)
ART_DIRECT_PATTERN = re.compile(r"\bArt\.?\s*(\d+(?:\([^)]*\))*)", flags=re.IGNORECASE)
REF_TOKEN_PATTERN = re.compile(r"\d+(?:\([^)]*\))*")
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


def _canonical_article_ref(article_number: str, suffix: str = "") -> str:
    return f"Art{int(article_number)}{suffix.replace(' ', '')}"


def _reference_to_article_root(reference: str) -> str | None:
    match = re.match(r"^Art(\d+)", reference)
    if not match:
        return None
    return f"Art{int(match.group(1))}"


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _drop_generic_refs_when_specific_exists(references: list[str]) -> list[str]:
    specific_roots = {
        root
        for reference in references
        if "(" in reference
        for root in [_reference_to_article_root(reference)]
        if root
    }
    filtered: list[str] = []
    for reference in references:
        root = _reference_to_article_root(reference)
        if root and "(" not in reference and root in specific_roots:
            continue
        filtered.append(reference)
    return filtered


def extract_references(raw_text: str, clean_text: str) -> list[str]:
    refs: list[str] = []

    # 1) Explicit inline [Ref: Article X Context] tags.
    for content in REF_CONTENT_PATTERN.findall(raw_text):
        for article_number, suffix in ARTICLE_FROM_REF_CONTENT_PATTERN.findall(content):
            refs.append(_canonical_article_ref(article_number, suffix))

    # 2) In-text Article lists, e.g. "Article 46 or 47".
    for list_payload in ARTICLE_LIST_PATTERN.findall(clean_text):
        for token in REF_TOKEN_PATTERN.findall(list_payload):
            number_match = re.match(r"^(\d+)((?:\([^)]*\))*)$", token)
            if not number_match:
                continue
            article_number, suffix = number_match.groups()
            refs.append(_canonical_article_ref(article_number, suffix))

    # 3) In-text direct mentions, e.g. "Article 49(1)" or "Art. 6(1)".
    for token in ARTICLE_DIRECT_PATTERN.findall(clean_text):
        number_match = re.match(r"^(\d+)((?:\([^)]*\))*)$", token)
        if not number_match:
            continue
        article_number, suffix = number_match.groups()
        refs.append(_canonical_article_ref(article_number, suffix))

    for token in ART_DIRECT_PATTERN.findall(clean_text):
        number_match = re.match(r"^(\d+)((?:\([^)]*\))*)$", token)
        if not number_match:
            continue
        article_number, suffix = number_match.groups()
        refs.append(_canonical_article_ref(article_number, suffix))

    return _drop_generic_refs_when_specific_exists(_dedupe_keep_order(refs))


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
    references = extract_references(raw_text=raw_text, clean_text=clean_text)

    article = f"Art{article_number}"
    location = f"{article}{suffix}"
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


def load_external_article_index(paths: list[Path]) -> dict[str, list[str]]:
    article_to_clause_ids: dict[str, list[str]] = defaultdict(list)
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
            location_match = LOCATION_PATTERN.match(raw_location)
            if not location_match:
                continue
            article_number, _ = location_match.groups()
            article = f"Art{int(article_number)}"
            article_to_clause_ids[article].append(reg_id)

    # Ensure deterministic ordering and deduplication.
    return {article: _dedupe_keep_order(ids) for article, ids in article_to_clause_ids.items()}


def resolve_reference_clause_ids(
    clauses: list[GDPRClause],
    local_article_index: dict[str, list[str]],
    external_article_index: dict[str, list[str]],
) -> None:
    for clause in clauses:
        targets: list[str] = []
        for reference in clause.get("references", []):
            article_root = _reference_to_article_root(reference)
            if not article_root:
                continue

            local_targets = [reg_id for reg_id in local_article_index.get(article_root, []) if reg_id != clause["id"]]
            if local_targets:
                targets.extend(local_targets)
                continue

            # Fallback: resolve from external cleaned corpus when article missing in local JSON scope.
            targets.extend(external_article_index.get(article_root, []))

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
    external_article_index = load_external_article_index(external_reference_files or [])
    resolve_reference_clause_ids(
        clauses=clauses,
        local_article_index=local_article_index,
        external_article_index=external_article_index,
    )

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
