from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class DeviationPromptBuilder:
    MAX_MAIN_REG_PER_PROMPT = 3

    SYSTEM_PROMPT = """You are a legal compliance deviation assessor.

Compare the REA and REG primarily using the raw text.
Use the logical slots only to structure the comparison and focus on these dimensions:
- actor
- modal
- action
- object
- temporal
- condition
- manner
- sequence
- negation

Use graph context only as supporting legal context when provided.
Use it only to clarify the meaning, scope, order, alternatives, or parent-child structure of the main REG clauses.
Do not let graph context override the main REG text unless it clearly resolves ambiguity.

Your task is to determine whether and where the REA deviates from the REG.
A deviation exists only if there is a meaning-changing mismatch supported by the provided text.

Important rules:
1. Treat raw clause text as the authoritative evidence.
2. Treat logical slots as guidance, not as the final source of truth.
3. Use graph context only when needed to interpret the REG.
4. Do not use external knowledge.
5. Do not treat omission alone as a deviation.
6. Do not assume that shared verbs imply the same constraint.
7. Only classify a deviation when the quoted REA and REG spans clearly express the same or directly conflicting constraint.
8. Prefer Non-Deviation if the evidence is ambiguous.
9. For every deviation, quote the exact REA span and exact REG span that support the mismatch.
10. If no quote-supported mismatch exists, return Non-Deviation.

Deviation Taxonomy:
If a deviation is found, classify it into exactly one of these categories:
- Data deviation: The specific scope, state, or category of data/processing is subtly altered or narrowed.
  (Example 1: GDPR grants access to data "being processed", but the policy limits it to data "stored" at rest.
   Example 2: GDPR grants the right to object specifically to "profiling," but the policy only mentions general "processing".)
- Severity deviation: The policy is over-compliant (stricter about constraints than the GDPR requires).
  (Example: GDPR requires informing within 72h, while policy states within 24h.)
- Execution style deviation: The method or phrasing of how a task is executed differs.
  (Example: regulation says "gluing parts together", policy says "weld the parts".)
- Negation deviation: The constraints are similar but logically negated.
  (Example: regulation requires contacting by phone, policy states not to use phone.)
- Responsibility deviation: The entity/resource/role specified to execute a task differs.
  (Example: regulation assigns Resource A, policy assigns Resource B.)
- Time deviation: The timeframe or deadline differs (and it is not an over-compliant severity deviation).
  (Example: regulation requires one day, policy allows two days.)
- Task execution order deviation: The required sequence of actions differs.
  (Example: regulation requires A-B-C, policy states B-A-C.)

Return JSON only using this exact schema:
{
  "id": "REA-XX#Y",
  "per_reg_comparisons": [
    {
      "reg_id": "REG-XXX",
      "deviation": true,
      "type": "Time deviation",
      "evidence_rea": ["..."],
      "evidence_reg": ["..."],
      "reasoning_short": "...",
      "confidence": "low|medium|high",
      "needs_more_context": false
    }
  ],
  "overall_deviation": true,
  "overall_confidence": "low|medium|high"
}"""

    def __init__(
        self,
        project_root: str | Path,
        reg_slots_json: str | Path | None = None,
        rea_stage_root: str | Path | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        self.reg_slots_json = (
            Path(reg_slots_json).expanduser().resolve()
            if reg_slots_json is not None
            else self.project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_slots_main.json"
        )
        self.rea_stage_root = (
            Path(rea_stage_root).expanduser().resolve()
            if rea_stage_root is not None
            else self.project_root / "intermediate_results" / "rea_case3_injections_deontic_stages"
        )
        self.reg_rows_by_id = self._load_reg_rows()

    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _build_clause(article: Any, paragraph: Any) -> str:
        article_str = " ".join(str(article or "").split()).strip()
        paragraph_str = " ".join(str(paragraph or "").split()).strip()
        if not article_str:
            return ""
        if paragraph_str:
            return f"Art{article_str}({paragraph_str})"
        return f"Art{article_str}"

    @classmethod
    def _clean_placeholder(cls, value: Any) -> str:
        text = cls._normalize_spaces(value)
        text = text.replace("[missing_subject]", "").replace("missing_subject", "")
        return cls._normalize_spaces(text)

    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_reg_rows(self) -> dict[str, dict[str, Any]]:
        payload = self._load_json(self.reg_slots_json)
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("REG slots JSON must be a list or an object with 'results'.")

        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            reg_id = self._normalize_spaces(row.get("ID", row.get("id", "")))
            if reg_id:
                by_id[reg_id] = row
        return by_id

    @staticmethod
    def _format_slot_block(row: dict[str, Any]) -> str:
        action_list = row.get("action_list", [])
        if not isinstance(action_list, list):
            action_list = [action_list] if action_list else []
        actions = [str(value).strip() for value in action_list if str(value).strip()]

        lines = [
            f"actor: {DeviationPromptBuilder._clean_placeholder(row.get('actor', ''))}",
            f"modal: {str(row.get('modal', row.get('Modal', ''))).strip()}",
            f"action: {str(row.get('action', '')).strip()}",
            f"actions: {' | '.join(actions)}" if actions else "actions: ",
            f"object: {DeviationPromptBuilder._clean_placeholder(row.get('object', ''))}",
            f"temporal: {DeviationPromptBuilder._clean_placeholder(row.get('temporal', ''))}",
            f"condition: {DeviationPromptBuilder._clean_placeholder(row.get('condition', ''))}",
            f"manner: {DeviationPromptBuilder._clean_placeholder(row.get('manner', ''))}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _sort_stage4_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def _key(row: dict[str, Any]) -> tuple[str, int]:
            rea_id = str(row.get("rea_id", row.get("id", ""))).strip()
            split_index_raw = str(row.get("split_index", "")).strip()
            try:
                split_index = int(split_index_raw)
            except Exception:
                split_index = 10**9
            return rea_id, split_index

        return sorted(rows, key=_key)

    def _resolve_stage_file(self, reranked_json_path: Path) -> Path:
        chunk_dir_name = reranked_json_path.parent.name
        chunk_name = chunk_dir_name.replace("_deontic_stages", "")
        stage_file = self.rea_stage_root / chunk_name / f"{chunk_name}_deontic_stages.json"
        if not stage_file.exists():
            raise FileNotFoundError(f"REA stage file not found for reranked JSON: {stage_file}")
        return stage_file

    def _load_focus_and_siblings(self, reranked_json_path: Path, sub_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        stage_file = self._resolve_stage_file(reranked_json_path)
        payload = self._load_json(stage_file)
        stage4_rows = payload.get("stage4_output", [])
        if not isinstance(stage4_rows, list):
            raise ValueError(f"stage4_output missing in {stage_file}")

        focus_row: dict[str, Any] | None = None
        by_rea: dict[str, list[dict[str, Any]]] = {}
        for row in stage4_rows:
            if not isinstance(row, dict):
                continue
            rea_id = self._normalize_spaces(row.get("rea_id", row.get("id", "")))
            if not rea_id:
                continue
            by_rea.setdefault(rea_id, []).append(row)
            if self._normalize_spaces(row.get("sub_id", "")) == sub_id:
                focus_row = row

        if focus_row is None:
            raise ValueError(f"Could not find stage4 row for sub_id={sub_id} in {stage_file}")

        rea_id = self._normalize_spaces(focus_row.get("rea_id", focus_row.get("id", "")))
        family = self._sort_stage4_rows(by_rea.get(rea_id, []))
        focus_idx = next((idx for idx, row in enumerate(family) if self._normalize_spaces(row.get("sub_id", "")) == sub_id), None)
        if focus_idx is None:
            return focus_row, []

        siblings: list[dict[str, Any]] = []
        if focus_idx - 1 >= 0:
            siblings.append(family[focus_idx - 1])
        if focus_idx + 1 < len(family):
            siblings.append(family[focus_idx + 1])
        return focus_row, siblings

    def _build_reg_context(self, top_matches: list[dict[str, Any]], top_k: int) -> tuple[list[str], list[str]]:
        blocks: list[str] = []
        used_reg_ids: list[str] = []
        limited_top_k = min(max(1, top_k), self.MAX_MAIN_REG_PER_PROMPT)
        for idx, match in enumerate(top_matches[:limited_top_k], start=1):
            reg_id = self._normalize_spaces(match.get("ID", ""))
            if not reg_id:
                continue
            used_reg_ids.append(reg_id)
            reg_row = self.reg_rows_by_id.get(reg_id, {})
            raw_text = self._normalize_spaces(reg_row.get("text", reg_row.get("Text", match.get("text", ""))))
            article = self._normalize_spaces(reg_row.get("article", reg_row.get("Article", match.get("article", ""))))
            paragraph = self._normalize_spaces(reg_row.get("paragraph", reg_row.get("Paragraph", "")))
            clause = self._normalize_spaces(match.get("article", ""))
            fallback_clause = self._build_clause(article, paragraph)
            slot_block = self._format_slot_block(reg_row if reg_row else {})
            lines = [
                f"{idx}. {reg_id}",
                f"clause: {clause or fallback_clause}",
                f"text: \"{self._clean_placeholder(raw_text)}\"",
                "slots:",
                slot_block,
            ]
            blocks.append("\n".join(lines))
        return blocks, used_reg_ids

    def _format_graph_context_rows(self, rows: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            reg_id = self._normalize_spaces(row.get("id", ""))
            edge_type = self._normalize_spaces(row.get("edge_type", ""))
            direction = self._normalize_spaces(row.get("direction", ""))
            hop_count = self._normalize_spaces(row.get("hop_count", ""))
            relation_path = self._normalize_spaces(row.get("relation_path", ""))
            article = self._normalize_spaces(row.get("article", ""))
            paragraph = self._normalize_spaces(row.get("paragraph", ""))
            clause = self._normalize_spaces(row.get("clause", "")) or self._build_clause(article, paragraph)
            text = self._clean_placeholder(row.get("text", ""))
            if not reg_id:
                continue
            lines.extend(
                [
                    f"- id: {reg_id}",
                    f"  clause: {clause}",
                    f"  edge_type: {edge_type}",
                    f"  direction: {direction}",
                    f"  hop_count: {hop_count}",
                    f"  relation_path: {relation_path}",
                    f'  text: "{text}"',
                ]
            )
        return lines

    def _build_reg_context_from_graph_context(self, graph_context: dict[str, Any]) -> tuple[list[str], list[str]]:
        blocks: list[str] = []
        used_reg_ids: list[str] = []
        main_constraints = graph_context.get("main_constraints", [])
        if not isinstance(main_constraints, list):
            return blocks, used_reg_ids

        for idx, main in enumerate(main_constraints[: self.MAX_MAIN_REG_PER_PROMPT], start=1):
            if not isinstance(main, dict):
                continue
            reg_id = self._normalize_spaces(main.get("id", ""))
            if not reg_id:
                continue
            used_reg_ids.append(reg_id)
            reg_row = self.reg_rows_by_id.get(reg_id, {})
            raw_text = self._normalize_spaces(reg_row.get("text", reg_row.get("Text", main.get("text", ""))))
            article = self._normalize_spaces(reg_row.get("article", reg_row.get("Article", "")))
            paragraph = self._normalize_spaces(reg_row.get("paragraph", reg_row.get("Paragraph", "")))
            clause = self._normalize_spaces(main.get("clause", ""))
            fallback_clause = self._build_clause(article, paragraph)
            slot_block = self._format_slot_block(reg_row if reg_row else {})
            lines = [
                f"{idx}. {reg_id}",
                f"clause: {clause or fallback_clause}",
                f'text: "{self._clean_placeholder(raw_text)}"',
                "slots:",
                slot_block,
                "graph_context:",
            ]
            graph_rows = main.get("graph_context", [])
            if isinstance(graph_rows, list) and graph_rows:
                lines.extend(self._format_graph_context_rows(graph_rows))
            else:
                lines.append("- none")
            blocks.append("\n".join(lines))
        return blocks, used_reg_ids

    def build_prompt_payload(
        self,
        reranked_json_path: str | Path,
        top_k: int = 3,
        graph_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        reranked_path = Path(reranked_json_path).expanduser().resolve()
        payload = self._load_json(reranked_path)
        sub_id = self._normalize_spaces(payload.get("id", ""))
        if not sub_id:
            raise ValueError(f"Reranked JSON missing id: {reranked_path}")

        focus_row, _siblings = self._load_focus_and_siblings(reranked_path, sub_id)
        if graph_context and isinstance(graph_context, dict):
            reg_blocks, used_reg_ids = self._build_reg_context_from_graph_context(graph_context)
        else:
            reg_blocks, used_reg_ids = self._build_reg_context(payload.get("top matches", []), top_k=top_k)

        user_prompt_lines = [
            "REA FOCUS UNIT",
            f"id: {sub_id}",
            f"text: \"{self._clean_placeholder(focus_row.get('text', ''))}\"",
            "slots:",
            self._format_slot_block(focus_row),
        ]

        user_prompt_lines.extend(
            [
                "",
                "MAIN REG MATCHES",
                "\n\n".join(reg_blocks) if reg_blocks else "none",
                "",
                "REQUIRED REG IDS",
                ", ".join(used_reg_ids) if used_reg_ids else "none",
                "",
                "INSTRUCTIONS",
                "1. Compare the REA and REG primarily using the raw text.",
                "2. Use the slots only as checklist hints (actor/modal/action/object/condition/temporal/manner/sequence/negation).",
                "3. For each REG, decide if there is a quote-supported deviation.",
                "4. If deviation=true, set exactly one 'type' from this taxonomy only:",
                "   Data deviation | Severity deviation | Execution style deviation | Negation deviation | Responsibility deviation | Time deviation | Task execution order deviation",
                "5. Every deviation claim must include evidence spans from both REA and REG.",
                "6. Do not assume that shared verbs imply the same constraint.",
                "7. Only classify a deviation when quoted REA and REG spans clearly express the same or directly conflicting constraint.",
                "8. Do not treat omission alone as a deviation.",
                "9. If evidence is ambiguous or weak for a REG comparison, set deviation=false, confidence=low, and needs_more_context=true for that REG.",
                "10. Return exactly one per_reg_comparisons entry for each REG ID listed under REQUIRED REG IDS. No missing IDs and no extra IDs.",
                "11. Return JSON only in this schema:",
                "",
                "{",
                f'  "id": "{sub_id}",',
                '  "per_reg_comparisons": [',
                "    {",
                '      "reg_id": "REG-XXX",',
                '      "deviation": true,',
                '      "type": "Data deviation | Severity deviation | Execution style deviation | Negation deviation | Responsibility deviation | Time deviation | Task execution order deviation",',
                '      "evidence_rea": ["...exact quote span(s)..."],',
                '      "evidence_reg": ["...exact quote span(s)..."],',
                '      "reasoning_short": "...one concise explanation...",',
                '      "confidence": "low | medium | high",',
                '      "needs_more_context": false',
                "    }",
                "  ],",
                '  "overall_deviation": true,',
                '  "overall_confidence": "low | medium | high"',
                "}",
            ]
        )

        return {
            "id": sub_id,
            "top_k": min(max(1, top_k), self.MAX_MAIN_REG_PER_PROMPT),
            "reranked_json": str(reranked_path),
            "used_reg_ids": used_reg_ids,
            "system_prompt": self.SYSTEM_PROMPT,
            "user_prompt": "\n".join(user_prompt_lines),
            "graph_context": graph_context if isinstance(graph_context, dict) else {},
        }

    @staticmethod
    def _to_markdown(prompt_payload: dict[str, Any]) -> str:
        used_reg_ids = prompt_payload.get("used_reg_ids", [])
        if not isinstance(used_reg_ids, list):
            used_reg_ids = []
        reg_ids_line = ", ".join(str(value).strip() for value in used_reg_ids if str(value).strip()) or "none"

        lines = [
            "# Deviation Prompt",
            "",
            f"- id: {prompt_payload.get('id', '')}",
            f"- top_k: {prompt_payload.get('top_k', '')}",
            f"- reranked_json: {prompt_payload.get('reranked_json', '')}",
            f"- used_reg_ids: {reg_ids_line}",
            "",
            "## System Prompt",
            "```text",
            str(prompt_payload.get("system_prompt", "")).strip(),
            "```",
            "",
            "## User Prompt",
            "```text",
            str(prompt_payload.get("user_prompt", "")).strip(),
            "```",
            "",
        ]
        return "\n".join(lines)

    def run(
        self,
        reranked_json_path: str | Path,
        output_json: str | Path,
        top_k: int = 3,
        output_md: str | Path | None = None,
        graph_context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        prompt_payload = self.build_prompt_payload(
            reranked_json_path=reranked_json_path,
            top_k=top_k,
            graph_context=graph_context,
        )
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(prompt_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        if output_md is None:
            output_md_path = output_path.with_suffix(".md")
        else:
            output_md_path = Path(output_md).expanduser().resolve()
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(self._to_markdown(prompt_payload), encoding="utf-8")

        return {
            "json": str(output_path),
            "md": str(output_md_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one deviation prompt from a reranked REA JSON.")
    parser.add_argument("reranked_json", help="Path to one reranked REA JSON file, e.g. rea-01#5.json")
    parser.add_argument("--top-k", type=int, default=3, help="Number of top REG matches to include.")
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional output path. Defaults to <reranked_json>_prompt.json",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Optional readable markdown path. Defaults to <output_json>.md",
    )
    args = parser.parse_args()

    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    builder = DeviationPromptBuilder(project_root=project_root)

    reranked_json = Path(args.reranked_json).expanduser().resolve()
    output_json = (
        Path(args.output_json).expanduser().resolve()
        if args.output_json
        else reranked_json.with_name(f"{reranked_json.stem}_prompt.json")
    )
    saved = builder.run(
        reranked_json_path=reranked_json,
        output_json=output_json,
        top_k=max(1, args.top_k),
        output_md=Path(args.output_md).expanduser().resolve() if args.output_md else None,
    )
    print(json.dumps(saved, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
