from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import spacy  # type: ignore
except Exception:  # pragma: no cover
    spacy = None

class DeonticSlotExtractorLlama:
    """
    Extract deontic semantic slots from grouped regulatory nodes using a local
    Ollama-compatible Llama 3 endpoint.
    """

    SYSTEM_PROMPT = """### System Role
You are a Legal Compliance Auditor specialized in Deontic Logic. Your task is to decompose regulatory text into specific semantic slots. You must resolve all pronouns (Anaphora Resolution) using the provided context.

### Instructions
Extract the following slots for EVERY individual requirement found in the text:
1. ACTOR: The entity responsible for the action (Subject).
2. DEONTIC: The legal force (Mandatory, Permissive, Prohibited).
3. ACTION: The core verb/task.
4. OBJECT: The target of the action (Scope/Data).
5. TEMPORAL: Any time limits, deadlines, or frequency (The "When").
6. MANNER: The specific method or style of execution (The "How").
7. CONDITION: Any 'if', 'where', or 'when' triggers (The "Nebensatz").

### Special Rules for Deviations
- NEGATION: If the text describes a state of secrecy or a ban, mark DEONTIC as "Prohibited" even if the word 'not' is missing.
- RESPONSIBILITY: Always identify the specific role (e.g., "Provider" vs "Deployer").
- TIME: Extract durations exactly (e.g., "72 hours", "continuous").

### Rule: Contextual Inheritance
Some text fragments (e.g., those starting with 'and' or 'or') may have a missing Subject/Actor. If a node has a logic_relation or is part of a list, you MUST inherit the Actor from the preceding or parent node.
Example: If REG-118 says 'Deployers shall not use...' and REG-119 says 'and shall inform...', the Actor for REG-119 is 'Deployers'.

### Output Format
Return ONLY a valid JSON array of objects. Do not include introductory text.
Example Schema:
[
  {
    "id": "REG-XXX",
    "actor": "",
    "modal": "",
    "action": "",
    "object": "",
    "temporal": "",
    "manner": "",
    "condition": ""
  }
]
""".strip()
    PASSIVE_TO_ACTIVE_SYSTEM_PROMPT_TEMPLATE = """### SYSTEM ROLE
You are a Regulatory Linguist specializing in Deontic Logic. Your task is to perform 'Semantic Agent Recovery' while strictly preserving the Legal Modal Force.

### MODAL FORCE RULES (Preservation List)
{modal_force_rules_block}

### INSTRUCTIONS
1. IDENTIFY THE AGENT: Locate who is performing the action (check 'by...' phrases or context).
2. INFER THE AGENT: If the agent is missing, determine the responsible entity (e.g., Chapter III requirements usually apply to 'The Provider').
3. CONVERT TO ACTIVE: Rewrite the sentence so the Agent is the Subject.
4. MODAL PRESERVATION RULE: You MUST NOT lose the modal verb.
   - Passive: "Technical documentation shall be drawn up."
   - Active: "The Provider SHALL draw up technical documentation." (DO NOT use "The provider draws up").
5. NEGATION WATCH: If the original uses a PROHIBITED modal (e.g., 'shall not be used'), ensure the active version remains prohibited (e.g., 'The Deployer shall not use').
6. PRONOUN RESOLUTION (MANDATORY): During rewrite, resolve pronouns to explicit nouns whenever context allows.
   - Replace personal/possessive pronouns (e.g., it, they, them, this, that, those, its, their) with their antecedent noun phrase.
   - If the antecedent cannot be determined with confidence, keep the original pronoun.

### FORMAT
Input: JSON with "ID" and "Text".
Output: JSON with "ID" and "Active_Recovered_Text".
""".strip()
    ANAPHORA_MISSING_ACTOR_SYSTEM_PROMPT = """### SYSTEM ROLE
You are a legal text normalizer. Your task is to resolve anaphora and fill missing actor/subject in connector fragments, while preserving legal meaning and modality.

### INSTRUCTIONS
1. Keep each node ID unchanged.
2. Rewrite only the "Text" field for each node.
3. Resolve pronouns to explicit antecedents when clear from context.
4. If a node starts with connector words (and/or/but) and lacks an explicit subject, inherit the correct subject from previous context.
5. Do NOT convert passive to active voice in this step.
6. Do NOT add or remove legal constraints.

### OUTPUT FORMAT
Return ONLY a JSON array:
[
  { "ID": "REG-XXX", "Text": "..." }
]
""".strip()

    REQUIRED_FIELDS = [
        "id",
        "actor",
        "modal",
        "action",
        "object",
        "temporal",
        "manner",
        "condition",
    ]
    INVENTED_WORD_CHECK_FIELDS = [
        "actor",
        "action",
        "object",
        "temporal",
        "manner",
        "condition",
    ]

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 180,
        max_retries: int = 3,
        temperature: float = 0.1,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature
        self.modal_rules_path = Path(__file__).resolve().parents[1] / "extractor" / "modal_force_rules.txt"
        self.temporal_rules_path = Path(__file__).resolve().parents[1] / "extractor" / "temporal_phrases_rules.txt"
        self.modal_force_rules = self._load_modal_force_rules(self.modal_rules_path)
        self.temporal_phrase_rules = self._load_temporal_phrase_rules(self.temporal_rules_path)
        self.passive_to_active_system_prompt = self._build_passive_to_active_system_prompt()
        self._nlp = self._load_lightweight_nlp()
        # Preserve pronouns already present in source text during normalization.
        self.preserve_existing_pronouns = True

    @staticmethod
    def _load_lightweight_nlp() -> Any:
        """
        Best-effort lightweight NLP:
        - try en_core_web_sm with parser enabled
        - fall back to None (regex-only behavior)
        """
        if spacy is None:
            return None
        try:
            return spacy.load("en_core_web_sm", disable=["ner"])
        except Exception:
            return None

    @staticmethod
    def _load_requirements(input_json: Path) -> list[dict[str, Any]]:
        payload = json.loads(input_json.read_text(encoding="utf-8"))

        def _load_modal_map_from_companion(report_path: Path) -> dict[str, str]:
            """
            For passive->active report input, reuse upstream modal from the original
            requirements file by REG-ID.
            """
            candidates = [
                report_path.parent / "eu_ai_requirements_extended.json",
                report_path.parent / "eu_ai_requirements.json",
            ]
            modal_map: dict[str, str] = {}
            for candidate in candidates:
                if not candidate.exists():
                    continue
                try:
                    raw = json.loads(candidate.read_text(encoding="utf-8"))
                    if not isinstance(raw, list):
                        continue
                    for row in raw:
                        if not isinstance(row, dict):
                            continue
                        reg_id = str(row.get("ID", "")).strip()
                        modal = str(row.get("Modal", "")).strip()
                        if reg_id and modal:
                            modal_map[reg_id] = modal
                    if modal_map:
                        break
                except Exception:
                    continue
            return modal_map

        # Format A: plain requirement list
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

        # Format B: passive->active pipeline report
        # {
        #   "test_type": "passive_active_file_pipeline",
        #   "results": [
        #      {"article":"..","paragraph":"..","output":[{"ID":"..","Active_Recovered_Text":".."}], ...}
        #   ]
        # }
        if isinstance(payload, dict) and payload.get("test_type") == "passive_active_file_pipeline":
            rows: list[dict[str, Any]] = []
            modal_map = _load_modal_map_from_companion(input_json)
            for scenario in payload.get("results", []):
                if not isinstance(scenario, dict):
                    continue
                article = str(scenario.get("article", "")).strip()
                paragraph = str(scenario.get("paragraph", "")).strip()
                if not article or not paragraph:
                    continue
                output_rows = scenario.get("output", [])
                if not isinstance(output_rows, list):
                    output_rows = []

                # Primary path: use stage1-3 recovered text.
                for out_row in output_rows:
                    if not isinstance(out_row, dict):
                        continue
                    reg_id = str(out_row.get("ID", "")).strip()
                    text = DeonticSlotExtractorLlama._normalize_text(
                        str(out_row.get("Active_Recovered_Text", ""))
                    )
                    if not reg_id or not text:
                        continue
                    rows.append(
                        {
                            "ID": reg_id,
                            "Article": article,
                            "Paragraph": paragraph,
                            "Text": text,
                            "Modal": modal_map.get(reg_id, ""),
                        }
                    )

                # Fallback path: if stage1-3 failed and output is empty, reuse input_nodes
                # so stage4 can still extract slots deterministically.
                if not output_rows:
                    input_nodes = scenario.get("input_nodes", [])
                    if not isinstance(input_nodes, list):
                        input_nodes = []
                    for node in input_nodes:
                        if not isinstance(node, dict):
                            continue
                        reg_id = str(node.get("ID", "")).strip()
                        text = DeonticSlotExtractorLlama._normalize_text(str(node.get("Text", "")))
                        if not reg_id or not text:
                            continue
                        rows.append(
                            {
                                "ID": reg_id,
                                "Article": article,
                                "Paragraph": paragraph,
                                "Text": text,
                                "Modal": modal_map.get(reg_id, ""),
                            }
                        )
            return rows

        raise ValueError(f"Unsupported input format in: {input_json}")

    @staticmethod
    def _reg_sort_key(reg_id: str) -> tuple[int, str]:
        match = re.search(r"(\d+)", str(reg_id))
        if not match:
            return (10**9, str(reg_id))
        return (int(match.group(1)), str(reg_id))

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value)).strip()

    @staticmethod
    def _load_modal_force_rules(path: Path) -> dict[str, list[str]]:
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
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            norm_key = key.strip().upper()
            values = [token.strip() for token in value.split(",") if token.strip()]
            if norm_key and values:
                loaded[norm_key] = values

        for key, default_values in defaults.items():
            if key not in loaded or not loaded[key]:
                loaded[key] = default_values
        return loaded

    @staticmethod
    def _load_temporal_phrase_rules(path: Path) -> dict[str, list[str]]:
        defaults: dict[str, list[str]] = {
            "FREQUENCY": ["annually", "monthly", "continuous", "iterative", "regular", "periodically"],
            "DEADLINE": ["within", "no later than", "by", "at the latest", "before the end of"],
            "ANCHOR": ["upon", "after", "following", "from the moment", "at the time of"],
            "DURATION": ["throughout", "for a period of", "until", "during"],
            "SEQUENCE": ["prior to", "subsequently", "then", "first", "finally"],
        }
        if not path.exists():
            return defaults

        loaded: dict[str, list[str]] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            norm_key = key.strip().upper()
            values = [token.strip() for token in value.split(",") if token.strip()]
            if norm_key and values:
                loaded[norm_key] = values

        for key, default_values in defaults.items():
            if key not in loaded or not loaded[key]:
                loaded[key] = default_values
        return loaded

    def _all_temporal_phrases(self) -> list[str]:
        phrases: list[str] = []
        seen: set[str] = set()
        for values in self.temporal_phrase_rules.values():
            for phrase in values:
                norm = self._normalize_text(phrase).lower()
                if not norm or norm in seen:
                    continue
                seen.add(norm)
                phrases.append(norm)
        phrases.sort(key=len, reverse=True)
        return phrases

    def _build_modal_force_rules_block(self) -> str:
        order = ["PROHIBITED", "MANDATORY", "PERMISSIVE", "ADVISORY"]
        lines: list[str] = []
        for key in order:
            values = self.modal_force_rules.get(key, [])
            lines.append(f"- {key}: {', '.join(values)}")
        return "\n".join(lines)

    def _build_passive_to_active_system_prompt(self) -> str:
        return self.PASSIVE_TO_ACTIVE_SYSTEM_PROMPT_TEMPLATE.format(
            modal_force_rules_block=self._build_modal_force_rules_block()
        )

    def _modal_signal_terms(self) -> list[str]:
        ordered_keys = ["PROHIBITED", "MANDATORY", "PERMISSIVE", "ADVISORY"]
        terms: list[str] = []
        seen: set[str] = set()
        for key in ordered_keys:
            for term in self.modal_force_rules.get(key, []):
                norm = str(term).strip()
                if not norm:
                    continue
                low = norm.lower()
                if low in seen:
                    continue
                seen.add(low)
                terms.append(norm)
        terms.sort(key=len, reverse=True)
        return terms

    def _extract_actor_from_active_text(self, active_text: str) -> str:
        text = self._normalize_text(active_text)
        if not text:
            return ""
        modal_alt = "|".join(re.escape(term) for term in self._modal_signal_terms())
        match = re.match(rf"^\s*(.+?)\s+(?:{modal_alt})\b", text, flags=re.IGNORECASE)
        if not match:
            return ""
        return self._normalize_text(match.group(1))

    @staticmethod
    def _infer_actor_from_source_text(source_text: str) -> str:
        text = str(source_text).lower()
        if "deployer" in text or "deployers" in text:
            return "The Deployer"
        if "provider" in text or "providers" in text:
            return "The Provider"
        if "authority" in text or "authorities" in text:
            return "The Authorities"
        return ""

    @staticmethod
    def _is_non_empty_subject(subject: str) -> bool:
        text = str(subject).strip()
        return bool(text and text != "[missing_subject]")

    def _infer_subject_from_source_text(self, source_text: str) -> str:
        """
        Infer grammatical subject from source clause using modal anchor.
        Example:
        - 'that system shall not be used' -> 'that system'
        - 'the technical documentation shall be drawn up' -> 'the technical documentation'
        """
        text = self._normalize_text(source_text)
        if not text:
            return ""

        modal_alt = "|".join(re.escape(term) for term in self._modal_signal_terms())
        # strip connector prefix first
        text_wo_connector = re.sub(r"^\s*(and|or|but)\s+", "", text, flags=re.IGNORECASE)

        match = re.search(rf"(.+?)\s+(?:{modal_alt})\b", text_wo_connector, flags=re.IGNORECASE)
        if not match:
            return ""

        subject = self._normalize_text(match.group(1))
        # remove leading condition prefix to get the actual subject phrase
        subject = re.sub(r"^\s*(when|if|where)\b[^,]*,\s*", "", subject, flags=re.IGNORECASE).strip()
        return subject

    def _extract_subject_phrase(self, text: str) -> str:
        """
        Extract subject phrase with spaCy when available; fallback to regex-based infer.
        """
        clean = self._normalize_text(text)
        if not clean:
            return ""

        if self._nlp is not None:
            try:
                doc = self._nlp(clean)
                for token in doc:
                    if token.dep_ in {"nsubj", "nsubjpass"}:
                        subtree = " ".join(t.text for t in token.subtree)
                        subtree = self._normalize_text(subtree)
                        if subtree:
                            return subtree
            except Exception:
                pass
        return self._infer_subject_from_source_text(clean)

    def _extract_object_phrase(self, text: str) -> str:
        """
        Extract object phrase with spaCy when available; fallback to existing heuristics.
        """
        clean = self._normalize_text(text)
        if not clean:
            return ""

        if self._nlp is not None:
            try:
                doc = self._nlp(clean)
                for token in doc:
                    if token.dep_ in {"dobj", "pobj", "obj"}:
                        subtree = " ".join(t.text for t in token.subtree)
                        subtree = self._normalize_text(subtree)
                        if subtree:
                            return subtree
            except Exception:
                pass
        return self._infer_object_candidate_from_source(clean)

    def _infer_actor_candidate_from_source(self, source_text: str) -> str:
        """
        Prefer actor from leading condition context:
        - 'When such deployers find ...' -> 'deployers'
        Fallback to role inference.
        """
        text = self._normalize_text(source_text)
        cond_match = re.match(r"^\s*(when|if|where)\s+([^,]+),", text, flags=re.IGNORECASE)
        if cond_match:
            cond_clause = cond_match.group(2).lower()
            if "deployer" in cond_clause:
                return "deployers"
            if "provider" in cond_clause:
                return "provider"
            if "authorit" in cond_clause:
                return "authorities"

        role = self._infer_actor_from_source_text(text)
        if role.lower().endswith("deployer"):
            return "deployer"
        if role.lower().endswith("provider"):
            return "provider"
        if role.lower().endswith("authorities"):
            return "authorities"
        return ""

    def _infer_object_candidate_from_source(self, source_text: str) -> str:
        """
        Infer a stable object antecedent for pronoun resolution.
        """
        text = self._normalize_text(source_text)
        if not text:
            return ""

        system_matches = re.findall(
            r"\b(?:a|an|the|that)\s+(?:[a-z0-9-]+\s+){0,6}system\b",
            text,
            flags=re.IGNORECASE,
        )
        if system_matches:
            return self._normalize_text(system_matches[-1]).lower()

        if re.search(r"\btechnical documentation\b", text, flags=re.IGNORECASE):
            return "technical documentation"
        return ""

    @staticmethod
    def _extract_leading_condition(source_text: str) -> str:
        match = re.match(r"^\s*((?:when|if|where)\b[^,]*),", str(source_text), flags=re.IGNORECASE)
        if not match:
            return ""
        return DeonticSlotExtractorLlama._normalize_text(match.group(1))

    def _ensure_condition_presence(self, active_text: str, source_text: str) -> str:
        """
        Preserve leading condition from source if model rewrite dropped it.
        """
        out = self._normalize_text(active_text)
        if not out:
            return out
        condition = self._extract_leading_condition(source_text)
        if not condition:
            return out
        if re.search(r"\b(when|if|where)\b", out, flags=re.IGNORECASE):
            return out
        return f"{out.rstrip('.')} {condition.lower()}."

    def _resolve_pronouns_in_text(
        self,
        text: str,
        actor_hint: str,
        object_hint: str,
        source_text: str = "",
    ) -> str:
        """
        Resolve pronouns to explicit nouns when antecedents are known.
        """
        out = self._normalize_text(text)
        if not out:
            return out
        source = self._normalize_text(source_text)

        actor = self._normalize_text(actor_hint)
        obj = self._normalize_text(object_hint)

        def _allow_replace(pronoun: str) -> bool:
            if not self.preserve_existing_pronouns:
                return True
            if not source:
                return True
            return re.search(rf"\b{re.escape(pronoun)}\b", source, flags=re.IGNORECASE) is None

        actor_surface = actor
        if actor_surface.lower() == "deployers":
            actor_surface = "Deployers"
        elif actor_surface.lower() == "deployer":
            actor_surface = "The Deployer"
        elif actor_surface.lower() == "provider":
            actor_surface = "The Provider"
        elif actor_surface.lower() == "authorities":
            actor_surface = "The Authorities"

        if actor_surface:
            if _allow_replace("they"):
                out = re.sub(r"\bthey\b", actor_surface, out, flags=re.IGNORECASE)
            if _allow_replace("them"):
                out = re.sub(r"\bthem\b", actor_surface, out, flags=re.IGNORECASE)
            possessive = f"{actor_surface}'" if actor_surface.lower().endswith("s") else f"{actor_surface}'s"
            if _allow_replace("their"):
                out = re.sub(r"\btheir\b", possessive, out, flags=re.IGNORECASE)

        if obj:
            if _allow_replace("it"):
                out = re.sub(r"\bit\b", obj, out, flags=re.IGNORECASE)
            if _allow_replace("its"):
                out = re.sub(r"\bits\b", f"{obj}'s", out, flags=re.IGNORECASE)

        return self._normalize_text(out)

    @staticmethod
    def _lexical_overlap_ratio(source_text: str, rewritten_text: str) -> float:
        source_tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", str(source_text).lower()))
        rewritten_tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", str(rewritten_text).lower()))
        if not source_tokens or not rewritten_tokens:
            return 0.0
        return len(source_tokens & rewritten_tokens) / max(1, len(source_tokens))

    def _is_safe_stage1_rewrite(self, source_text: str, rewritten_text: str) -> bool:
        """
        Stage1 should resolve references/subjects, not expand clause semantics.
        """
        source = self._normalize_text(source_text)
        rewritten = self._normalize_text(rewritten_text)
        if not source or not rewritten:
            return False

        if len(rewritten) > int(len(source) * 1.5):
            return False

        if self._lexical_overlap_ratio(source, rewritten) < 0.65:
            return False

        return True

    def _collapse_duplicated_leading_subject(self, text: str) -> str:
        """
        Fix artifacts like:
        'The risk management system The risk management system shall ...'
        """
        value = self._normalize_text(text)
        if not value:
            return value

        pattern = re.compile(
            r"^(?P<subject>[A-Za-z][A-Za-z0-9' -]{2,120}?)\s+(?P=subject)\s+(?P<rest>.*)$",
            flags=re.IGNORECASE,
        )
        match = pattern.match(value)
        if not match:
            return value
        subject = self._normalize_text(match.group("subject"))
        rest = self._normalize_text(match.group("rest"))
        return f"{subject} {rest}".strip()

    @staticmethod
    def _source_starts_with_connector(source_text: str) -> bool:
        return bool(re.match(r"^\s*(and|or|but)\b", str(source_text), flags=re.IGNORECASE))

    @staticmethod
    def _participle_to_base(phrase: str) -> str:
        p = phrase.strip().lower()
        # Keep only phrasal particles when present; drop pronouns/determiners.
        particle_whitelist = {"up", "out", "off", "in", "on", "over", "away", "back", "down"}
        parts = p.split()
        if len(parts) >= 2 and parts[1] not in particle_whitelist:
            p = parts[0]
        lemma_map = {
            "reported": "report",
            "used": "use",
            "drawn up": "draw up",
            "drawn": "draw",
            "placed": "place",
            "provided": "provide",
            "performed": "perform",
            "processed": "process",
            "disclosed": "disclose",
            "stored": "store",
            "retained": "retain",
            "erased": "erase",
            "deleted": "delete",
            "collected": "collect",
            "transferred": "transfer",
            "withdrawn": "withdraw",
        }
        return lemma_map.get(p, p)

    def _rewrite_source_with_actor(self, source_text: str, actor: str) -> str:
        """
        Deterministic fallback rewrite:
        - removes leading connector
        - converts '<modal> [not] be <participle>' to '<modal> [not] <base_verb>'
        - prepends inferred/inherited actor
        """
        text = self._normalize_text(source_text)
        if not text:
            return ""

        text = re.sub(r"^\s*(and|or|but)\s+", "", text, flags=re.IGNORECASE)

        pattern = re.compile(
            r"^\s*(?P<modal>shall|must|may)\s+(?P<neg>not\s+)?be\s+(?P<pp1>[a-z]+(?:ed|en|n))(?:\s+(?P<pp2>[a-z]{2,6}))?(?P<tail>.*)$",
            flags=re.IGNORECASE,
        )
        match = pattern.match(text)
        if match:
            modal = self._normalize_text(match.group("modal")).lower()
            neg = "not " if match.group("neg") else ""
            pp_phrase = f"{match.group('pp1') or ''} {match.group('pp2') or ''}".strip()
            base = self._participle_to_base(pp_phrase)
            tail = self._normalize_text(match.group("tail") or "")
            reconstructed = f"{actor} {modal} {neg}{base}".strip()
            if tail:
                reconstructed = f"{reconstructed} {tail}".strip()
            if not reconstructed.endswith("."):
                reconstructed += "."
            return reconstructed

        # If text already begins with a modal, keep it and just prepend actor.
        if re.match(r"^\s*(shall|must|may|should|can|will|requires)\b", text, flags=re.IGNORECASE):
            out = f"{actor} {text}".strip()
            if not out.endswith("."):
                out += "."
            return out

        # Last-resort actor prefix.
        out = f"{actor} {text}".strip()
        if not out.endswith("."):
            out += "."
        return out

    def _rewrite_negative_imperative(self, source_text: str, actor_hint: str) -> str:
        """
        Deterministic handling for imperative prohibitions:
        - "Do not document X ..." -> "[missing_subject] shall not document X ..."
        This prevents LLM role inversion from by-phrases in modifiers.
        """
        text = self._normalize_text(source_text)
        if not text:
            return ""
        match = re.match(r"^\s*(do\s+not|don't)\s+([a-z][a-z-]*)(.*)$", text, flags=re.IGNORECASE)
        if not match:
            return ""

        verb = self._normalize_text(match.group(2)).lower()
        tail = self._normalize_text(match.group(3))
        actor = self._normalize_text(actor_hint)
        if not actor:
            actor = "[missing_subject]"

        out = f"{actor} shall not {verb}".strip()
        if tail:
            out = f"{out} {tail}".strip()
        if not out.endswith("."):
            out += "."
        return out

    def _rewrite_positive_imperative(self, source_text: str, actor_hint: str) -> str:
        """
        Deterministic handling for positive imperatives:
        - "Review X ..." -> "[missing_subject] shall review X ..."
        """
        text = self._normalize_text(source_text)
        if not text:
            return ""

        # Strip connector if present; imperative body starts after it.
        body = re.sub(r"^\s*(and|or|but)\s+", "", text, flags=re.IGNORECASE)
        match = re.match(r"^\s*([a-z][a-z-]*)(.*)$", body, flags=re.IGNORECASE)
        if not match:
            return ""

        verb = self._normalize_text(match.group(1)).lower()
        tail = self._normalize_text(match.group(2))
        actor = self._normalize_text(actor_hint) or "[missing_subject]"

        out = f"{actor} shall {verb}".strip()
        if tail:
            out = f"{out} {tail}".strip()
        if not out.endswith("."):
            out += "."
        return out

    def _looks_positive_imperative(self, source_text: str) -> bool:
        """
        Heuristic imperative detector for REA-style commands like:
        - "Review ..."
        - "Secure ..."
        - "Update and review ..."
        """
        text = DeonticSlotExtractorLlama._normalize_text(source_text)
        if not text:
            return False

        # Only inspect the first sentence for imperative detection.
        first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
        if not first_sentence:
            return False

        # Exclude explicit modal / conditional / nominal starts.
        if re.match(r"^\s*(if|when|where|unless|provided that)\b", first_sentence, flags=re.IGNORECASE):
            return False
        if re.match(r"^\s*(the|a|an|this|that|these|those|in|for|with|without|by|at|to|from|upon|after|before|during)\b", first_sentence, flags=re.IGNORECASE):
            return False
        if re.search(r"\b(shall|must|may|should|can|will|requires)\b", first_sentence, flags=re.IGNORECASE):
            return False
        if re.match(r"^\s*(do\s+not|don't)\b", first_sentence, flags=re.IGNORECASE):
            return False

        # Prefer spaCy decision when available:
        # imperative ~= root is bare verb (VB) and subject is missing.
        if self._nlp is not None:
            try:
                doc = self._nlp(first_sentence)
                sent = next(iter(doc.sents), None)
                if sent is not None:
                    has_subject = any(tok.dep_ in {"nsubj", "nsubjpass", "expl"} for tok in sent)
                    root = sent.root
                    if root is not None and root.pos_ == "VERB" and root.tag_ == "VB" and not has_subject:
                        return True
                    return False
            except Exception:
                # Fall through to conservative fallback.
                pass

        # Conservative fallback without NLP: do not force imperative rewrite.
        return False

    def _looks_passive_voice(self, source_text: str) -> bool:
        """
        Detect likely passive voice so stage-3 only rewrites when needed.
        """
        text = self._normalize_text(source_text)
        if not text:
            return False

        if self._nlp is not None:
            try:
                doc = self._nlp(text)
                for token in doc:
                    if token.dep_ in {"nsubjpass", "auxpass"}:
                        return True
            except Exception:
                pass

        # Fallback regex: be + participle pattern commonly used in legal passive clauses.
        return bool(
            re.search(
                r"\b(is|are|was|were|be|been|being)\s+\w+(ed|en|n)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _is_trusted_actor_for_imperative(actor_hint: str) -> bool:
        """
        Only allow explicit legal-role actors for imperative fallback.
        Prevents hallucinated entity actors like organizations/offices.
        """
        actor = DeonticSlotExtractorLlama._normalize_text(actor_hint).lower()
        if not actor:
            return False
        trusted_markers = {
            "provider",
            "providers",
            "deployer",
            "deployers",
            "authority",
            "authorities",
            "controller",
            "controllers",
            "processor",
            "processors",
        }
        tokens = set(re.findall(r"[a-z]+", actor))
        return any(token in trusted_markers for token in tokens)

    @staticmethod
    def _is_already_active_modal_clause(source_text: str) -> bool:
        """
        Deterministic guard policy:
        - modal + be + verb  -> treat as passive-ish, let LLM handle (no guard)
        - modal + verb       -> treat as active, guard applies
        - modal + be         -> ambiguous/incomplete, let LLM handle (no guard)
        - modal + be + X + Y where X/Y are non-verbal -> active guard applies
        """
        text = DeonticSlotExtractorLlama._normalize_text(source_text)
        if not text:
            return False

        text_wo_connector = re.sub(r"^\s*(and|or|but)\s+", "", text, flags=re.IGNORECASE)
        modal_clause = re.search(
            r"\b(shall|must|may|should|can|will|requires)\b\s+(not\s+)?([a-z]+)\b(?P<rest>.*)$",
            text_wo_connector,
            flags=re.IGNORECASE,
        )
        if not modal_clause:
            return False

        first_after_modal = (modal_clause.group(3) or "").lower()
        rest_after_first = DeonticSlotExtractorLlama._normalize_text(modal_clause.group("rest") or "")
        tail_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", rest_after_first.lower())

        # Rule 1 and 3:
        # - modal + be + verb -> no guard (LLM)
        # - modal + be        -> no guard (LLM)
        # Additional rule:
        # - if after two tokens there is still no verbal signal, treat as active guard.
        if first_after_modal == "be":
            if not tail_tokens:
                return False

            first_two = tail_tokens[:2]
            verbal_signal = re.compile(
                r"(ed|en|ing)$|^(use|used|using|draw|drawn|report|reported|place|placed|keep|kept|provide|provided|"
                r"perform|performed|process|processed|disclose|disclosed|store|stored|retain|retained|erase|erased|"
                r"delete|deleted|collect|collected|transfer|transferred|withdraw|withdrawn)$",
                flags=re.IGNORECASE,
            )
            if any(verbal_signal.search(tok) for tok in first_two):
                return False

            pre_modal = text_wo_connector[: modal_clause.start()].strip()
            return bool(pre_modal)

        # Rule 2: modal + lexical verb -> active guard (if explicit subject exists)
        # (once first token after modal is lexical and not "be", we treat clause as active.)
        pre_modal = text_wo_connector[: modal_clause.start()].strip()
        return bool(pre_modal)

    def _normalize_modal_verb_form(self, text: str) -> str:
        """
        Normalize malformed modal constructions in recovered text, e.g.:
        - 'shall reported' -> 'shall report'
        - 'shall not reported' -> 'shall not report'
        """
        value = self._normalize_text(text)
        if not value:
            return value

        modal_alt = "|".join(re.escape(term) for term in self._modal_signal_terms() if " " not in term)
        malformed_pattern = re.compile(
            rf"\b({modal_alt})\s+(not\s+)?([a-z]+(?:ed|en|n))(?:\s+([a-z]{{2,16}}))?\b",
            flags=re.IGNORECASE,
        )

        def _replace(match: re.Match[str]) -> str:
            modal = match.group(1)
            neg = match.group(2) or ""
            pp_phrase = f"{match.group(3) or ''} {match.group(4) or ''}".strip()
            base = self._participle_to_base(pp_phrase)
            if not base:
                return match.group(0)
            return f"{modal} {neg}{base}".strip()

        fixed = malformed_pattern.sub(_replace, value)
        return self._normalize_text(fixed)

    def _postprocess_passive_active_rows(
        self,
        nodes: list[dict[str, Any]],
        rows: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """
        Enforce actor inheritance for continuation fragments:
        - if output is empty, recover from context/source
        - if source starts with connector and output lacks explicit actor, inherit previous actor
        """
        by_id: dict[str, dict[str, str]] = {}
        for row in rows:
            row_id = str(row.get("ID", "")).strip()
            if row_id:
                by_id[row_id] = row

        processed: list[dict[str, str]] = []
        previous_subject = ""
        previous_actor = ""
        previous_object = ""

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("ID", "")).strip()
            source_text = self._normalize_text(str(node.get("Text", "")))
            raw_output = by_id.get(node_id, {})
            active_text = self._normalize_text(str(raw_output.get("Active_Recovered_Text", "")))
            starts_with_connector = self._source_starts_with_connector(source_text)

            # Subject hint from output and source.
            detected_subject = self._extract_actor_from_active_text(active_text)
            if self._is_non_empty_subject(detected_subject):
                previous_subject = detected_subject

            source_subject = self._infer_subject_from_source_text(source_text)
            if self._is_non_empty_subject(source_subject):
                previous_subject = source_subject
            source_actor = self._infer_actor_candidate_from_source(source_text)
            source_object = self._infer_object_candidate_from_source(source_text)
            source_is_active = self._is_already_active_modal_clause(source_text)
            source_is_passive = self._looks_passive_voice(source_text)
            source_is_negative_imperative = bool(
                re.match(r"^\s*(do\s+not|don't)\s+[a-z][a-z-]*\b", source_text, flags=re.IGNORECASE)
            )
            source_is_positive_imperative = self._looks_positive_imperative(source_text)
            # Do not let connector object-mentions (e.g. "to the provider") overwrite actor context.
            if not starts_with_connector and self._is_non_empty_subject(source_actor):
                previous_actor = source_actor
            if not starts_with_connector and source_object:
                previous_object = source_object

            needs_recovery = not active_text
            if starts_with_connector and not detected_subject:
                needs_recovery = True

            if needs_recovery:
                # Required order:
                # 1) If connector-fragment with missing actor -> inherit previous actor.
                # 2) If still missing -> [missing_subject]
                # 3) Then convert passive->active.
                if starts_with_connector and not detected_subject:
                    actor = previous_actor if self._is_non_empty_subject(previous_actor) else "[missing_subject]"
                else:
                    actor = source_actor or source_subject or detected_subject or previous_actor or previous_subject
                if not actor:
                    actor = "[missing_subject]"
                active_text = self._rewrite_source_with_actor(source_text, actor)
                # For connector fragments, keep connector semantics and allow pronoun carry-over.
                if starts_with_connector and actor != "[missing_subject]":
                    connector_match = re.match(r"^\s*(and|or|but)\b", source_text, flags=re.IGNORECASE)
                    connector = connector_match.group(1).lower() if connector_match else "and"
                    pronoun = "they" if actor.lower().endswith("s") else actor
                    active_text = re.sub(
                        rf"^\s*{re.escape(actor)}\b",
                        f"{connector} {pronoun}",
                        active_text,
                        flags=re.IGNORECASE,
                    )
                new_subject = self._extract_actor_from_active_text(active_text) or actor
                if self._is_non_empty_subject(new_subject):
                    previous_subject = new_subject
                if self._is_non_empty_subject(source_actor):
                    previous_actor = source_actor
            elif starts_with_connector:
                # Connector row with model-provided subject:
                # enforce previous actor context if subject mismatches.
                if self._is_non_empty_subject(previous_actor):
                    detected_low = detected_subject.lower() if detected_subject else ""
                    actor_low = previous_actor.lower()
                    if actor_low not in detected_low:
                        # Rebuild from source with inherited actor, then convert to connector + pronoun style.
                        active_text = self._rewrite_source_with_actor(source_text, previous_actor)
                        connector_match = re.match(r"^\s*(and|or|but)\b", source_text, flags=re.IGNORECASE)
                        connector = connector_match.group(1).lower() if connector_match else "and"
                        pronoun = "they" if previous_actor.lower().endswith("s") else previous_actor
                        active_text = re.sub(
                            rf"^\s*{re.escape(previous_actor)}\b",
                            f"{connector} {pronoun}",
                            active_text,
                            flags=re.IGNORECASE,
                        )

            # Guard: if source is already active with explicit subject, keep source text.
            # This prevents LLM from changing legal subject (e.g. "measures" -> "provider").
            if source_is_active and not starts_with_connector:
                active_text = source_text
            # Skip stage-3 rewriting for non-passive clauses to avoid hallucinated rewrites.
            if not source_is_passive:
                active_text = source_text

            # Guard: imperative prohibition should not be role-inverted by LLM.
            if source_is_negative_imperative and not starts_with_connector and source_is_passive:
                imperative_actor = source_actor if self._is_trusted_actor_for_imperative(source_actor) else ""
                if not imperative_actor and self._is_trusted_actor_for_imperative(previous_actor):
                    imperative_actor = previous_actor
                active_text = self._rewrite_negative_imperative(
                    source_text,
                    actor_hint=imperative_actor,
                )
            elif source_is_positive_imperative and not starts_with_connector and source_is_passive:
                imperative_actor = source_actor if self._is_trusted_actor_for_imperative(source_actor) else ""
                if not imperative_actor and self._is_trusted_actor_for_imperative(previous_actor):
                    imperative_actor = previous_actor
                active_text = self._rewrite_positive_imperative(
                    source_text,
                    actor_hint=imperative_actor,
                )

            # Preserve leading when/if/where condition from source when omitted by the model.
            active_text = self._ensure_condition_presence(active_text, source_text)

            # Resolve pronouns against available actor/object context.
            active_text = self._resolve_pronouns_in_text(
                active_text,
                actor_hint=(previous_actor or source_actor or detected_subject),
                object_hint=(previous_object or source_object),
                source_text=source_text,
            )

            # Refresh context from source grammatical subject whenever available.
            if self._is_non_empty_subject(source_subject):
                previous_subject = source_subject

            # Always normalize malformed modal constructions from model output.
            active_text = self._normalize_modal_verb_form(active_text)
            active_text = self._collapse_duplicated_leading_subject(active_text)

            processed.append({"ID": node_id, "Active_Recovered_Text": active_text})

        return processed

    @staticmethod
    def _tokenize_words(value: str) -> set[str]:
        """
        Tokenize into lowercase lexical words used for simple invention checks.
        """
        return set(re.findall(r"[A-Za-z][A-Za-z0-9_'-]*", str(value).lower()))

    def _group_by_article_paragraph(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            article = str(row.get("Article", "")).strip()
            paragraph = str(row.get("Paragraph", "")).strip()
            reg_id = str(row.get("ID", "")).strip()
            text = self._normalize_text(str(row.get("Text", "")))
            if not article or not paragraph or not reg_id or not text:
                continue
            key = (article, paragraph)
            grouped.setdefault(key, []).append(row)

        out: list[dict[str, Any]] = []
        for (article, paragraph), members in grouped.items():
            members_sorted = sorted(members, key=lambda r: self._reg_sort_key(str(r.get("ID", ""))))
            out.append(
                {
                    "article": article,
                    "paragraph": paragraph,
                    "nodes": members_sorted,
                }
            )

        out.sort(key=lambda g: (int(g["article"]) if str(g["article"]).isdigit() else 10**9, str(g["paragraph"])))
        return out

    def _build_user_prompt_for_group(self, group: dict[str, Any]) -> str:
        article = str(group.get("article", "")).strip()
        paragraph = str(group.get("paragraph", "")).strip()
        nodes = group.get("nodes", [])

        lines: list[str] = []
        lines.append(f"Article: {article}")
        lines.append(f"Paragraph: {paragraph}")
        lines.append("")
        lines.append("Nodes:")

        for row in nodes:
            reg_id = str(row.get("ID", "")).strip()
            text = self._normalize_text(str(row.get("Text", "")))
            parent = str(row.get("parent", "")).strip()
            logic_relations = row.get("logic_relations", [])

            lines.append(f"Node ID: {reg_id}")
            lines.append(f"Text: {text}")
            if parent and parent.lower() != "none":
                lines.append(f"Parent: {parent}")
            if isinstance(logic_relations, list) and logic_relations:
                lines.append("Logic Relations:")
                for rel in logic_relations:
                    if not isinstance(rel, dict):
                        continue
                    rel_type = str(rel.get("type", "")).strip()
                    target = str(rel.get("target", "")).strip()
                    if rel_type or target:
                        lines.append(f"- {rel_type} -> {target}")
            lines.append("")

        lines.append("Return only the JSON array.")
        return "\n".join(lines).strip()

    def _call_ollama(self, user_prompt: str) -> str:
        return self._call_ollama_with_system(self.SYSTEM_PROMPT, user_prompt)

    def _call_ollama_with_system(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self.temperature,
            },
        }

        request = urllib.request.Request(
            url=self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
        envelope = json.loads(raw)
        message = envelope.get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else ""
        return str(content).strip()

    @staticmethod
    def _extract_json_array_from_text(text: str) -> list[dict[str, Any]]:
        cleaned = str(text).strip()

        # 1) direct
        try:
            payload = json.loads(cleaned)
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
        except json.JSONDecodeError:
            pass

        # 2) fenced
        fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate = fenced.group(1)
            payload = json.loads(candidate)
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]

        # 3) first array span
        span = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
        if span:
            payload = json.loads(span.group(0))
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]

        raise ValueError("Could not parse JSON array from model output.")

    @staticmethod
    def _extract_passive_active_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            reg_id = str(row.get("ID", "")).strip()
            recovered = str(row.get("Active_Recovered_Text", "")).strip()
            if not recovered:
                recovered = str(row.get("Recovered_Text", "")).strip()
            if not reg_id and "id" in row:
                reg_id = str(row.get("id", "")).strip()
            if not recovered and "active_recovered_text" in row:
                recovered = str(row.get("active_recovered_text", "")).strip()
            if not recovered and "recovered_text" in row:
                recovered = str(row.get("recovered_text", "")).strip()
            if not reg_id:
                continue
            out.append({"ID": reg_id, "Active_Recovered_Text": recovered})
        return out

    @staticmethod
    def _extract_text_rewrite_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            reg_id = str(row.get("ID", "")).strip()
            if not reg_id and "id" in row:
                reg_id = str(row.get("id", "")).strip()
            text = str(row.get("Text", "")).strip()
            if not text:
                text = str(row.get("Resolved_Text", "")).strip()
            if not text and "text" in row:
                text = str(row.get("text", "")).strip()
            if not text and "resolved_text" in row:
                text = str(row.get("resolved_text", "")).strip()
            if not reg_id:
                continue
            out.append({"ID": reg_id, "Text": text})
        return out

    @staticmethod
    def _build_passive_to_active_prompt(nodes: list[dict[str, Any]]) -> str:
        prompt_payload = {"nodes": nodes}
        return (
            "### Input Nodes\n"
            + json.dumps(prompt_payload, indent=2, ensure_ascii=False)
            + "\n\nReturn only the JSON array."
        )

    @staticmethod
    def _has_explicit_subject_before_modal(text: str, modal_terms: list[str]) -> bool:
        clean = DeonticSlotExtractorLlama._normalize_text(text)
        if not clean:
            return False
        text_wo_connector = re.sub(r"^\s*(and|or|but)\s+", "", clean, flags=re.IGNORECASE)
        modal_alt = "|".join(re.escape(term) for term in modal_terms)
        match = re.search(rf"^(.+?)\s+(?:{modal_alt})\b", text_wo_connector, flags=re.IGNORECASE)
        if not match:
            return False
        subject_part = DeonticSlotExtractorLlama._normalize_text(match.group(1))
        return bool(subject_part)

    def _inject_missing_subject_for_connector_rows(
        self,
        nodes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Deterministic repair after call #1:
        if connector row still has no explicit subject, inherit previous node subject.
        """
        repaired: list[dict[str, Any]] = []
        previous_subject = ""
        modal_terms = self._modal_signal_terms()
        by_id: dict[str, dict[str, Any]] = {}
        for node in nodes:
            if isinstance(node, dict):
                node_id = str(node.get("ID", "")).strip()
                if node_id:
                    by_id[node_id] = node

        for node in nodes:
            if not isinstance(node, dict):
                continue
            copied = dict(node)
            text = self._normalize_text(str(copied.get("Text", "")))
            starts_with_connector = self._source_starts_with_connector(text)

            subject = self._extract_subject_phrase(text)
            if self._is_non_empty_subject(subject):
                previous_subject = subject

            if starts_with_connector and text:
                has_subject = self._has_explicit_subject_before_modal(text, modal_terms)
                if not has_subject and self._is_non_empty_subject(previous_subject):
                    connector_match = re.match(r"^\s*(and|or|but)\b", text, flags=re.IGNORECASE)
                    connector = connector_match.group(1).lower() if connector_match else "and"
                    text_wo_connector = re.sub(r"^\s*(and|or|but)\s+", "", text, flags=re.IGNORECASE)
                    text = f"{connector} {previous_subject} {text_wo_connector}".strip()
                elif not has_subject:
                    # Try target-linked inheritance from logic relations when local previous is unavailable.
                    rels = copied.get("logic_relations", [])
                    inherited = ""
                    if isinstance(rels, list):
                        for rel in rels:
                            if not isinstance(rel, dict):
                                continue
                            target = str(rel.get("target", "")).strip()
                            target_node = by_id.get(target, {})
                            target_text = self._normalize_text(str(target_node.get("Text", "")))
                            candidate = self._extract_subject_phrase(target_text)
                            if self._is_non_empty_subject(candidate):
                                inherited = candidate
                                break
                    if inherited:
                        connector_match = re.match(r"^\s*(and|or|but)\b", text, flags=re.IGNORECASE)
                        connector = connector_match.group(1).lower() if connector_match else "and"
                        text_wo_connector = re.sub(r"^\s*(and|or|but)\s+", "", text, flags=re.IGNORECASE)
                        text = f"{connector} {inherited} {text_wo_connector}".strip()

            copied["Text"] = text
            repaired.append(copied)

        return repaired

    def _resolve_anaphora_in_chain(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Rule-based anaphora resolution across legal node chains:
        - resolve actor pronouns from previous actor
        - resolve object pronouns from previous object
        """
        resolved: list[dict[str, Any]] = []
        previous_actor = ""
        previous_object = ""

        for node in nodes:
            if not isinstance(node, dict):
                continue
            copied = dict(node)
            text = self._normalize_text(str(copied.get("Text", "")))
            if not text:
                resolved.append(copied)
                continue

            subject = self._extract_subject_phrase(text)
            if self._is_non_empty_subject(subject):
                previous_actor = subject

            obj = self._extract_object_phrase(text)
            if obj:
                previous_object = obj

            actor_hint = previous_actor or self._infer_actor_candidate_from_source(text)
            object_hint = previous_object or self._infer_object_candidate_from_source(text)
            text = self._resolve_pronouns_in_text(
                text,
                actor_hint=actor_hint,
                object_hint=object_hint,
                source_text=text,
            )
            copied["Text"] = text

            # refresh context on resolved text
            resolved_subject = self._extract_subject_phrase(text)
            if self._is_non_empty_subject(resolved_subject):
                previous_actor = resolved_subject
            resolved_object = self._extract_object_phrase(text)
            if resolved_object:
                previous_object = resolved_object

            resolved.append(copied)
        return resolved

    def _normalize_stage1_modal_phrases(self, text: str) -> str:
        """
        Stage-1 modal normalization:
        - "is to be"  -> "shall"
        - "are to be" -> "shall"
        """
        value = self._normalize_text(text)
        if not value:
            return value
        value = re.sub(r"\bis\s+to\s+be\b", "shall", value, flags=re.IGNORECASE)
        value = re.sub(r"\bare\s+to\s+be\b", "shall", value, flags=re.IGNORECASE)
        return self._normalize_text(value)

    def resolve_anaphora_and_missing_actor(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Stage 1 (rule-based only):
        1) missing actor on connector fragments
        2) anaphora resolution in legal chains
        Keeps passive voice and legal force unchanged.
        """
        normalized_nodes: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            copied = dict(node)
            copied["Text"] = self._normalize_stage1_modal_phrases(str(copied.get("Text", "")))
            normalized_nodes.append(copied)

        with_subjects = self._inject_missing_subject_for_connector_rows(normalized_nodes)
        return self._resolve_anaphora_in_chain(with_subjects)

    def make_passive_to_active(self, nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Transform passive voice nodes to active voice action statements via Llama/Ollama.
        Input nodes should include at least: {"ID": "...", "Text": "..."}.
        """
        user_prompt = self._build_passive_to_active_prompt(nodes)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                content = self._call_ollama_with_system(self.passive_to_active_system_prompt, user_prompt)
                raw_rows = self._extract_json_array_from_text(content)
                extracted = self._extract_passive_active_rows(raw_rows)
                return self._postprocess_passive_active_rows(nodes, extracted)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 * attempt, 5))
        raise RuntimeError(f"Failed passive->active recovery after retries: {last_error}")

    def make_passive_to_active_two_calls(self, nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Two-call pipeline requested:
        1) anaphora + missing actor (keeps passive voice)
        2) passive->active conversion
        3) pronoun resolution is applied in post-processing of step 2
        """
        stage1_nodes = self.resolve_anaphora_and_missing_actor(nodes)
        return self.make_passive_to_active(stage1_nodes)

    @staticmethod
    def _quick_passive_checks(output_rows: list[dict[str, str]]) -> dict[str, Any]:
        checks = {
            "empty_outputs": [],
            "has_shall_reported_error": [],
            "has_shall_withdrawn_error": [],
            "has_unresolved_they": [],
        }
        for row in output_rows:
            reg_id = str(row.get("ID", "")).strip()
            text = str(row.get("Active_Recovered_Text", "")).strip().lower()
            if not text:
                checks["empty_outputs"].append(reg_id)
            if "shall reported" in text:
                checks["has_shall_reported_error"].append(reg_id)
            if "shall withdrawn" in text:
                checks["has_shall_withdrawn_error"].append(reg_id)
            if re.search(r"\bthey\b", text):
                checks["has_unresolved_they"].append(reg_id)

        checks["passed"] = (
            not checks["empty_outputs"]
            and not checks["has_shall_reported_error"]
            and not checks["has_shall_withdrawn_error"]
            and not checks["has_unresolved_they"]
        )
        return checks

    @staticmethod
    def _build_pipeline_nodes_from_group(group: dict[str, Any]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for row in group.get("nodes", []):
            if not isinstance(row, dict):
                continue
            node: dict[str, Any] = {
                "ID": str(row.get("ID", "")).strip(),
                "Text": DeonticSlotExtractorLlama._normalize_text(str(row.get("Text", ""))),
            }
            if isinstance(row.get("logic_relations"), list) and row.get("logic_relations"):
                node["logic_relations"] = row.get("logic_relations", [])
            if str(row.get("parent", "")).strip():
                node["parent"] = str(row.get("parent", "")).strip()
            if node["ID"] and node["Text"]:
                nodes.append(node)
        return nodes

    def run_passive_active_pipeline_on_file(self, input_json: str | Path, output_json: str | Path) -> Path:
        """
        Run two-call passive->active pipeline on file input grouped by same Article+Paragraph.
        Output format mirrors llama_live_test_report style.
        """
        input_path = Path(input_json).expanduser().resolve()
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = self._load_requirements(input_path)
        groups = self._group_by_article_paragraph(rows)

        scenario_results: list[dict[str, Any]] = []
        for group in groups:
            article = str(group.get("article", "")).strip()
            paragraph = str(group.get("paragraph", "")).strip()
            scenario_name = f"article_{article}_paragraph_{paragraph}"
            input_nodes = self._build_pipeline_nodes_from_group(group)
            if not input_nodes:
                scenario_results.append(
                    {
                        "scenario": scenario_name,
                        "article": article,
                        "paragraph": paragraph,
                        "input_nodes": [],
                        "stage1_output": [],
                        "output": [],
                        "checks": {"passed": False},
                        "status": "warning",
                        "error": "No valid nodes in group.",
                    }
                )
                continue

            try:
                stage1_nodes = self.resolve_anaphora_and_missing_actor(input_nodes)
                stage2_output = self.make_passive_to_active(stage1_nodes)
                checks = self._quick_passive_checks(stage2_output)
                scenario_results.append(
                    {
                        "scenario": scenario_name,
                        "article": article,
                        "paragraph": paragraph,
                        "input_nodes": input_nodes,
                        "stage1_output": stage1_nodes,
                        "output": stage2_output,
                        "checks": checks,
                        "status": "ok" if checks["passed"] else "warning",
                    }
                )
            except Exception as exc:
                scenario_results.append(
                    {
                        "scenario": scenario_name,
                        "article": article,
                        "paragraph": paragraph,
                        "input_nodes": input_nodes,
                        "stage1_output": [],
                        "output": [],
                        "checks": {"passed": False},
                        "status": "error",
                        "error": str(exc),
                    }
                )

        payload = {
            "test_type": "passive_active_file_pipeline",
            "model": self.model_name,
            "endpoint": self.endpoint_url,
            "input_file": str(input_path),
            "scenario_count": len(scenario_results),
            "results": scenario_results,
        }
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def test_passive_to_active(self, output_json: str | Path | None = None) -> dict[str, Any]:
        """
        Test method with 3 passive nodes, including an 'and ...' continuation
        to validate logic-relation actor inheritance behavior.
        """
        test_nodes = [
            {
                "ID": "REG-118",
                "Text": "When such deployers find that a high-risk AI system presents a risk, that system shall not be used.",
            },
            {
                "ID": "REG-119",
                "Text": "and shall be reported to the provider or the distributor.",
                "logic_relations": [{"type": "AND", "target": "REG-118"}],
            },
            {
                "ID": "REG-120",
                "Text": "The technical documentation shall be drawn up before that system is placed on the market.",
            },
        ]

        recovered = self.make_passive_to_active(test_nodes)
        payload = {
            "test_name": "passive_to_active_three_nodes",
            "model": self.model_name,
            "endpoint": self.endpoint_url,
            "input_nodes": test_nodes,
            "output": recovered,
        }

        if output_json is not None:
            out_path = Path(output_json).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return payload

    def _normalize_slot_rows(
        self,
        rows: list[dict[str, Any]],
        fallback_node_ids: list[str],
        article: str,
        paragraph: str,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            normalized: dict[str, Any] = {}
            for field in self.REQUIRED_FIELDS:
                value = row.get(field, "")
                # Backward compatibility for fallback LLM outputs that still use "deontic".
                if field == "modal" and (value is None or str(value).strip() == ""):
                    value = row.get("deontic", "")
                normalized[field] = self._normalize_text(str(value)) if value is not None else ""
            raw_action_list = row.get("action_list", [])
            if isinstance(raw_action_list, list):
                normalized["action_list"] = [
                    self._normalize_text(str(item))
                    for item in raw_action_list
                    if self._normalize_text(str(item))
                ]
            else:
                action_list_text = self._normalize_text(str(raw_action_list))
                normalized["action_list"] = [action_list_text] if action_list_text else []
            if not normalized["action_list"] and normalized.get("action"):
                normalized["action_list"] = [normalized["action"]]

            if not normalized["id"] and idx < len(fallback_node_ids):
                normalized["id"] = fallback_node_ids[idx]

            # Keep group metadata to make downstream debugging easier.
            normalized["article"] = article
            normalized["paragraph"] = paragraph
            out.append(normalized)

        # Ensure at least one output per node if model under-returns.
        known_ids = {str(item.get("id", "")).strip() for item in out}
        for node_id in fallback_node_ids:
            if node_id in known_ids:
                continue
            out.append(
                {
                    "id": node_id,
                    "actor": "",
                    "modal": "",
                    "action": "",
                    "action_list": [],
                    "object": "",
                    "temporal": "",
                    "manner": "",
                    "condition": "",
                    "article": article,
                    "paragraph": paragraph,
                }
            )
        return out

    def _build_group_source_vocab(self, group: dict[str, Any]) -> set[str]:
        """
        Build source vocabulary from all node texts in one (article, paragraph) group.
        """
        vocab: set[str] = set()
        nodes = group.get("nodes", [])
        for node in nodes:
            if not isinstance(node, dict):
                continue
            text = self._normalize_text(str(node.get("Text", "")))
            vocab.update(self._tokenize_words(text))
        return vocab

    def _annotate_invented_words(
        self,
        rows: list[dict[str, Any]],
        source_vocab: set[str],
    ) -> list[dict[str, Any]]:
        """
        Keep output rows unchanged (new-word debug fields removed).
        """
        _ = source_vocab
        return [dict(row) for row in rows]

    def _extract_condition_from_text(self, text: str) -> str:
        clean = self._normalize_text(text)
        if not clean:
            return ""
        match = re.search(r"\b((?:if|when|where|unless|provided that)\b[^,.;:]*)", clean, flags=re.IGNORECASE)
        if not match:
            return ""
        return self._normalize_text(match.group(1))

    def _find_modal_anchor(self, text: str) -> dict[str, Any]:
        clean = self._normalize_text(text)
        if not clean:
            return {"found": False}

        for phrase in self._modal_signal_terms():
            pattern = rf"\b{re.escape(phrase)}\b"
            match = re.search(pattern, clean, flags=re.IGNORECASE)
            if match:
                return {
                    "found": True,
                    "phrase": self._normalize_text(match.group(0)).lower(),
                    "start": match.start(),
                    "end": match.end(),
                    "before": self._normalize_text(clean[: match.start()]),
                    "after": self._normalize_text(clean[match.end() :]),
                }
        return {"found": False}

    @staticmethod
    def _clean_actor_candidate(actor: str) -> str:
        value = DeonticSlotExtractorLlama._normalize_text(actor)
        if not value:
            return ""
        bad = {"that", "which", "who", "it", "they", "them", "this", "those", "these"}
        if value.lower() in bad:
            return ""
        value = re.sub(r"^(?:for|to|of)\s+", "", value, flags=re.IGNORECASE)
        return DeonticSlotExtractorLlama._normalize_text(value)

    def _extract_actor_around_modal(self, text: str, anchor: dict[str, Any]) -> str:
        if not anchor.get("found"):
            return ""
        before = self._normalize_text(str(anchor.get("before", "")))
        if not before:
            return ""

        # Prefer nearest clause fragment before modal.
        fragments = [self._normalize_text(f) for f in re.split(r"[,;:]", before) if self._normalize_text(f)]
        candidate = fragments[-1] if fragments else before
        candidate = re.sub(r"^\s*(?:if|when|where|unless|provided that)\b[^,;:]*\b", "", candidate, flags=re.IGNORECASE)
        candidate = self._clean_actor_candidate(candidate)
        if candidate:
            return candidate

        # Fallback to full-subject extraction.
        return self._clean_actor_candidate(self._extract_subject_phrase(text))

    def _extract_action_object_around_modal(self, text: str, anchor: dict[str, Any]) -> tuple[str, str]:
        if not anchor.get("found"):
            return "", ""
        after = self._normalize_text(str(anchor.get("after", "")))
        if not after:
            return "", ""

        # Remove immediate negation token for action extraction.
        after_wo_neg = re.sub(r"^\s*not\b\s*", "", after, flags=re.IGNORECASE)
        # Pattern 1: be + participle / adjectival / nominal phrase
        be_match = re.match(r"^(?:be|being|been)\s+([a-z][a-z-]*)(.*)$", after_wo_neg, flags=re.IGNORECASE)
        if be_match:
            head = self._normalize_text(be_match.group(1))
            tail = self._normalize_text(be_match.group(2))
            # Passive-like verb phrase
            if re.search(r"(ed|en|n)$", head, flags=re.IGNORECASE):
                action = self._participle_to_base(head)
                obj = self._normalize_text(tail.lstrip(", "))
                return action, obj
            # Copular forms (e.g., be such that, be part of, be combined with)
            action = f"be {head}".strip()
            obj = self._normalize_text(tail.lstrip(", "))
            return action, obj

        # Pattern 2: direct lexical verb after modal
        vmatch = re.match(r"^([a-z][a-z-]*)(.*)$", after_wo_neg, flags=re.IGNORECASE)
        if not vmatch:
            return "", ""
        verb = self._normalize_text(vmatch.group(1)).lower()
        action = self._participle_to_base(verb)
        obj = self._normalize_text(vmatch.group(2).lstrip(", "))
        return action, obj

    def _extract_action_list_around_modal(self, text: str, anchor: dict[str, Any]) -> list[str]:
        if not anchor.get("found"):
            return []
        after = self._normalize_text(str(anchor.get("after", "")))
        if not after:
            return []

        after_wo_neg = re.sub(r"^\s*not\b\s*", "", after, flags=re.IGNORECASE)
        be_match = re.match(r"^(?:be|being|been)\s+([a-z][a-z-]*)(.*)$", after_wo_neg, flags=re.IGNORECASE)
        if be_match:
            head = self._normalize_text(be_match.group(1))
            if re.search(r"(ed|en|n)$", head, flags=re.IGNORECASE):
                return [self._participle_to_base(head)]
            return [self._normalize_text(f"be {head}")]

        vmatch = re.match(r"^([a-z][a-z-]*)(.*)$", after_wo_neg, flags=re.IGNORECASE)
        if not vmatch:
            return []

        stop_tokens = {
            "a",
            "an",
            "the",
            "to",
            "for",
            "of",
            "in",
            "on",
            "with",
            "into",
            "at",
            "by",
            "that",
            "which",
            "who",
            "if",
            "when",
            "where",
            "unless",
            "provided",
            "as",
        }
        actions = [self._participle_to_base(self._normalize_text(vmatch.group(1)).lower())]
        remaining = vmatch.group(2)
        while True:
            delimiter_match = re.match(r"^\s*(?:,\s*|\band\b\s+|\bor\b\s+)", remaining, flags=re.IGNORECASE)
            if not delimiter_match:
                break
            candidate_text = remaining[delimiter_match.end() :]
            next_match = re.match(r"^([a-z][a-z-]*)(.*)$", candidate_text, flags=re.IGNORECASE)
            if not next_match:
                break
            token = self._normalize_text(next_match.group(1)).lower()
            if token in stop_tokens:
                break
            actions.append(self._participle_to_base(token))
            remaining = next_match.group(2)

        deduped: list[str] = []
        seen: set[str] = set()
        for action in actions:
            normalized = self._normalize_text(action)
            lowered = normalized.lower()
            if not normalized or lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
        return deduped

    def _extract_temporal_from_text(self, text: str) -> str:
        clean = self._normalize_text(text)
        if not clean:
            return ""

        # 1) Rule-file phrase detection (exact phrase-first)
        for phrase in self._all_temporal_phrases():
            match = re.search(rf"\b{re.escape(phrase)}\b(?:\s+[A-Za-z0-9-]+){{0,5}}", clean, flags=re.IGNORECASE)
            if match:
                return self._normalize_text(match.group(0))

        # 2) spaCy detection for adverbial/prepositional temporal attachments
        # Example: "within 72 hours", "by 31 March", "during processing", "prior to deployment".
        if self._nlp is not None:
            try:
                doc = self._nlp(clean)
                temporal_heads = {
                    "within",
                    "by",
                    "before",
                    "after",
                    "during",
                    "until",
                    "upon",
                    "following",
                    "throughout",
                    "prior",
                    "subsequently",
                    "monthly",
                    "annually",
                    "periodically",
                    "regularly",
                    "continuous",
                    "iterative",
                    "then",
                    "first",
                    "finally",
                }
                for token in doc:
                    low = token.text.lower()
                    if low in temporal_heads and token.dep_ in {"prep", "advmod", "mark"}:
                        span = " ".join(t.text for t in token.subtree)
                        span = self._normalize_text(span)
                        if span:
                            return span
            except Exception:
                pass

        # 3) Regex fallback for common legal temporal patterns
        patterns = [
            r"\bwithin\s+\d+\s+(?:hour|hours|day|days|week|weeks|month|months|year|years)\b",
            r"\bby\s+\d{1,2}\s+\w+\b",
            r"\bno\s+later\s+than\b[^,.;:]*",
            r"\bat\s+the\s+latest\b[^,.;:]*",
            r"\bbefore\s+the\s+end\s+of\b[^,.;:]*",
            r"\bwithout\s+undue\s+delay\b",
            r"\bfrom\s+the\s+moment\b[^,.;:]*",
            r"\bat\s+the\s+time\s+of\b[^,.;:]*",
            r"\bfor\s+a\s+period\s+of\b[^,.;:]*",
            r"\bthroughout\b[^,.;:]*",
            r"\bduring\b[^,.;:]*",
            r"\bprior\s+to\b[^,.;:]*",
        ]
        for pattern in patterns:
            match = re.search(pattern, clean, flags=re.IGNORECASE)
            if match:
                return self._normalize_text(match.group(0))
        return ""

    def _extract_manner_from_text(self, text: str) -> str:
        clean = self._normalize_text(text)
        if not clean:
            return ""
        patterns = [
            r"\bin accordance with\b[^,.;]*",
            r"\bwith a view to\b[^,.;]*",
            r"\bby\b[^,.;]*",
            r"\bthrough\b[^,.;]*",
            r"\bvia\b[^,.;]*",
        ]
        for pattern in patterns:
            match = re.search(pattern, clean, flags=re.IGNORECASE)
            if match:
                return self._normalize_text(match.group(0))
        return ""

    def _extract_action_from_text(self, text: str) -> str:
        clean = self._normalize_text(text)
        if not clean:
            return ""

        if self._nlp is not None:
            try:
                doc = self._nlp(clean)
                modal_lemmas = {t.lower() for t in self._modal_signal_terms()}
                for token in doc:
                    if token.text.lower() in modal_lemmas or token.lemma_.lower() in modal_lemmas:
                        for child in token.children:
                            if child.pos_ == "VERB":
                                return self._normalize_text(child.lemma_)
                        # fallback to right neighbor verb
                        for right in token.rights:
                            if right.pos_ == "VERB":
                                return self._normalize_text(right.lemma_)
                # general fallback: first verb lemma
                for token in doc:
                    if token.pos_ == "VERB":
                        return self._normalize_text(token.lemma_)
            except Exception:
                pass

        match = re.search(
            r"\b(shall|must|may|should|can|will|requires)\b\s+(?:not\s+)?([a-z]+)\b",
            clean,
            flags=re.IGNORECASE,
        )
        if not match:
            return ""
        verb = self._normalize_text(match.group(2)).lower()
        if verb == "be":
            return ""
        return verb

    def _detect_deontic_from_text(self, text: str) -> str:
        clean = self._normalize_text(text).lower()
        if not clean:
            return ""
        # priority keeps stronger force first
        priority = [
            ("PROHIBITED", "Prohibited"),
            ("MANDATORY", "Mandatory"),
            ("PERMISSIVE", "Permissive"),
            ("ADVISORY", "Advisory"),
        ]
        for rule_key, label in priority:
            for phrase in self.modal_force_rules.get(rule_key, []):
                token = str(phrase).strip().lower()
                if token and re.search(rf"\b{re.escape(token)}\b", clean):
                    return label
        return ""

    def _detect_deontic_from_anchor(self, anchor_phrase: str) -> str:
        phrase = self._normalize_text(anchor_phrase).lower()
        if not phrase:
            return ""
        for rule_key, label in [
            ("PROHIBITED", "Prohibited"),
            ("MANDATORY", "Mandatory"),
            ("PERMISSIVE", "Permissive"),
            ("ADVISORY", "Advisory"),
        ]:
            for modal in self.modal_force_rules.get(rule_key, []):
                if phrase == self._normalize_text(modal).lower():
                    return label
        return ""

    def _extract_rule_based_slot_row(
        self,
        node: dict[str, Any],
        article: str,
        paragraph: str,
    ) -> tuple[dict[str, Any], dict[str, float]]:
        reg_id = str(node.get("ID", "")).strip()
        text = self._normalize_text(str(node.get("Text", "")))
        modal_anchor = self._find_modal_anchor(text)
        upstream_modal = self._normalize_text(str(node.get("Modal", "")))

        actor = self._extract_actor_around_modal(text, modal_anchor)
        if not actor:
            actor = self._clean_actor_candidate(self._extract_subject_phrase(text))
        if not actor:
            actor = self._clean_actor_candidate(self._infer_actor_candidate_from_source(text))

        modal = self._normalize_text(upstream_modal)
        action, obj = self._extract_action_object_around_modal(text, modal_anchor)
        action_list = self._extract_action_list_around_modal(text, modal_anchor)
        if not action:
            action = self._extract_action_from_text(text)
        if not action_list and action:
            action_list = [self._normalize_text(action)]
        if not obj:
            obj = self._extract_object_phrase(text) or self._infer_object_candidate_from_source(text)
        temporal = self._extract_temporal_from_text(text)
        manner = self._extract_manner_from_text(text)
        condition = self._extract_condition_from_text(text)

        row = {
            "id": reg_id,
            "text": text,
            "actor": self._normalize_text(actor),
            "modal": self._normalize_text(modal),
            "action": self._normalize_text(action),
            "action_list": action_list,
            "object": self._normalize_text(obj),
            "temporal": self._normalize_text(temporal),
            "manner": self._normalize_text(manner),
            "condition": self._normalize_text(condition),
            "article": article,
            "paragraph": paragraph,
            "source": "rule",
        }

        confidence = {
            "actor": 1.0 if row["actor"] else 0.0,
            "modal": 1.0 if row["modal"] else 0.0,
            "action": 1.0 if row["action"] else 0.0,
            "object": 1.0 if row["object"] else 0.0,
            "temporal": 0.7 if row["temporal"] else 0.0,
            "manner": 0.6 if row["manner"] else 0.0,
            "condition": 0.7 if row["condition"] else 0.0,
        }
        return row, confidence

    def _select_llm_fallback_ids(
        self,
        rule_rows: list[dict[str, Any]],
        confidence_rows: list[dict[str, float]],
    ) -> set[str]:
        fallback_ids: set[str] = set()
        for row, conf in zip(rule_rows, confidence_rows):
            reg_id = str(row.get("id", "")).strip()
            if not reg_id:
                continue
            critical = ["actor", "modal", "action", "object"]
            missing_critical = any(not str(row.get(field, "")).strip() for field in critical)
            score = sum(float(conf.get(field, 0.0)) for field in critical)
            text = self._normalize_text(str(row.get("text", "")))
            comma_count = text.count(",")
            token_count = len(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text))
            long_with_many_commas = comma_count >= 2 and token_count >= 20
            if missing_critical or score < 3.0 or long_with_many_commas:
                fallback_ids.add(reg_id)
        return fallback_ids

    def _merge_rule_and_llm_rows(
        self,
        rule_rows: list[dict[str, Any]],
        llm_rows: list[dict[str, Any]],
        fallback_ids: set[str],
    ) -> list[dict[str, Any]]:
        llm_by_id = {str(r.get("id", "")).strip(): r for r in llm_rows if str(r.get("id", "")).strip()}
        merged: list[dict[str, Any]] = []
        for base in rule_rows:
            reg_id = str(base.get("id", "")).strip()
            candidate = dict(base)
            if reg_id in fallback_ids and reg_id in llm_by_id:
                llm_row = llm_by_id[reg_id]
                for field in self.REQUIRED_FIELDS:
                    if field == "id":
                        continue
                    base_value = self._normalize_text(str(candidate.get(field, "")))
                    llm_value = self._normalize_text(str(llm_row.get(field, "")))
                    if not base_value and llm_value:
                        candidate[field] = llm_value
                candidate["source"] = "hybrid"
            merged.append(candidate)
        return merged

    def _extract_rule_based_slots_for_group(
        self,
        group: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, float]]]:
        article = str(group.get("article", "")).strip()
        paragraph = str(group.get("paragraph", "")).strip()
        rule_rows: list[dict[str, Any]] = []
        confidence_rows: list[dict[str, float]] = []
        for node in group.get("nodes", []):
            if not isinstance(node, dict):
                continue
            row, conf = self._extract_rule_based_slot_row(node, article=article, paragraph=paragraph)
            if str(row.get("id", "")).strip():
                rule_rows.append(row)
                confidence_rows.append(conf)
        return rule_rows, confidence_rows

    def extract_slots_for_group(self, group: dict[str, Any]) -> list[dict[str, Any]]:
        article = str(group.get("article", "")).strip()
        paragraph = str(group.get("paragraph", "")).strip()
        nodes = group.get("nodes", [])
        fallback_ids = [str(row.get("ID", "")).strip() for row in nodes if str(row.get("ID", "")).strip()]
        id_to_text = {
            str(row.get("ID", "")).strip(): self._normalize_text(str(row.get("Text", "")))
            for row in nodes
            if str(row.get("ID", "")).strip()
        }
        prompt = self._build_user_prompt_for_group(group)

        # Stage 4a: deterministic extraction (primary)
        rule_rows, confidence_rows = self._extract_rule_based_slots_for_group(group)
        llm_fallback_ids = self._select_llm_fallback_ids(rule_rows, confidence_rows)

        # Stage 4b: LLM fallback only for low-confidence rows
        llm_rows: list[dict[str, Any]] = []
        if llm_fallback_ids:
            last_error: Exception | None = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    content = self._call_ollama(prompt)
                    raw_rows = self._extract_json_array_from_text(content)
                    llm_rows = self._normalize_slot_rows(raw_rows, fallback_ids, article, paragraph)
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < self.max_retries:
                        time.sleep(min(2 * attempt, 5))
            if not llm_rows and last_error is not None:
                # keep rule-only output on fallback failure
                llm_rows = []

        # Stage 4c: merge + deterministic validation output schema
        merged_rows = self._merge_rule_and_llm_rows(rule_rows, llm_rows, llm_fallback_ids)

        # Ensure all input IDs appear at least once
        known_ids = {str(item.get("id", "")).strip() for item in merged_rows}
        for node_id in fallback_ids:
            if node_id in known_ids:
                continue
            merged_rows.append(
                {
                    "id": node_id,
                    "text": id_to_text.get(node_id, ""),
                    "actor": "",
                    "modal": "",
                    "action": "",
                    "action_list": [],
                    "object": "",
                    "temporal": "",
                    "manner": "",
                    "condition": "",
                    "article": article,
                    "paragraph": paragraph,
                    "source": "rule",
                }
            )

        source_vocab = self._build_group_source_vocab(group)
        return self._annotate_invented_words(merged_rows, source_vocab)

    def run(self, input_json: str | Path, output_json: str | Path) -> Path:
        input_path = Path(input_json).expanduser().resolve()
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = self._load_requirements(input_path)
        groups = self._group_by_article_paragraph(rows)

        merged_results: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        group_audit: list[dict[str, Any]] = []

        for group in groups:
            article = str(group.get("article", "")).strip()
            paragraph = str(group.get("paragraph", "")).strip()
            try:
                group_rows = self.extract_slots_for_group(group)
                merged_results.extend(group_rows)
                invented_union: set[str] = set()
                for row in group_rows:
                    for token in row.get("new_words", []):
                        invented_union.add(str(token))
                group_audit.append(
                    {
                        "article": article,
                        "paragraph": paragraph,
                        "newwords": len(invented_union) > 0,
                        "new_words": sorted(invented_union),
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "article": article,
                        "paragraph": paragraph,
                        "error": str(exc),
                    }
                )

        output_payload = {
            "input_file": str(input_path),
            "model": self.model_name,
            "endpoint": self.endpoint_url,
            "total_groups": len(groups),
            "total_rows": len(merged_results),
            "failures": failures,
            "group_newword_audit": group_audit,
            "results": merged_results,
        }

        output_path.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    extractor = DeonticSlotExtractorLlama(
        endpoint_url="http://localhost:11434/api/chat",
        model_name="llama3",
        timeout_seconds=240,
        max_retries=3,
        temperature=0.1,
    )

    # Call options:
    # 1) Slot extraction pipeline run:
    #    .venv/bin/python .../DeonticSlotExtractorLlama.py
    # 2) Passive->active single test run:
    #    .venv/bin/python .../DeonticSlotExtractorLlama.py --test-passive-active
    # 3) Passive->active file pipeline run (stage1->stage2->post):
    #    .venv/bin/python .../DeonticSlotExtractorLlama.py --run-passive-active-file
    # 4) Run all stages in one call (stage1->3 then stage4):
    #    .venv/bin/python .../DeonticSlotExtractorLlama.py --run-all-stages
    if "--test-passive-active" in sys.argv:
        test_output = (
            project_root
            / "intermediate_results"
            / "reg_eu_ai_act"
            / "passive_to_active_test_result.json"
        )
        payload = extractor.test_passive_to_active(output_json=test_output)
        print(f"Saved passive->active test result: {test_output}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if "--run-passive-active-file" in sys.argv:
        input_json = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_extended.json"
        output_json = (
            project_root
            / "intermediate_results"
            / "reg_eu_ai_act"
            / "eu_ai_requirements_extended_passive_active_report_llama3.json"
        )
        saved = extractor.run_passive_active_pipeline_on_file(input_json=input_json, output_json=output_json)
        print(f"Saved passive->active file report: {saved}")
        return

    if "--run-all-stages" in sys.argv:
        stage13_input = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_extended.json"
        stage13_output = (
            project_root
            / "intermediate_results"
            / "reg_eu_ai_act"
            / "eu_ai_requirements_extended_passive_active_report_llama3.json"
        )
        saved_stage13 = extractor.run_passive_active_pipeline_on_file(
            input_json=stage13_input,
            output_json=stage13_output,
        )
        print(f"Saved stage 1-3 report: {saved_stage13}")

        stage4_output = (
            project_root
            / "intermediate_results"
            / "reg_eu_ai_act"
            / "eu_ai_requirements_extended_slots_llama3.json"
        )
        saved_stage4 = extractor.run(input_json=stage13_output, output_json=stage4_output)
        print(f"Saved stage 4 slots: {saved_stage4}")
        return

    input_json = (
        project_root
        / "intermediate_results"
        / "reg_eu_ai_act"
        / "eu_ai_requirements_extended_passive_active_report_llama3.json"
    )
    output_json = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_extended_slots_llama3.json"

    # Default behavior convenience:
    # if stage 1-3 report is missing, create it first from extended requirements.
    if not input_json.exists():
        stage13_input = project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_extended.json"
        if not stage13_input.exists():
            raise FileNotFoundError(
                "Missing both stage 1-3 report and base requirements file:\n"
                f"- {input_json}\n"
                f"- {stage13_input}\n"
                "Run RequirementsExtractor_v2 first or provide the expected inputs."
            )
        saved_stage13 = extractor.run_passive_active_pipeline_on_file(
            input_json=stage13_input,
            output_json=input_json,
        )
        print(f"Stage 1-3 report was missing. Auto-generated: {saved_stage13}")

    saved = extractor.run(input_json=input_json, output_json=output_json)
    print(f"Saved slot extraction result: {saved}")


if __name__ == "__main__":
    main()
