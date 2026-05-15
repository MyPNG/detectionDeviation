from __future__ import annotations

import csv
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from common.io_text import load_json, normalize_spaces

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ReadableLlmResponse = importlib.import_module(
    "pipeline.02_processing.03_reasoning.ReadableLlmResponse"
).ReadableLlmResponse


class EndResultExtractor:
    """
    Build the final deviation/compliance report from LLM response files.

    Input:
    - a prompt output folder, e.g. intermediate_results/02_processing/03_reasoning/reapromptpreparation/prompts_rea_no_injections__reg
    - response files named step4_prompt_payload*_llm_response.json

    Output:
    - output/<run_name>/<run_name>_end_results.csv
    - output/<run_name>/<run_name>_end_results.md
    """

    CSV_FIELDS = [
        "chunk",
        "rea_id",
        "rea_text",
        "reg_id",
        "reg_article",
        "reg_text",
        "deviation",
        "confidence",
        "needs_more_context",
        "types",
        "compliance_status",
        "reasoning_short",
        "evidence_rea",
        "evidence_reg",
        "response_file",
        "prompt_file",
        "reranked_file",
    ]

    def __init__(
        self,
        project_root: str | Path,
        drop_columns: list[str] | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        self.response_parser = ReadableLlmResponse()
        self.drop_columns = set(drop_columns or ["reranked_file", "prompt_file", "response_file"])

    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return normalize_spaces(value)

    @staticmethod
    def _load_json(path: Path) -> Any:
        return load_json(path)

    @staticmethod
    def _run_name_from_prompt_root(prompt_root: Path) -> str:
        name = prompt_root.name.strip()
        if name.startswith("prompts_"):
            return name[len("prompts_") :]
        return name

    @staticmethod
    def _chunk_from_response_path(response_path: Path, prompt_root: Path) -> str:
        try:
            relative = response_path.relative_to(prompt_root)
        except ValueError:
            return ""
        return relative.parts[0] if relative.parts else ""

    @staticmethod
    def _join_list(value: Any) -> str:
        if isinstance(value, list):
            return " | ".join(normalize_spaces(item) for item in value if normalize_spaces(item))
        text = normalize_spaces(value)
        return text

    @staticmethod
    def _article_number_from_clause(value: Any) -> str:
        text = normalize_spaces(value)
        match = re.search(r"Art\s*(\d+)", text, flags=re.IGNORECASE)
        return match.group(1) if match else ""

    @classmethod
    def _format_clause_display(cls, clause: Any) -> str:
        """
        Prefer clause-level display (e.g. Art14(5(d))).
        Fallback to article-level display when only article number is available.
        """
        text = cls._normalize_spaces(clause)
        if not text:
            return ""
        # already a legal location form
        if re.search(r"^Art\s*\d+", text, flags=re.IGNORECASE):
            return text
        # raw number like "14" -> "Art14"
        if text.isdigit():
            return f"Art{text}"
        # mixed forms that still include article number
        article_num = cls._article_number_from_clause(text)
        if article_num:
            return text
        return text

    @classmethod
    def _compliance_status(cls, *, deviation: bool, confidence: str, needs_more_context: bool) -> str:
        normalized_conf = cls._normalize_spaces(confidence).lower()
        if deviation:
            return "potential violation"
        if normalized_conf in {"high", "medium"} and not needs_more_context:
            return "compliant"
        return "needs manual review"

    def _parse_prompt_payload(self, prompt_json_path: Path) -> dict[str, Any]:
        if not prompt_json_path.exists():
            return {}
        payload = self._load_json(prompt_json_path)
        return payload if isinstance(payload, dict) else {}

    def _load_reranked_payload(self, prompt_payload: dict[str, Any]) -> dict[str, Any]:
        reranked_raw = self._normalize_spaces(prompt_payload.get("reranked_json", ""))
        if not reranked_raw:
            return {}
        reranked_path = Path(reranked_raw).expanduser().resolve()
        if not reranked_path.exists():
            return {}
        payload = self._load_json(reranked_path)
        return payload if isinstance(payload, dict) else {}

    def _build_reg_metadata_map(
        self,
        *,
        prompt_payload: dict[str, Any],
        reranked_payload: dict[str, Any],
    ) -> dict[str, dict[str, str]]:
        metadata: dict[str, dict[str, str]] = {}

        matches = reranked_payload.get("top matches", [])
        if isinstance(matches, list):
            for row in matches:
                if not isinstance(row, dict):
                    continue
                reg_id = self._normalize_spaces(row.get("ID", ""))
                if not reg_id:
                    continue
                clause = self._normalize_spaces(row.get("article", ""))
                metadata[reg_id] = {
                    "reg_article": self._format_clause_display(clause),
                    "reg_article_num": self._article_number_from_clause(clause),
                    "reg_clause": clause,
                    "reg_text": self._normalize_spaces(row.get("text", row.get("Text", ""))),
                }

        graph_context = prompt_payload.get("graph_context", {})
        main_constraints = graph_context.get("main_constraints", []) if isinstance(graph_context, dict) else []
        if isinstance(main_constraints, list):
            for row in main_constraints:
                if not isinstance(row, dict):
                    continue
                reg_id = self._normalize_spaces(row.get("id", ""))
                if not reg_id:
                    continue
                existing = metadata.setdefault(reg_id, {"reg_article": "", "reg_clause": "", "reg_text": ""})
                clause = self._normalize_spaces(row.get("clause", ""))
                if clause and not existing.get("reg_clause"):
                    existing["reg_clause"] = clause
                if clause and not existing.get("reg_article"):
                    existing["reg_article"] = self._format_clause_display(clause)
                if clause and not existing.get("reg_article_num"):
                    existing["reg_article_num"] = self._article_number_from_clause(clause)
                text = self._normalize_spaces(row.get("text", ""))
                if text and not existing.get("reg_text"):
                    existing["reg_text"] = text

        return metadata

    def _extract_rea_text(self, *, prompt_payload: dict[str, Any], reranked_payload: dict[str, Any]) -> str:
        search_query = self._normalize_spaces(reranked_payload.get("search query", ""))
        if search_query:
            return search_query

        user_prompt = str(prompt_payload.get("user_prompt", ""))
        match = re.search(r'REA FOCUS UNIT\s+id:\s*[^\n]+\s+text:\s*"([^"]*)"', user_prompt, flags=re.DOTALL)
        if match:
            return self._normalize_spaces(match.group(1))
        return ""

    def _rows_from_response_file(self, response_path: Path, prompt_root: Path) -> list[dict[str, str]]:
        raw_payload = self._load_json(response_path)
        if not isinstance(raw_payload, dict):
            return []

        decision = self.response_parser._extract_decision(raw_payload)
        prompt_json_raw = self._normalize_spaces(decision.get("prompt_json", raw_payload.get("prompt_json", "")))
        if prompt_json_raw:
            prompt_json_path = Path(prompt_json_raw).expanduser().resolve()
        else:
            # Generic fallback supports both:
            # - step4_prompt_payload_llm_response.json
            # - step4_prompt_payload_01_llm_response.json
            fallback_name = response_path.name.replace("_llm_response.json", ".json")
            prompt_json_path = response_path.with_name(fallback_name)
        prompt_payload = self._parse_prompt_payload(prompt_json_path)
        reranked_payload = self._load_reranked_payload(prompt_payload)
        reg_metadata = self._build_reg_metadata_map(prompt_payload=prompt_payload, reranked_payload=reranked_payload)

        rea_id = self._normalize_spaces(decision.get("id", raw_payload.get("id", "")))
        rea_text = self._extract_rea_text(prompt_payload=prompt_payload, reranked_payload=reranked_payload)
        reranked_file = self._normalize_spaces(prompt_payload.get("reranked_json", ""))
        chunk = self._chunk_from_response_path(response_path, prompt_root)

        comparisons = decision.get("per_reg_comparisons", [])
        if not isinstance(comparisons, list):
            comparisons = []

        out: list[dict[str, str]] = []
        for comparison in comparisons:
            if not isinstance(comparison, dict):
                continue
            reg_id = self._normalize_spaces(comparison.get("reg_id", ""))
            deviation = bool(comparison.get("deviation", False))
            confidence = self._normalize_spaces(comparison.get("confidence", ""))
            needs_more_context = bool(comparison.get("needs_more_context", False))
            types = comparison.get("types", [])
            if not deviation:
                type_text = "none"
            else:
                type_text = self._join_list(types) or self._normalize_spaces(comparison.get("type", "")) or "unspecified"

            meta = reg_metadata.get(reg_id, {})
            reg_clause = self._normalize_spaces(meta.get("reg_clause", ""))
            reg_article = self._normalize_spaces(meta.get("reg_article", ""))
            if not reg_article:
                reg_article = self._format_clause_display(reg_clause)
            if not reg_article:
                article_num = self._normalize_spaces(meta.get("reg_article_num", "")) or self._article_number_from_clause(reg_clause)
                reg_article = f"Art{article_num}" if article_num else ""

            out.append(
                {
                    "chunk": chunk,
                    "rea_id": rea_id,
                    "rea_text": rea_text,
                    "reg_id": reg_id,
                    "reg_article": reg_article,
                    "reg_text": self._normalize_spaces(meta.get("reg_text", "")),
                    "deviation": str(deviation),
                    "confidence": confidence,
                    "needs_more_context": str(needs_more_context),
                    "types": type_text,
                    "compliance_status": self._compliance_status(
                        deviation=deviation,
                        confidence=confidence,
                        needs_more_context=needs_more_context,
                    ),
                    "reasoning_short": self._normalize_spaces(comparison.get("reasoning_short", "")),
                    "evidence_rea": self._join_list(comparison.get("evidence_rea", [])),
                    "evidence_reg": self._join_list(comparison.get("evidence_reg", [])),
                    "response_file": str(response_path),
                    "prompt_file": str(prompt_json_path),
                    "reranked_file": reranked_file,
                }
            )

        return out

    @staticmethod
    def _sort_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
        def key(row: dict[str, str]) -> tuple[str, int, int, int, str]:
            chunk = row.get("chunk", "")
            rea = row.get("rea_id", "")
            rea_match = re.search(r"REA-(\d+)(?:#(\d+))?", rea, flags=re.IGNORECASE)
            rea_main = int(rea_match.group(1)) if rea_match else 10**9
            rea_sub = int(rea_match.group(2) or 0) if rea_match else 10**9
            article = row.get("reg_article", "")
            article_match = re.search(r"(\d+)", article)
            article_num = int(article_match.group(1)) if article_match else 10**9
            return (chunk, rea_main, rea_sub, article_num, row.get("reg_id", ""))

        return sorted(rows, key=key)

    def _active_csv_fields(self, drop_columns: list[str] | None = None) -> list[str]:
        columns_to_drop = self.drop_columns if drop_columns is None else set(drop_columns)
        return [field for field in self.CSV_FIELDS if field not in columns_to_drop]

    def _write_csv(self, rows: list[dict[str, str]], output_csv: Path, drop_columns: list[str] | None = None) -> Path:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = self._active_csv_fields(drop_columns)
        with output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        return output_csv

    def _build_markdown(self, rows: list[dict[str, str]], prompt_root: Path, output_csv: Path) -> str:
        lines = [
            "# End Result Report",
            "",
            f"- prompt_root: {prompt_root}",
            f"- output_csv: {output_csv}",
            f"- total_mappings: {len(rows)}",
        ]

        lines.extend(
            [
                "",
                "## Overview",
                "",
                "| clause | REG | REA | status | deviation | confidence | needs context | type | reasoning |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )

        for row in rows:
            reasoning = row.get("reasoning_short", "").replace("|", "\\|")
            rea_text = row.get("rea_text", "").replace("|", "\\|")
            if len(rea_text) > 140:
                rea_text = rea_text[:137].rstrip() + "..."
            if len(reasoning) > 180:
                reasoning = reasoning[:177].rstrip() + "..."
            lines.append(
                "| {article} | {reg_id} | {rea_id}: {rea_text} | {status} | {deviation} | {confidence} | {needs} | {types} | {reasoning} |".format(
                    article=row.get("reg_article", ""),
                    reg_id=row.get("reg_id", ""),
                    rea_id=row.get("rea_id", ""),
                    rea_text=rea_text,
                    status=row.get("compliance_status", ""),
                    deviation=row.get("deviation", ""),
                    confidence=row.get("confidence", ""),
                    needs=row.get("needs_more_context", ""),
                    types=row.get("types", "").replace("|", "\\|"),
                    reasoning=reasoning,
                )
            )

        lines.append("")
        return "\n".join(lines)

    def _write_markdown(self, rows: list[dict[str, str]], prompt_root: Path, output_csv: Path, output_md: Path) -> Path:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(self._build_markdown(rows, prompt_root, output_csv), encoding="utf-8")
        return output_md

    def run(
        self,
        prompt_root: str | Path,
        output_root: str | Path | None = None,
        drop_columns: list[str] | None = None,
    ) -> dict[str, Any]:
        prompt_root_path = Path(prompt_root).expanduser().resolve()
        if not prompt_root_path.exists() or not prompt_root_path.is_dir():
            raise FileNotFoundError(f"Prompt root not found or not a directory: {prompt_root_path}")

        run_name = self._run_name_from_prompt_root(prompt_root_path)
        output_dir = (
            Path(output_root).expanduser().resolve()
            if output_root is not None
            else self.project_root / "output" / run_name
        )

        response_files = sorted(prompt_root_path.rglob("step4_prompt_payload*_llm_response.json"))
        rows: list[dict[str, str]] = []
        skipped_files: list[str] = []
        for response_file in response_files:
            try:
                rows.extend(self._rows_from_response_file(response_file, prompt_root_path))
            except Exception:
                skipped_files.append(str(response_file))

        rows = self._sort_rows(rows)
        output_csv = output_dir / f"{run_name}_end_results.csv"
        output_md = output_dir / f"{run_name}_end_results.md"
        self._write_csv(rows, output_csv, drop_columns=drop_columns)
        self._write_markdown(rows, prompt_root_path, output_csv, output_md)

        return {
            "prompt_root": str(prompt_root_path),
            "output_dir": str(output_dir),
            "output_csv": str(output_csv),
            "output_md": str(output_md),
            "response_file_count": len(response_files),
            "row_count": len(rows),
            "skipped_file_count": len(skipped_files),
            "skipped_files": skipped_files,
        }


def main() -> None:
    # -------------------------------
    # Edit config here (code-first)
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    prompt_root = (
        project_root
        / "intermediate_results"
        / "02_processing"
        / "03_reasoning"
        / "reapromptpreparation"
        / "prompts_rea_no_injections__reg"
    )
    output_root: Path | None = None

    extractor = EndResultExtractor(project_root=project_root)
    result = extractor.run(
        prompt_root=prompt_root,
        output_root=output_root,
        drop_columns=None,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
