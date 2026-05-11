from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ARTICLE_REF_PATTERN = re.compile(
    r"\b(?:Article|Art\.?)\s*(\d+)\s*((?:\(\s*[0-9A-Za-z]+\s*\)\s*)*)",
    flags=re.IGNORECASE,
)
ARTICLE_LIST_PATTERN = re.compile(
    r"\b(?:Article|Articles|Art\.?)\s+((?:\d+(?:\(\s*[0-9A-Za-z]+\s*\))*(?:\s*(?:,|and|or)\s*)?)+)",
    flags=re.IGNORECASE,
)
SAME_ARTICLE_PARAGRAPH_PATTERN = re.compile(
    r"\bparagraphs?\s+((?:\d+\s*(?:,|and|or)\s*)*\d+)\b",
    flags=re.IGNORECASE,
)
PAREN_TOKEN_PATTERN = re.compile(r"\(\s*([0-9A-Za-z]+)\s*\)")
ARTICLE_ROOT_PATTERN = re.compile(r"^(?:Art\s*)?(\d+)$", flags=re.IGNORECASE)
ARTICLE_TOKEN_PATTERN = re.compile(r"\d+(?:\(\s*[0-9A-Za-z]+\s*\))*")


class AdditionalReferenceDetector:
    """
    Detect additional GDPR references from clause text.

    Supported patterns:
    - "Article 14"               -> Art14
    - "Article 14(2)"            -> Art14(2)
    - "in paragraph 1 ..."       -> Art<current_article>(1)
    - multiple references in one text
    """

    @staticmethod
    def _normalize_paren_token(token: str) -> str:
        cleaned = token.strip()
        if cleaned.isdigit():
            return str(int(cleaned))
        if cleaned.isalpha() and len(cleaned) == 1:
            return cleaned.lower()
        return cleaned

    @staticmethod
    def _canonical_reference(article_number: int, suffix: str = "") -> str:
        parts = PAREN_TOKEN_PATTERN.findall(suffix)
        normalized_suffix = "".join(f"({AdditionalReferenceDetector._normalize_paren_token(part)})" for part in parts)
        return f"Art{int(article_number)}{normalized_suffix}"

    @staticmethod
    def _dedupe_keep_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    @staticmethod
    def _parse_current_article_number(current_article: str) -> int | None:
        match = ARTICLE_ROOT_PATTERN.match(str(current_article).strip())
        if not match:
            return None
        return int(match.group(1))

    def detect_additional_references(self, text: str, current_article: str) -> list[str]:
        references: list[str] = []

        # Article list references, e.g. "Article 46 or 49", "Articles 6(1) and 9(2)".
        for article_group in ARTICLE_LIST_PATTERN.findall(text):
            for token in ARTICLE_TOKEN_PATTERN.findall(article_group):
                token_match = re.match(r"^(\d+)((?:\(\s*[0-9A-Za-z]+\s*\))*)$", token.strip())
                if not token_match:
                    continue
                article_number_raw, suffix = token_match.groups()
                references.append(self._canonical_reference(int(article_number_raw), suffix))

        # Explicit article references, potentially with paragraph/point suffixes.
        for article_number_raw, suffix in ARTICLE_REF_PATTERN.findall(text):
            references.append(self._canonical_reference(int(article_number_raw), suffix))

        # Same-article paragraph references such as "in paragraph 1" / "paragraphs 1 and 2".
        current_article_number = self._parse_current_article_number(current_article)
        if current_article_number is not None:
            for paragraph_group in SAME_ARTICLE_PARAGRAPH_PATTERN.findall(text):
                for paragraph_number_raw in re.findall(r"\d+", paragraph_group):
                    references.append(self._canonical_reference(current_article_number, f"({int(paragraph_number_raw)})"))

        return self._dedupe_keep_order(references)

    def add_additional_references_to_clauses(
        self,
        clauses: list[dict[str, Any]],
        text_field: str = "Text",
        article_field: str = "Article",
        references_field: str = "references",
    ) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for clause in clauses:
            text_value = str(clause.get(text_field, ""))
            current_article = str(clause.get(article_field, ""))
            detected = self.detect_additional_references(text_value, current_article=current_article)

            existing = clause.get(references_field, [])
            existing_refs = [str(item) for item in existing] if isinstance(existing, list) else []
            merged = self._dedupe_keep_order(existing_refs + detected)

            updated = dict(clause)
            updated[references_field] = merged
            enriched.append(updated)
        return enriched


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    preferred_input = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements.json"
    fallback_input = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements.json"
    input_json = preferred_input if preferred_input.exists() else fallback_input
    output_json = input_json.parent / "eu_ai_requirements_with_additional_references.json"

    payload = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Expected input JSON to be a list of clause objects.")

    detector = AdditionalReferenceDetector()
    enriched = detector.add_additional_references_to_clauses(
        payload,
        text_field="Text",
        article_field="Article",
        references_field="references",
    )
    output_json.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved enriched clauses: {output_json}")


if __name__ == "__main__":
    main()
