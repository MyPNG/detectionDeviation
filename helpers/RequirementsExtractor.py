from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ARTICLE_HEADER_RE = re.compile(r"^\s*Article\s+(\d+)\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^\(\s*([a-z])\s*\)", re.IGNORECASE)
TEXT_REF_RE = re.compile(r"#/texts/(\d+)")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class ArticleSection:
    number: int
    title: str
    start_text_index: int
    end_text_index: int


class RequirementsExtractor:
    def __init__(self, gdpr_json_path: str | Path):
        self.gdpr_json_path = Path(gdpr_json_path).expanduser().resolve()
        self.data = self._load_json(self.gdpr_json_path)
        self.texts: list[dict[str, Any]] = self._get_list(self.data.get("texts"))
        self.groups: list[dict[str, Any]] = self._get_list(self.data.get("groups"))

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("GDPR JSON payload must be an object.")
        return payload

    @staticmethod
    def _get_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _normalize_text(value: str) -> str:
        return WHITESPACE_RE.sub(" ", value).strip()

    @staticmethod
    def _extract_text_index_from_ref(ref: str) -> int | None:
        match = TEXT_REF_RE.search(ref)
        if not match:
            return None
        return int(match.group(1))

    def extract_articles(self) -> list[ArticleSection]:
        """
        Extract article number/title spans from `texts` where label == section_header.
        """
        article_headers: list[tuple[int, int, str]] = []

        for idx, item in enumerate(self.texts):
            if str(item.get("label", "")).strip() != "section_header":
                continue
            text = self._normalize_text(str(item.get("text", "")))
            match = ARTICLE_HEADER_RE.match(text)
            if not match:
                continue
            article_number = int(match.group(1))
            article_title = ""
            next_idx = idx + 1
            if next_idx < len(self.texts):
                next_item = self.texts[next_idx]
                if str(next_item.get("label", "")).strip() == "section_header":
                    candidate_title = self._normalize_text(str(next_item.get("text", "")))
                    if not ARTICLE_HEADER_RE.match(candidate_title):
                        article_title = candidate_title
            article_headers.append((idx, article_number, article_title))

        sections: list[ArticleSection] = []
        for i, (start_idx, article_number, article_title) in enumerate(article_headers):
            if i + 1 < len(article_headers):
                end_idx = article_headers[i + 1][0] - 1
            else:
                end_idx = len(self.texts) - 1
            sections.append(
                ArticleSection(
                    number=article_number,
                    title=article_title,
                    start_text_index=start_idx,
                    end_text_index=end_idx,
                )
            )
        return sections

    def identify_paragraph(self, text_item: dict[str, Any], is_first_in_group: bool) -> bool:
        """
        Paragraph rule:
        - label == list_item
        - first item in a group
        - text does NOT start with sub-marker like (a)
        """
        if str(text_item.get("label", "")).strip() != "list_item":
            return False
        if not is_first_in_group:
            return False
        text = self._normalize_text(str(text_item.get("text", "")))
        return BULLET_RE.match(text) is None

    def identify_bullet_point(self, text_item: dict[str, Any]) -> str | None:
        """
        Bullet rule:
        - label == list_item
        - text starts with (a), (b), ...
        Returns bullet letter or None.
        """
        if str(text_item.get("label", "")).strip() != "list_item":
            return None
        text = self._normalize_text(str(text_item.get("text", "")))
        match = BULLET_RE.match(text)
        if not match:
            return None
        return match.group(1).lower()

    def _build_text_index_to_article(self, sections: list[ArticleSection]) -> dict[int, ArticleSection]:
        index_to_article: dict[int, ArticleSection] = {}
        for section in sections:
            for idx in range(section.start_text_index, section.end_text_index + 1):
                index_to_article[idx] = section
        return index_to_article

    def _group_text_indices(self, group_item: dict[str, Any]) -> list[int]:
        children = group_item.get("children")
        if not isinstance(children, list):
            return []
        indices: list[int] = []
        for child in children:
            if not isinstance(child, dict):
                continue
            ref_obj = child.get("$ref")
            if not isinstance(ref_obj, str):
                continue
            text_index = self._extract_text_index_from_ref(ref_obj)
            if text_index is None:
                continue
            if 0 <= text_index < len(self.texts):
                indices.append(text_index)
        return indices

    @staticmethod
    def _base_paragraph(paragraph_value: str) -> str:
        paragraph_text = str(paragraph_value).strip()
        match = re.match(r"^(\d+)", paragraph_text)
        if not match:
            return paragraph_text
        return match.group(1)

    def merge_bullet_points_by_paragraph(self, requirements: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        Merge bullet points (e.g. 1(a), 1(b), ...) into one row per paragraph.
        Output paragraph key is the base paragraph number (e.g. 1).
        """
        grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in requirements:
            article = str(row.get("Article", "")).strip()
            paragraph = str(row.get("Paragraph", "")).strip()
            base_paragraph = self._base_paragraph(paragraph)
            grouped[(article, base_paragraph)].append(row)

        merged_rows: list[dict[str, str]] = []
        for (_, base_paragraph), rows in sorted(
            grouped.items(),
            key=lambda item: min(int(r.get("_order", 0)) for r in item[1]),
        ):
            rows_sorted = sorted(rows, key=lambda r: int(r.get("_order", 0)))
            article = str(rows_sorted[0].get("Article", "")).strip()

            lead_texts: list[str] = []
            bullet_texts: list[str] = []
            for row in rows_sorted:
                paragraph = str(row.get("Paragraph", "")).strip()
                text = self._normalize_text(str(row.get("Text", "")))
                if not text:
                    continue
                if BULLET_RE.match(text) or re.match(r"^\d+\([a-z]\)$", paragraph, flags=re.IGNORECASE):
                    bullet_texts.append(text)
                else:
                    lead_texts.append(text)

            merged_text_parts = lead_texts + bullet_texts
            if not merged_text_parts:
                continue
            merged_text = " ".join(merged_text_parts)
            merged_rows.append(
                {
                    "ID": "",
                    "Article": article,
                    "Paragraph": base_paragraph,
                    "Text": merged_text,
                    "_order": str(min(int(r.get("_order", 0)) for r in rows_sorted)),
                }
            )

        return merged_rows

    def extract_requirements(self) -> list[dict[str, str]]:
        sections = self.extract_articles()
        index_to_article = self._build_text_index_to_article(sections)
        paragraph_counter_by_article: dict[int, int] = defaultdict(int)
        current_paragraph_by_article: dict[int, int] = {}

        extracted: list[dict[str, str]] = []
        order_counter = 0

        for group_item in self.groups:
            text_indices = self._group_text_indices(group_item)
            if not text_indices:
                continue

            first_idx = text_indices[0]
            article_section = index_to_article.get(first_idx)
            if article_section is None:
                continue
            article_no = article_section.number

            first_item = self.texts[first_idx]
            if self.identify_paragraph(first_item, is_first_in_group=True):
                paragraph_counter_by_article[article_no] += 1
                current_paragraph_by_article[article_no] = paragraph_counter_by_article[article_no]

            for idx in text_indices:
                item = self.texts[idx]
                if str(item.get("label", "")).strip() != "list_item":
                    continue

                text = self._normalize_text(str(item.get("text", "")))
                if not text:
                    continue

                paragraph_no = current_paragraph_by_article.get(article_no)
                bullet_letter = self.identify_bullet_point(item)

                if bullet_letter and paragraph_no is not None:
                    paragraph_value = f"{paragraph_no}({bullet_letter})"
                elif bullet_letter and paragraph_no is None:
                    paragraph_value = f"({bullet_letter})"
                elif idx == first_idx and paragraph_no is not None:
                    paragraph_value = str(paragraph_no)
                elif paragraph_no is not None:
                    paragraph_value = str(paragraph_no)
                else:
                    continue

                extracted.append(
                    {
                        "ID": "",  # filled after extraction
                        "Article": str(article_no),
                        "Paragraph": paragraph_value,
                        "Text": text,
                        "_order": str(order_counter),
                    }
                )
                order_counter += 1

        extracted = self.merge_bullet_points_by_paragraph(extracted)

        width = max(3, len(str(len(extracted))))
        for i, row in enumerate(sorted(extracted, key=lambda r: int(r.get("_order", 0))), start=1):
            row["ID"] = f"REG-{i:0{width}d}"
            row.pop("_order", None)
        return extracted

    def save_requirements(self, output_path: str | Path) -> Path:
        requirements = self.extract_requirements()
        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(requirements, indent=2, ensure_ascii=False), encoding="utf-8")
        return output


def main() -> None:
    input_json = "/Users/my/Documents/projects/detectionDeviation/datasets/reg/gdpr.json"
    output_json = "/Users/my/Documents/projects/detectionDeviation/gdpr_clause/gdpr_requirements.json"
    extractor = RequirementsExtractor(input_json)
    saved_path = extractor.save_requirements(output_json)
    print(f"Saved requirements: {saved_path}")


if __name__ == "__main__":
    main()
