from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from .DeonticSlotExtractorLlama import DeonticSlotExtractorLlama
except ImportError:  # pragma: no cover - fallback for direct script execution
    from DeonticSlotExtractorLlama import DeonticSlotExtractorLlama


class ReaDeonticStagePipeline:
    """
    Run REA chunk requirements through stage 1-4 by reusing DeonticSlotExtractorLlama:
    - stage 1: resolve_anaphora_and_missing_actor (rule-based)
    - stage 2: normalization pass (no-op pass-through for traceability)
    - stage 3: passive->active (LLM + deterministic guards)
    - stage 4: slot extraction (rule-first + LLM fallback hybrid)
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 240,
        max_retries: int = 3,
        temperature: float = 0.1,
    ) -> None:
        self.extractor = DeonticSlotExtractorLlama(
            endpoint_url=endpoint_url,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value)).strip()

    @staticmethod
    def _chunk_sort_key(path: Path) -> tuple[int, str]:
        match = re.search(r"chunk(\d+)", path.name, flags=re.IGNORECASE)
        if not match:
            return (10**9, path.name)
        return (int(match.group(1)), path.name)

    @staticmethod
    def _load_json_list(path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected list JSON in: {path}")
        return [row for row in payload if isinstance(row, dict)]

    def _find_chunk_requirement_file(self, chunk_dir: Path) -> Path | None:
        candidates = sorted(chunk_dir.glob("*_requirements.json"))
        if not candidates:
            return None
        return candidates[0]

    def _build_stage_nodes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for row in rows:
            reg_id = self._normalize_text(str(row.get("rea_id", "")))
            text = self._normalize_text(str(row.get("text", "")))
            if not reg_id or not text:
                continue
            nodes.append(
                {
                    "ID": reg_id,
                    "Text": text,
                }
            )
        return nodes

    def _split_nodes_for_stage_processing(self, input_nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Split each REA node into sentence/action units BEFORE stage-1 resolution.
        """
        split_nodes: list[dict[str, str]] = []
        for node in input_nodes:
            rea_id = self._normalize_text(str(node.get("ID", "")))
            text = self._normalize_text(str(node.get("Text", "")))
            if not rea_id or not text:
                continue
            split_nodes.extend(self._split_rea_text_for_stage4(rea_id=rea_id, text=text))
        return split_nodes

    def _detect_modal_with_signal(self, text: str) -> str:
        """
        Build REA modal in Force(signal) format, e.g. Mandatory(shall),
        using modal anchor helpers from the shared extractor.
        """
        anchor = self.extractor._find_modal_anchor(text)  # reuse existing modal anchor logic
        phrase = self._normalize_text(str(anchor.get("phrase", "")))
        if not phrase:
            return ""
        label = self.extractor._detect_deontic_from_anchor(phrase)  # label: Mandatory/Permissive/...
        if not label:
            label = self.extractor._detect_deontic_from_text(text)
        if not label:
            return ""
        return f"{label}({phrase})"

    def _split_into_sentences(self, text: str) -> list[str]:
        clean = self._normalize_text(text)
        if not clean:
            return []

        nlp = getattr(self.extractor, "_nlp", None)
        if nlp is not None:
            try:
                doc = nlp(clean)
                sents = [self._normalize_text(sent.text) for sent in doc.sents if self._normalize_text(sent.text)]
                if sents:
                    return sents
            except Exception:
                pass

        parts = re.split(r"(?<=[.!?])\s+", clean)
        return [self._normalize_text(part) for part in parts if self._normalize_text(part)]

    def _starts_with_main_action(self, text: str) -> bool:
        fragment = self._normalize_text(text)
        if not fragment:
            return False

        nlp = getattr(self.extractor, "_nlp", None)
        if nlp is not None:
            try:
                doc = nlp(fragment)
                first_token = next((token for token in doc if not token.is_space and not token.is_punct), None)
                if first_token is not None:
                    if first_token.pos_ == "VERB":
                        return True
                    if first_token.pos_ == "AUX":
                        return True
                    return False
            except Exception:
                pass

        first_word_match = re.match(r"^([A-Za-z][A-Za-z-]*)", fragment)
        if not first_word_match:
            return False
        first_word = first_word_match.group(1).lower()
        non_action_starters = {
            "a",
            "an",
            "the",
            "this",
            "that",
            "these",
            "those",
            "people",
            "organizations",
            "organisation",
            "organizations",
            "society",
            "system",
            "systems",
            "provider",
            "providers",
            "deployer",
            "deployers",
        }
        if first_word in non_action_starters:
            return False
        # Conservative fallback: only allow likely imperative/base-form starters.
        return bool(re.match(r"^(?:review|secure|update|assess|document|maintain|implement|establish|monitor|notify|inform|record|log|perform|complete|provide|use|ensure|verify|check|report)\b", first_word, flags=re.IGNORECASE))

    def _is_substantial_split_unit(self, text: str) -> bool:
        """
        Only split on connectors when the preceding fragment is already a
        meaningful clause rather than a bare coordinated verb.
        """
        fragment = self._normalize_text(text)
        if not fragment:
            return False
        if len(re.findall(r"[A-Za-z0-9_-]+", fragment)) >= 3:
            return True
        return bool(re.search(r"\b(?:shall|must|may|should|will|can)\b", fragment, flags=re.IGNORECASE))

    def _split_sentence_by_modal_or_action(self, sentence: str) -> list[str]:
        """
        Stage-4 REA splitting:
        1) split by semicolon first
        2) if multiple modal anchors exist, split at connector before next modal
        3) if a single modal governs coordinated verbs, keep that clause together
        4) no-modal action split fallback: split at connector + verb-start patterns
        """
        base = self._normalize_text(sentence)
        if not base:
            return []

        semicolon_parts = [self._normalize_text(p) for p in re.split(r";\s*", base) if self._normalize_text(p)]
        if not semicolon_parts:
            semicolon_parts = [base]

        modal_terms = self.extractor._modal_signal_terms()
        modal_alt = "|".join(re.escape(term) for term in modal_terms)
        out: list[str] = []

        for part in semicolon_parts:
            # Detect number of modal anchors in this part.
            modal_matches = list(re.finditer(rf"\b({modal_alt})\b", part, flags=re.IGNORECASE)) if modal_alt else []
            if len(modal_matches) > 1:
                # Split only where connector likely starts next modal clause.
                split_pattern = re.compile(
                    rf"\b(and|or|but|then)\b(?=\s+(?:not\s+)?(?:{modal_alt})\b)",
                    flags=re.IGNORECASE,
                )
                prev = 0
                for match in split_pattern.finditer(part):
                    chunk = self._normalize_text(part[prev:match.start()])
                    if chunk:
                        out.append(chunk)
                    prev = match.start()
                tail = self._normalize_text(part[prev:])
                if tail:
                    out.append(tail)
                continue

            # A single modal typically governs a coordinated verb list
            # (e.g. "shall establish, implement, document and maintain ...").
            # Keep it as one unit and let stage-4 action extraction recover
            # the verb list instead of splitting the clause here.
            if len(modal_matches) == 1:
                out.append(part)
                continue

            # No modal: optional action-oriented split for imperative chains.
            # Example: "Review ... and secure ..."
            action_split = re.split(
                r"\b(and|then)\b(?=\s+[A-Za-z][A-Za-z-]{2,}\b)",
                part,
                flags=re.IGNORECASE,
            )
            if len(action_split) > 1:
                merged_units: list[str] = []
                i = 0
                while i < len(action_split):
                    token = self._normalize_text(action_split[i])
                    if not token:
                        i += 1
                        continue
                    if token.lower() in {"and", "then"} and merged_units and i + 1 < len(action_split):
                        nxt = self._normalize_text(action_split[i + 1])
                        if nxt and self._starts_with_main_action(nxt) and self._is_substantial_split_unit(merged_units[-1]):
                            merged_units.append(f"{token} {nxt}".strip())
                        elif nxt:
                            merged_units[-1] = f"{merged_units[-1]} {token} {nxt}".strip()
                        i += 2
                        continue
                    merged_units.append(token)
                    i += 1

                # keep only meaningful units
                for unit in merged_units:
                    if len(re.findall(r"[A-Za-z0-9_-]+", unit)) >= 3:
                        out.append(unit)
                if merged_units:
                    continue

            out.append(part)

        return [self._normalize_text(unit) for unit in out if self._normalize_text(unit)]

    @staticmethod
    def _is_attachable_fragment(unit: str) -> bool:
        """
        Fragments that should stay attached to the previous main clause.
        """
        value = re.sub(r"^\s*[,;:]\s*", "", str(unit or "")).strip()
        if not value:
            return True
        return bool(
            re.match(
                r"^(and|or|but|if|when|where|unless|provided\s+that)\b",
                value,
                flags=re.IGNORECASE,
            )
        )

    def _split_rea_text_for_stage4(self, rea_id: str, text: str) -> list[dict[str, str]]:
        """
        Build stage-4 pseudo nodes from one REA text.
        One REA can produce multiple action units.
        """
        sentences = self._split_into_sentences(text)
        units: list[str] = []
        for sent in sentences:
            units.extend(self._split_sentence_by_modal_or_action(sent))
        if not units:
            units = [self._normalize_text(text)]

        # Re-attach connector/condition fragments to avoid broken standalone rows.
        merged_units: list[str] = []
        for unit in units:
            clean = self._normalize_text(unit)
            if not clean:
                continue
            if merged_units and self._is_attachable_fragment(clean):
                merged_units[-1] = self._normalize_text(f"{merged_units[-1]} {clean}")
            else:
                merged_units.append(clean)
        if merged_units:
            units = merged_units

        deduped_units: list[str] = []
        seen_units: set[str] = set()
        for unit in units:
            unit_text = self._normalize_text(unit)
            if not unit_text:
                continue
            dedup_key = unit_text.casefold()
            if dedup_key in seen_units:
                continue
            seen_units.add(dedup_key)
            deduped_units.append(unit_text)

        rows: list[dict[str, str]] = []
        for idx, unit in enumerate(deduped_units, start=1):
            unit_text = self._normalize_text(unit)
            if not unit_text:
                continue
            rows.append(
                {
                    "ID": f"{rea_id}#{idx}",
                    "REA_ID": rea_id,
                    "Text": unit_text,
                }
            )
        return rows

    def _resolve_split_nodes_for_stage4(self, split_nodes: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        After action/modal splitting, run stage-1 style repair again:
        - missing actor handling
        - anaphora resolution
        """
        if not split_nodes:
            return []

        # resolver expects ID/Text; keep a copy for REA_ID mapping
        id_to_rea: dict[str, str] = {}
        resolver_input: list[dict[str, str]] = []
        for node in split_nodes:
            node_id = self._normalize_text(str(node.get("ID", "")))
            rea_id = self._normalize_text(str(node.get("REA_ID", "")))
            text = self._normalize_text(str(node.get("Text", "")))
            if not node_id or not text:
                continue
            id_to_rea[node_id] = rea_id
            resolver_input.append({"ID": node_id, "Text": text})

        resolved = self.extractor.resolve_anaphora_and_missing_actor(resolver_input)
        out: list[dict[str, str]] = []
        for row in resolved:
            node_id = self._normalize_text(str(row.get("ID", "")))
            text = self._normalize_text(str(row.get("Text", "")))
            if not node_id or not text:
                continue
            out.append(
                {
                    "ID": node_id,
                    "REA_ID": id_to_rea.get(node_id, ""),
                    "Text": text,
                    "Modal": self._detect_modal_with_signal(text),
                }
            )
        return out

    def _build_stage4_group(self, chunk_name: str, stage3_rows: list[dict[str, str]]) -> dict[str, Any]:
        """
        Build stage-4 group directly from stage-3 split outputs.
        (No re-splitting or re-resolution here.)
        """
        group_nodes: list[dict[str, str]] = []
        for row in stage3_rows:
            node_id = self._normalize_text(str(row.get("ID", "")))
            text = self._normalize_text(str(row.get("Active_Recovered_Text", "")))
            if not node_id or not text:
                continue
            rea_id = node_id.split("#", 1)[0] if "#" in node_id else node_id
            group_nodes.append(
                {
                    "ID": node_id,
                    "REA_ID": rea_id,
                    "Text": text,
                    "Modal": self._detect_modal_with_signal(text),
                }
            )

        return {
            "article": chunk_name,   # for grouping compatibility
            "paragraph": "1",        # single pseudo-paragraph per chunk
            "nodes": group_nodes,
        }

    @staticmethod
    def _stage13_file_path(chunk_out_dir: Path, chunk_name: str) -> Path:
        return chunk_out_dir / f"{chunk_name}_stage1_3.json"

    @staticmethod
    def _stage4_file_path(chunk_out_dir: Path, chunk_name: str) -> Path:
        return chunk_out_dir / f"{chunk_name}_stage4_slots.json"

    @staticmethod
    def _combined_file_path(chunk_out_dir: Path, chunk_name: str) -> Path:
        return chunk_out_dir / f"{chunk_name}_deontic_stages.json"

    def run_chunk_stage1_3(self, chunk_dir: Path, output_root: Path) -> dict[str, Any]:
        chunk_name = chunk_dir.name
        req_file = self._find_chunk_requirement_file(chunk_dir)
        if req_file is None:
            return {
                "chunk": chunk_name,
                "status": "skipped",
                "error": "No *_requirements.json found",
            }

        req_rows = self._load_json_list(req_file)
        input_nodes = self._build_stage_nodes(req_rows)
        if not input_nodes:
            return {
                "chunk": chunk_name,
                "status": "skipped",
                "requirements_file": str(req_file),
                "error": "No valid REA rows with rea_id/text",
            }

        # Stage 1: split first
        stage1_output = self._split_nodes_for_stage_processing(input_nodes)

        # Stage 2: missing actor + anaphora resolution on split units
        stage2_output = self._resolve_split_nodes_for_stage4(stage1_output)

        # Stage 3: passive->active on stage2 text
        stage3_input = [{"ID": row["ID"], "Text": row["Text"]} for row in stage2_output if row.get("ID") and row.get("Text")]
        stage3_output = self.extractor.make_passive_to_active(stage3_input)

        chunk_out_dir = output_root / chunk_name
        chunk_out_dir.mkdir(parents=True, exist_ok=True)
        stage13_file = self._stage13_file_path(chunk_out_dir, chunk_name)
        stage13_payload = {
            "chunk": chunk_name,
            "requirements_file": str(req_file),
            "stage1_output": stage1_output,
            "stage2_output": stage2_output,
            "stage3_output": stage3_output,
        }
        stage13_file.write_text(json.dumps(stage13_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "chunk": chunk_name,
            "status": "ok",
            "requirements_file": str(req_file),
            "stage1_3_file": str(stage13_file),
            "input_nodes": len(input_nodes),
            "stage3_rows": len(stage3_output),
        }

    def run_chunk_stage4_from_stage3(
        self,
        chunk_dir: Path,
        output_root: Path,
        stage13_json_path: Path | None = None,
    ) -> dict[str, Any]:
        chunk_name = chunk_dir.name
        chunk_out_dir = output_root / chunk_name
        chunk_out_dir.mkdir(parents=True, exist_ok=True)

        source_file = stage13_json_path or self._stage13_file_path(chunk_out_dir, chunk_name)
        if not source_file.exists():
            return {
                "chunk": chunk_name,
                "status": "skipped",
                "error": f"Stage1-3 file not found: {source_file}",
            }

        payload = json.loads(source_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {
                "chunk": chunk_name,
                "status": "error",
                "error": f"Invalid Stage1-3 payload format: {source_file}",
            }

        stage3_output = payload.get("stage3_output", [])
        if not isinstance(stage3_output, list):
            return {
                "chunk": chunk_name,
                "status": "error",
                "error": f"Invalid stage3_output format in: {source_file}",
            }

        # Stage 4 from reviewed/edited stage3_output
        group = self._build_stage4_group(chunk_name=chunk_name, stage3_rows=stage3_output)
        stage4_output = self.extractor.extract_slots_for_group(group)

        # Map pseudo IDs back to REA ids and keep per-split traceability.
        for slot_row in stage4_output:
            slot_id = self._normalize_text(str(slot_row.get("id", "")))
            if "#" in slot_id:
                base, sub = slot_id.split("#", 1)
                slot_row["rea_id"] = base
                slot_row["sub_id"] = slot_id
                slot_row["id"] = base
                slot_row["split_index"] = sub

        stage4_file = self._stage4_file_path(chunk_out_dir, chunk_name)
        stage4_payload = {
            "chunk": chunk_name,
            "stage1_3_file": str(source_file),
            "stage4_output": stage4_output,
        }
        stage4_file.write_text(json.dumps(stage4_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # Combined output for backward compatibility.
        chunk_output_file = self._combined_file_path(chunk_out_dir, chunk_name)
        chunk_payload = {
            "chunk": chunk_name,
            "requirements_file": str(payload.get("requirements_file", "")),
            "stage1_3_file": str(source_file),
            "stage1_output": payload.get("stage1_output", []),
            "stage2_output": payload.get("stage2_output", []),
            "stage3_output": stage3_output,
            "stage4_output": stage4_output,
        }
        chunk_output_file.write_text(json.dumps(chunk_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "chunk": chunk_name,
            "status": "ok",
            "requirements_file": str(payload.get("requirements_file", "")),
            "stage1_3_file": str(source_file),
            "stage4_file": str(stage4_file),
            "output_file": str(chunk_output_file),
            "stage4_rows": len(stage4_output),
        }

    def run_chunk(self, chunk_dir: Path, output_root: Path) -> dict[str, Any]:
        stage13_result = self.run_chunk_stage1_3(chunk_dir=chunk_dir, output_root=output_root)
        if stage13_result.get("status") != "ok":
            return stage13_result
        stage4_result = self.run_chunk_stage4_from_stage3(
            chunk_dir=chunk_dir,
            output_root=output_root,
            stage13_json_path=Path(str(stage13_result["stage1_3_file"])),
        )
        merged = dict(stage13_result)
        merged.update(
            {
                "stage4_status": stage4_result.get("status"),
                "stage4_file": stage4_result.get("stage4_file", ""),
                "output_file": stage4_result.get("output_file", ""),
                "stage4_rows": stage4_result.get("stage4_rows", 0),
            }
        )
        return merged

    def run_folder(self, input_root: str | Path, output_root: str | Path, run_stage4: bool = True) -> Path:
        in_root = Path(input_root).expanduser().resolve()
        out_root = Path(output_root).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        chunk_dirs = [p for p in in_root.iterdir() if p.is_dir() and p.name.lower().startswith("chunk")]
        chunk_dirs = sorted(chunk_dirs, key=self._chunk_sort_key)

        results: list[dict[str, Any]] = []
        for chunk_dir in chunk_dirs:
            try:
                if run_stage4:
                    results.append(self.run_chunk(chunk_dir=chunk_dir, output_root=out_root))
                else:
                    results.append(self.run_chunk_stage1_3(chunk_dir=chunk_dir, output_root=out_root))
            except Exception as exc:
                results.append(
                    {
                        "chunk": chunk_dir.name,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        report_name = "rea_deontic_stages_report.json" if run_stage4 else "rea_stage1_3_report.json"
        merged_path = out_root / report_name
        merged_payload = {
            "input_root": str(in_root),
            "output_root": str(out_root),
            "chunk_count": len(chunk_dirs),
            "run_stage4": run_stage4,
            "results": results,
        }
        merged_path.write_text(json.dumps(merged_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return merged_path

    def run_folder_stage1_3(self, input_root: str | Path, output_root: str | Path) -> Path:
        return self.run_folder(input_root=input_root, output_root=output_root, run_stage4=False)

    def run_folder_stage4_from_saved_stage3(self, input_root: str | Path, output_root: str | Path) -> Path:
        in_root = Path(input_root).expanduser().resolve()
        out_root = Path(output_root).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        chunk_dirs = [p for p in in_root.iterdir() if p.is_dir() and p.name.lower().startswith("chunk")]
        chunk_dirs = sorted(chunk_dirs, key=self._chunk_sort_key)

        results: list[dict[str, Any]] = []
        for chunk_dir in chunk_dirs:
            try:
                results.append(self.run_chunk_stage4_from_stage3(chunk_dir=chunk_dir, output_root=out_root))
            except Exception as exc:
                results.append(
                    {
                        "chunk": chunk_dir.name,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        merged_path = out_root / "rea_stage4_from_saved_stage3_report.json"
        merged_payload = {
            "input_root": str(in_root),
            "output_root": str(out_root),
            "chunk_count": len(chunk_dirs),
            "results": results,
        }
        merged_path.write_text(json.dumps(merged_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return merged_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    input_root = project_root / "intermediate_results" / "rea_case3_injections"
    output_root = project_root / "intermediate_results" / "rea_case3_injections_deontic_stages"

    runner = ReaDeonticStagePipeline(
        endpoint_url="http://localhost:11434/api/chat",
        model_name="llama3",
        timeout_seconds=240,
        max_retries=3,
        temperature=0.1,
    )
    saved = runner.run_folder(input_root=input_root, output_root=output_root)
    print(f"Saved REA stage report: {saved}")


if __name__ == "__main__":
    main()
