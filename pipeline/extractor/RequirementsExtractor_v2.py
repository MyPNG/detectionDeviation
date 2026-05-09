from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import warnings

try:
    import spacy
except Exception:  # pragma: no cover - optional runtime dependency
    spacy = None


def _build_alt_pattern(items: list[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    cleaned.sort(key=len, reverse=True)
    if not cleaned:
        return r"$^"
    return "|".join(re.escape(item) for item in cleaned)


def _load_modal_rules(path: Path) -> dict[str, list[str]]:
    defaults: dict[str, list[str]] = {
        "PROHIBITED": ["shall not", "must not", "may not"],
        "MANDATORY": ["shall", "must", "will", "requires"],
        "PERMISSIVE": ["may", "can", "entitled to"],
        "ADVISORY": ["should", "is encouraged to"],
    }
    if not path.exists():
        return defaults

    loaded: dict[str, list[str]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        norm_key = key.strip().upper()
        values = [token.strip().lower() for token in value.split(",") if token.strip()]
        if norm_key and values:
            loaded[norm_key] = values

    # Ensure every expected key exists.
    for key, default_values in defaults.items():
        if key not in loaded or not loaded[key]:
            loaded[key] = default_values
    return loaded


ARTICLE_HEADER_RE = re.compile(r"^\s*Article\s+(\d+)\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^\(\s*([a-z])\s*\)", re.IGNORECASE)
TEXT_REF_RE = re.compile(r"#/texts/(\d+)")
WHITESPACE_RE = re.compile(r"\s+")
CLAUSE_SPLIT_RE = re.compile(r";\s+")
CONNECTOR_RE = re.compile(r"\b(and|or|but|if|provided that)\b", re.IGNORECASE)
MODAL_RULES = _load_modal_rules(Path(__file__).resolve().parent / "modal_force_rules.txt")

_modal_union: list[str] = []
for _rule_key in ("PROHIBITED", "MANDATORY", "PERMISSIVE", "ADVISORY"):
    _modal_union.extend(MODAL_RULES.get(_rule_key, []))
# Deduplicate while preserving order.
_seen_modal: set[str] = set()
MODAL_SIGNAL_TERMS: list[str] = []
for _term in _modal_union:
    if _term in _seen_modal:
        continue
    _seen_modal.add(_term)
    MODAL_SIGNAL_TERMS.append(_term)
MODAL_SIGNAL_RE = re.compile(rf"\b({_build_alt_pattern(MODAL_SIGNAL_TERMS)})\b", re.IGNORECASE)

# For subject fallback regex, keep only single-word modal auxiliaries and keep is/are.
SUBJECT_FALLBACK_VERBS = sorted(
    {term for term in MODAL_SIGNAL_TERMS if " " not in term}.union({"is", "are"}),
    key=len,
    reverse=True,
)
SUBJECT_FALLBACK_ALT = _build_alt_pattern(SUBJECT_FALLBACK_VERBS)
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
POINT_LIST_OF_ARTICLE_PATTERN = re.compile(
    r"\bpoints?\s+((?:\(\s*[a-zA-Z]\s*\)\s*(?:,|and|or)?\s*)+)\s+of\s+Article\s+(\d+)\s*(\(\s*\d+\s*\))",
    flags=re.IGNORECASE,
)
POINT_LIST_OF_PARAGRAPH_PATTERN = re.compile(
    r"\bpoints?\s+((?:\(\s*[a-zA-Z]\s*\)\s*(?:,|and|or)?\s*)+)\s+of\s+paragraph\s+(\d+)",
    flags=re.IGNORECASE,
)
POINT_OF_PARAGRAPH_PATTERN = re.compile(
    r"\bpoint\s*\(\s*([a-zA-Z])\s*\)\s+of\s+paragraph\s+(\d+)",
    flags=re.IGNORECASE,
)
PARAGRAPH_POINT_PATTERN = re.compile(
    r"\bparagraph\s+(\d+)\s*,\s*point\s*\(\s*([a-zA-Z])\s*\)",
    flags=re.IGNORECASE,
)
ARTICLE_TOKEN_PATTERN = re.compile(r"\d+(?:\(\s*[0-9A-Za-z]+\s*\))*")
PAREN_TOKEN_PATTERN = re.compile(r"\(\s*([0-9A-Za-z]+)\s*\)")
ARTICLE_ROOT_PATTERN = re.compile(r"^(?:Art\s*)?(\d+)$", flags=re.IGNORECASE)

# Modal-force mapping (ordered by precedence).
FORCE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Prohibited", re.compile(rf"\b({_build_alt_pattern(MODAL_RULES.get('PROHIBITED', []))})\b", re.IGNORECASE)),
    ("Mandatory", re.compile(rf"\b({_build_alt_pattern(MODAL_RULES.get('MANDATORY', []))})\b", re.IGNORECASE)),
    ("Permissive", re.compile(rf"\b({_build_alt_pattern(MODAL_RULES.get('PERMISSIVE', []))})\b", re.IGNORECASE)),
    ("Advisory", re.compile(rf"\b({_build_alt_pattern(MODAL_RULES.get('ADVISORY', []))})\b", re.IGNORECASE)),
]

RELATION_BY_CONNECTOR: dict[str, str] = {
    "and": "AND",
    "or": "OR",
    "but": "CONTRAST",
    "if": "CONDITIONAL",
    "provided that": "CONDITIONAL",
}


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
        self._nlp = self._init_spacy_pipeline()

    @staticmethod
    def _init_spacy_pipeline():
        """
        Lightweight spaCy pipeline for sentence segmentation + POS/dependency hints.
        Falls back gracefully if spaCy model is unavailable.
        """
        if spacy is None:
            return None
        try:
            return spacy.load("en_core_web_sm")
        except Exception:
            warnings.warn(
                "spaCy model 'en_core_web_sm' not found. Using rule-based fallback for anaphora resolution."
            )
            return None

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

    def identify_paragraph(self, text_item: dict[str, Any]) -> bool:
        """
        Paragraph rule:
        - label == list_item
        - text does NOT start with sub-marker like (a)
        """
        if str(text_item.get("label", "")).strip() != "list_item":
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

    @staticmethod
    def _split_sentences_rule_based(text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _detect_modal_force(text: str) -> str:
        """
        Return a single modal force label for a clause text, or empty if none.
        Precedence is defined by FORCE_PATTERNS order.
        """
        candidate = str(text).strip()
        if not candidate:
            return ""
        for force, pattern in FORCE_PATTERNS:
            if pattern.search(candidate):
                return force
        return ""

    @staticmethod
    def _collect_modal_matches(text: str) -> list[tuple[int, str, str]]:
        """
        Return sorted modal matches as (position, force, matched_signal_text).
        """
        matches: list[tuple[int, str, str]] = []
        candidate = str(text).strip()
        if not candidate:
            return matches
        for force, pattern in FORCE_PATTERNS:
            for match in pattern.finditer(candidate):
                matches.append((match.start(), force, match.group(0)))
        matches.sort(key=lambda item: item[0])
        return matches

    @staticmethod
    def _normalize_paren_token(token: str) -> str:
        cleaned = token.strip()
        if cleaned.isdigit():
            return str(int(cleaned))
        if cleaned.isalpha() and len(cleaned) == 1:
            return cleaned.lower()
        return cleaned

    @classmethod
    def _canonical_reference(cls, article_number: int, suffix: str = "") -> str:
        parts = PAREN_TOKEN_PATTERN.findall(suffix)
        normalized_suffix = "".join(f"({cls._normalize_paren_token(part)})" for part in parts)
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

    @staticmethod
    def _extract_point_tokens(group_text: str) -> list[str]:
        letters = re.findall(r"\(\s*([a-zA-Z])\s*\)", group_text)
        return [letter.lower() for letter in letters]

    def _detect_references_with_points(self, text: str, current_article: str) -> list[str]:
        references: list[str] = []
        candidate = str(text)

        # Article list references, e.g. "Articles 6(1) and 9(2)".
        for article_group in ARTICLE_LIST_PATTERN.findall(candidate):
            for token in ARTICLE_TOKEN_PATTERN.findall(article_group):
                token_match = re.match(r"^(\d+)((?:\(\s*[0-9A-Za-z]+\s*\))*)$", token.strip())
                if not token_match:
                    continue
                article_number_raw, suffix = token_match.groups()
                references.append(self._canonical_reference(int(article_number_raw), suffix))

        # Explicit article references incl. point-level if directly present: Art14(3)(a).
        for article_number_raw, suffix in ARTICLE_REF_PATTERN.findall(candidate):
            references.append(self._canonical_reference(int(article_number_raw), suffix))

        # "points (a) and (b) of Article 14(3)" -> Art14(3)(a), Art14(3)(b)
        for point_group, article_number_raw, paragraph_suffix in POINT_LIST_OF_ARTICLE_PATTERN.findall(candidate):
            for point_token in self._extract_point_tokens(point_group):
                references.append(
                    self._canonical_reference(int(article_number_raw), f"{paragraph_suffix}({point_token})")
                )

        # Same article resolution.
        current_article_number = self._parse_current_article_number(current_article)
        if current_article_number is not None:
            # "point (d) of paragraph 2" -> Art<current>(2)(d)
            for point_token_raw, paragraph_raw in POINT_OF_PARAGRAPH_PATTERN.findall(candidate):
                paragraph_no = int(paragraph_raw)
                point_token = point_token_raw.lower()
                references.append(
                    self._canonical_reference(current_article_number, f"({paragraph_no})({point_token})")
                )

            # "paragraph 2, point (d)" -> Art<current>(2)(d)
            for paragraph_raw, point_token_raw in PARAGRAPH_POINT_PATTERN.findall(candidate):
                paragraph_no = int(paragraph_raw)
                point_token = point_token_raw.lower()
                references.append(
                    self._canonical_reference(current_article_number, f"({paragraph_no})({point_token})")
                )

            # "points (a) and (b) of paragraph 3" -> Art<current>(3)(a), Art<current>(3)(b)
            for point_group, paragraph_raw in POINT_LIST_OF_PARAGRAPH_PATTERN.findall(candidate):
                paragraph_no = int(paragraph_raw)
                for point_token in self._extract_point_tokens(point_group):
                    references.append(
                        self._canonical_reference(current_article_number, f"({paragraph_no})({point_token})")
                    )

            # "pursuant to paragraphs 1 and 2" -> Art<current>(1), Art<current>(2)
            for paragraph_group in SAME_ARTICLE_PARAGRAPH_PATTERN.findall(candidate):
                for paragraph_number_raw in re.findall(r"\d+", paragraph_group):
                    references.append(
                        self._canonical_reference(current_article_number, f"({int(paragraph_number_raw)})")
                    )

        deduped = self._dedupe_keep_order(references)
        return self._drop_less_specific_when_point_exists(deduped)

    @staticmethod
    def _drop_less_specific_when_point_exists(references: list[str]) -> list[str]:
        """
        If point-level refs exist (ArtX(Y)(a)), drop less-specific ArtX(Y) refs
        for the same article+paragraph.
        """
        point_prefixes: set[str] = set()
        for ref in references:
            match = re.match(r"^(Art\d+\(\d+\))\([0-9A-Za-z]+\)$", ref)
            if match:
                point_prefixes.add(match.group(1))

        if not point_prefixes:
            return references

        filtered: list[str] = []
        for ref in references:
            if ref in point_prefixes:
                continue
            filtered.append(ref)
        return filtered

    @staticmethod
    def _relation_for_connector(fragment: str) -> str:
        match = CONNECTOR_RE.search(fragment)
        if not match:
            return "SEQUENCE"
        connector = match.group(1).strip().lower()
        return RELATION_BY_CONNECTOR.get(connector, "SEQUENCE")

    @staticmethod
    def _find_modal_connector_split(part: str) -> tuple[int, str] | None:
        """
        Return split index and relation type only when connector likely starts
        a new modal clause.
        """
        text = str(part)
        for match in CONNECTOR_RE.finditer(text):
            connector = match.group(1).strip().lower()
            after = text[match.end():]
            # Split only if a modal signal appears near connector boundary.
            modal_after = MODAL_SIGNAL_RE.search(after[:30])
            if modal_after:
                return (match.start(), RELATION_BY_CONNECTOR.get(connector, "SEQUENCE"))
        return None

    def _split_by_modality(self, text: str) -> list[dict[str, str]]:
        """
        Split text into modality-focused clause segments.
        Strategy:
        1) sentence split
        2) if sentence has multiple modal cues, split further by ';' and connectors.
        3) each output segment gets a modal force and relation_to_previous marker.
        """
        clean = self._normalize_text(text)
        if not clean:
            return []

        sentence_parts = self._split_sentences_rule_based(clean)
        if not sentence_parts:
            sentence_parts = [clean]

        outputs: list[dict[str, str]] = []
        for sent_index, sentence in enumerate(sentence_parts):
            sentence_clean = self._normalize_text(sentence)
            if not sentence_clean:
                continue

            modal_matches = self._collect_modal_matches(sentence_clean)
            if len(modal_matches) <= 1:
                outputs.append(
                    {
                        "text": sentence_clean,
                        "modal": self._detect_modal_force(sentence_clean),
                        "relation_to_previous": "SEQUENCE" if (sent_index > 0 and outputs) else "",
                    }
                )
                continue

            # Multiple modalities in one sentence: split by ';' first, then connectors.
            semicolon_parts = [self._normalize_text(part) for part in CLAUSE_SPLIT_RE.split(sentence_clean) if self._normalize_text(part)]
            if not semicolon_parts:
                semicolon_parts = [sentence_clean]

            for part_idx, part in enumerate(semicolon_parts):
                part_modal_matches = self._collect_modal_matches(part)
                if len(part_modal_matches) <= 1:
                    relation = self._relation_for_connector(part) if (outputs or part_idx > 0 or sent_index > 0) else ""
                    outputs.append(
                        {
                            "text": part,
                            "modal": self._detect_modal_force(part),
                            "relation_to_previous": relation,
                        }
                    )
                    continue

                # Further split at connectors when multiple modal cues still present.
                connector_split = self._find_modal_connector_split(part)
                if connector_split is not None:
                    split_start, relation_type = connector_split
                    left = self._normalize_text(part[:split_start])
                    right = self._normalize_text(part[split_start:])
                    if left:
                        relation_left = "SEQUENCE" if outputs else ""
                        outputs.append(
                            {
                                "text": left,
                                "modal": self._detect_modal_force(left),
                                "relation_to_previous": relation_left,
                            }
                        )
                    if right:
                        outputs.append(
                            {
                                "text": right,
                                "modal": self._detect_modal_force(right),
                                "relation_to_previous": relation_type,
                            }
                        )
                else:
                    relation = "SEQUENCE" if outputs else ""
                    outputs.append(
                        {
                            "text": part,
                            "modal": self._detect_modal_force(part),
                            "relation_to_previous": relation,
                        }
                    )

        return self._merge_non_modal_related_fragments(outputs)

    def _merge_non_modal_related_fragments(self, segments: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        Merge segments that carry no modality when they are logically tied
        to neighboring segments.

        Typical fix:
        - "Providers" (Modal="") + "or prospective providers may ..." (Modal="Permissive")
          => one merged segment.
        """
        normalized_segments: list[dict[str, str]] = []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            normalized_segments.append(
                {
                    "text": self._normalize_text(str(segment.get("text", ""))),
                    "modal": str(segment.get("modal", "")).strip(),
                    "relation_to_previous": str(segment.get("relation_to_previous", "")).strip(),
                }
            )

        merged: list[dict[str, str]] = []
        index = 0
        while index < len(normalized_segments):
            current = normalized_segments[index]
            current_text = current.get("text", "")
            current_modal = current.get("modal", "")
            current_relation = current.get("relation_to_previous", "")

            if not current_text:
                index += 1
                continue

            # Case A: no-modal prefix tied to the next logical fragment.
            if (
                current_modal == ""
                and index + 1 < len(normalized_segments)
                and str(normalized_segments[index + 1].get("relation_to_previous", "")).strip() != ""
            ):
                nxt = dict(normalized_segments[index + 1])
                nxt["text"] = self._normalize_text(f"{current_text} {str(nxt.get('text', ''))}")
                if current_relation:
                    nxt["relation_to_previous"] = current_relation
                normalized_segments[index + 1] = nxt
                index += 1
                continue

            # Case B: no-modal fragment tied to previous logical fragment.
            if current_modal == "" and current_relation and merged:
                merged[-1]["text"] = self._normalize_text(f"{merged[-1].get('text', '')} {current_text}")
                index += 1
                continue

            merged.append(current)
            index += 1

        return merged

    def _extract_subject_candidate(self, sentence: str) -> str:
        """
        Get a candidate antecedent noun phrase from a sentence.
        Priority:
        1) dependency nsubj subtree (spaCy)
        2) first noun chunk (spaCy)
        3) regex fallback around modal verbs
        """
        if not sentence:
            return ""
        if self._nlp is not None:
            doc = self._nlp(sentence)
            for token in doc:
                if token.dep_ == "nsubj":
                    subtree = " ".join(t.text for t in token.subtree).strip()
                    if subtree:
                        return self._normalize_text(subtree)
            for chunk in doc.noun_chunks:
                candidate = self._normalize_text(chunk.text)
                if candidate:
                    return candidate

        # Fallback: capture noun phrase before legal modal verbs.
        fallback_match = re.match(
            rf"^\s*([A-Z][^.;:]{{2,120}}?)\s+(?:{SUBJECT_FALLBACK_ALT})\b",
            sentence.strip(),
            flags=re.IGNORECASE,
        )
        if fallback_match:
            return self._normalize_text(fallback_match.group(1))
        return ""

    @staticmethod
    def _replace_sentence_initial_pronoun(sentence: str, antecedent: str) -> str:
        if not antecedent:
            return sentence
        # Resolve common anaphoric starts for regulatory sentences.
        return re.sub(
            r"^\s*(It|This system|This paragraph|This)\b",
            antecedent,
            sentence,
            flags=re.IGNORECASE,
        )

    def _resolve_anaphora_in_text(self, text: str) -> str:
        """
        Lightweight deterministic anaphora resolution:
        - walks sentence by sentence
        - replaces sentence-initial pronouns (e.g., "It") with the latest
          detected antecedent noun phrase.
        """
        clean = self._normalize_text(text)
        if not clean:
            return clean

        sentences = self._split_sentences_rule_based(clean)
        if not sentences:
            return clean

        resolved_sentences: list[str] = []
        current_antecedent = ""
        for sentence in sentences:
            updated = self._replace_sentence_initial_pronoun(sentence, current_antecedent)
            resolved_sentences.append(self._normalize_text(updated))
            candidate = self._extract_subject_candidate(updated)
            if candidate:
                current_antecedent = candidate
        return self._normalize_text(" ".join(resolved_sentences))

    @staticmethod
    def _normalize_include_articles(include_articles: list[int] | None) -> set[int] | None:
        """
        Normalize optional include-article list into a set for fast lookups.
        Returns None when no filtering is requested.
        """
        if include_articles is None:
            return None
        normalized: set[int] = set()
        for article in include_articles:
            try:
                normalized.add(int(article))
            except Exception:
                continue
        return normalized if normalized else set()

    def _build_bullet_prefix_from_paragraph(self, paragraph_text: str) -> str:
        """
        Build context prefix used for each subsequent bullet:
        - prefer the sentence that introduces the list (contains ':')
        - fallback to the full paragraph text
        """
        clean = self._normalize_text(paragraph_text)
        if not clean:
            return ""
        sentences = self._split_sentences_rule_based(clean)
        for sentence in reversed(sentences):
            if ":" in sentence:
                return self._normalize_text(sentence)
        return clean

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

    def _append_text_labels_to_previous_requirement(
        self,
        requirements: list[dict[str, str]],
        index_to_article: dict[int, ArticleSection],
    ) -> None:
        """
        Attach standalone `label == text` items to the nearest previous
        extracted requirement in the same article.

        This captures patterns where explanatory body text follows a list_item
        paragraph and should belong to that paragraph.
        """
        if not requirements:
            return

        # Work on rows carrying source text index before merge.
        eligible_rows = [
            row
            for row in requirements
            if "_src_idx" in row and str(row.get("Article", "")).strip()
        ]
        if not eligible_rows:
            return

        for text_idx, item in enumerate(self.texts):
            if str(item.get("label", "")).strip() != "text":
                continue

            text_value = self._normalize_text(str(item.get("text", "")))
            if not text_value:
                continue

            article_section = index_to_article.get(text_idx)
            if article_section is None:
                continue
            article_key = str(article_section.number)

            # Pick nearest previous extracted row in same article.
            best_row: dict[str, str] | None = None
            best_src_idx = -1
            for row in eligible_rows:
                if str(row.get("Article", "")).strip() != article_key:
                    continue
                src_idx = int(str(row.get("_src_idx", "-1")))
                if src_idx < text_idx and src_idx > best_src_idx:
                    best_src_idx = src_idx
                    best_row = row

            if best_row is None:
                continue

            current_text = self._normalize_text(str(best_row.get("Text", "")))
            # Avoid duplicate appends.
            if text_value and text_value not in current_text:
                best_row["Text"] = f"{current_text} {text_value}".strip()

    def extract_requirements(self, include_articles: list[int] | None = None) -> list[dict[str, str]]:
        sections = self.extract_articles()
        index_to_article = self._build_text_index_to_article(sections)
        include_set = self._normalize_include_articles(include_articles)
        paragraph_counter_by_article: dict[int, int] = defaultdict(int)
        current_paragraph_by_article: dict[int, int] = {}
        bullet_prefix_by_article: dict[int, str] = {}

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
            if include_set is not None and article_no not in include_set:
                continue

            for idx in text_indices:
                item = self.texts[idx]
                if str(item.get("label", "")).strip() != "list_item":
                    continue

                text = self._normalize_text(str(item.get("text", "")))
                if not text:
                    continue

                # Each list_item without (a)/(b)/... starts a new paragraph.
                if self.identify_paragraph(item):
                    paragraph_counter_by_article[article_no] += 1
                    current_paragraph_by_article[article_no] = paragraph_counter_by_article[article_no]

                paragraph_no = current_paragraph_by_article.get(article_no)
                bullet_letter = self.identify_bullet_point(item)

                if bullet_letter and paragraph_no is not None:
                    paragraph_value = f"{paragraph_no}({bullet_letter})"
                elif bullet_letter and paragraph_no is None:
                    paragraph_value = f"({bullet_letter})"
                elif paragraph_no is not None:
                    paragraph_value = str(paragraph_no)
                else:
                    continue

                resolved_text = self._resolve_anaphora_in_text(text)
                output_text = resolved_text

                if not bullet_letter:
                    # Keep latest paragraph context for upcoming points.
                    bullet_prefix_by_article[article_no] = self._build_bullet_prefix_from_paragraph(resolved_text)
                else:
                    prefix = bullet_prefix_by_article.get(article_no, "").strip()
                    if prefix:
                        output_text = self._normalize_text(f"{prefix} {resolved_text}")

                split_rows = self._split_by_modality(output_text)
                if not split_rows:
                    split_rows = [
                        {
                            "text": output_text,
                            "modal": "",
                            "relation_to_previous": "",
                        }
                    ]

                split_group = f"{article_no}:{paragraph_value}:{order_counter}"
                for split_idx, split_row in enumerate(split_rows):
                    extracted.append(
                        {
                            "ID": "",  # filled after extraction
                            "Article": str(article_no),
                            "Paragraph": paragraph_value,
                            "Text": self._normalize_text(str(split_row.get("text", ""))),
                            "Modal": str(split_row.get("modal", "")).strip(),
                            "_split_group": split_group,
                            "_split_idx": str(split_idx),
                            "_relation_to_previous": str(split_row.get("relation_to_previous", "")).strip(),
                            "_order": str(order_counter),
                            "_src_idx": str(idx),
                        }
                    )
                    order_counter += 1

        self._append_text_labels_to_previous_requirement(extracted, index_to_article)
        # IMPORTANT: do not merge point rows back into one paragraph;
        # keep each point as its own requirement row.

        sorted_rows = sorted(extracted, key=lambda r: int(r.get("_order", 0)))
        width = max(3, len(str(len(sorted_rows))))
        for i, row in enumerate(sorted_rows, start=1):
            row["ID"] = f"REG-{i:0{width}d}"

        # Build parent/children links:
        # - Parent of ArtX paragraph point "N(a)" is paragraph "N" within same article.
        # - Paragraph rows get 0..n children pointing to their point rows.
        key_to_id: dict[tuple[str, str], str] = {}
        for row in sorted_rows:
            key_to_id[(str(row.get("Article", "")).strip(), str(row.get("Paragraph", "")).strip())] = str(row.get("ID", ""))

        children_by_id: dict[str, list[str]] = defaultdict(list)
        parent_by_id: dict[str, str | None] = {}

        point_paragraph_re = re.compile(r"^(\d+)\(([a-z])\)$", re.IGNORECASE)
        for row in sorted_rows:
            row_id = str(row.get("ID", "")).strip()
            article = str(row.get("Article", "")).strip()
            paragraph = str(row.get("Paragraph", "")).strip()
            parent_id: str | None = None

            match = point_paragraph_re.match(paragraph)
            if match:
                base_paragraph = match.group(1)
                parent_id = key_to_id.get((article, base_paragraph))
                if parent_id:
                    children_by_id[parent_id].append(row_id)

            parent_by_id[row_id] = parent_id

        for row in sorted_rows:
            row_id = str(row.get("ID", "")).strip()
            row["parent"] = parent_by_id.get(row_id)
            row["children"] = children_by_id.get(row_id, [])

        # Build logical relations for split rows.
        split_group_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in sorted_rows:
            split_group = str(row.get("_split_group", "")).strip()
            if split_group:
                split_group_rows[split_group].append(row)

        for group_rows in split_group_rows.values():
            rows_in_order = sorted(group_rows, key=lambda r: int(str(r.get("_split_idx", "0"))))
            for idx, row in enumerate(rows_in_order):
                relations: list[dict[str, str]] = []
                if idx > 0:
                    prev_id = str(rows_in_order[idx - 1].get("ID", "")).strip()
                    relation_type = str(row.get("_relation_to_previous", "")).strip() or "SEQUENCE"
                    if prev_id:
                        relations.append({"type": relation_type, "target": prev_id})
                row["logic_relations"] = relations

        for row in sorted_rows:
            row["references"] = self._detect_references_with_points(
                text=str(row.get("Text", "")),
                current_article=str(row.get("Article", "")),
            )
            row.pop("_order", None)
            row.pop("_src_idx", None)
            row.pop("_split_group", None)
            row.pop("_split_idx", None)
            row.pop("_relation_to_previous", None)

        return sorted_rows

    def save_requirements(self, output_path: str | Path, include_articles: list[int] | None = None) -> Path:
        requirements = self.extract_requirements(include_articles=include_articles)
        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(requirements, indent=2, ensure_ascii=False), encoding="utf-8")
        return output

    def save_requirements_dual(
        self,
        main_output_path: str | Path,
        extended_output_path: str | Path,
        main_articles: list[int],
        extended_articles: list[int],
    ) -> tuple[Path, Path]:
        """
        Save two requirement files:
        - main-only article set
        - extended article set (main + 1-depth context)
        """
        main_saved = self.save_requirements(main_output_path, include_articles=main_articles)
        extended_saved = self.save_requirements(extended_output_path, include_articles=extended_articles)
        return main_saved, extended_saved


def main() -> None:
    input_json = "/Users/my/Documents/projects/detectionDeviation/input/reg_eu_ai_act/eu_ai_act.json"
    output_main_json = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/reg_eu_ai_act/eu_ai_requirements.json"
    output_extended_json = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/reg_eu_ai_act/eu_ai_requirements_extended.json"

    # main: 8, 9, 10, 11, 12, 13, 14, 15
    main_articles = [8, 9, 10, 11, 12, 13, 14, 15]
    # 1-depth context additions: 72, 79, 60, 97, 26
    depth_one_articles = [72, 79, 60, 97, 26]
    extended_articles = list(dict.fromkeys(main_articles + depth_one_articles))

    extractor = RequirementsExtractor(input_json)
    saved_main, saved_extended = extractor.save_requirements_dual(
        main_output_path=output_main_json,
        extended_output_path=output_extended_json,
        main_articles=main_articles,
        extended_articles=extended_articles,
    )
    print(f"Saved main requirements: {saved_main}")
    print(f"Saved extended requirements: {saved_extended}")


if __name__ == "__main__":
    main()
