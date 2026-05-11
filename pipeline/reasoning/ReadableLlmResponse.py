from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


class ReadableLlmResponse:
    """
    Convert a *_prompt_llm_response.json file into:
    - normalized decision JSON
    - readable Markdown report
    """

    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _load_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _extract_json_block(text: str) -> dict[str, Any] | None:
        raw = str(text or "").strip()
        if not raw:
            return None

        # Direct JSON first.
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # Fenced code block.
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        # First {...} block fallback.
        brace_match = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
        if brace_match:
            candidate = brace_match.group(1).strip()
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                return None
        return None

    def _extract_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        response_text = payload.get("response_text", "")
        parsed = self._extract_json_block(str(response_text))

        if parsed is None:
            # Fallback to raw_response->choices->message->content
            raw_response = payload.get("raw_response", {})
            content = ""
            if isinstance(raw_response, dict):
                choices = raw_response.get("choices", [])
                if isinstance(choices, list) and choices:
                    msg = choices[0].get("message", {})
                    if isinstance(msg, dict):
                        content = str(msg.get("content", ""))
            parsed = self._extract_json_block(content)

        if parsed is None:
            parsed = {}

        normalized: dict[str, Any] = {
            "id": self._normalize_spaces(parsed.get("id", payload.get("id", ""))),
            "model": self._normalize_spaces(payload.get("model", "")),
            "prompt_json": self._normalize_spaces(payload.get("prompt_json", "")),
        }

        per_reg = parsed.get("per_reg_comparisons", [])
        if isinstance(per_reg, list) and per_reg:
            rows: list[dict[str, Any]] = []
            for row in per_reg:
                if not isinstance(row, dict):
                    continue
                types = row.get("types", [])
                single_type = self._normalize_spaces(row.get("type", ""))
                if not isinstance(types, list):
                    types = [str(types)] if str(types).strip() else []
                if single_type:
                    types = [single_type]
                evidence_rea = row.get("evidence_rea", [])
                if not isinstance(evidence_rea, list):
                    evidence_rea = [str(evidence_rea)] if str(evidence_rea).strip() else []
                evidence_reg = row.get("evidence_reg", [])
                if not isinstance(evidence_reg, list):
                    evidence_reg = [str(evidence_reg)] if str(evidence_reg).strip() else []

                rows.append(
                    {
                        "reg_id": self._normalize_spaces(row.get("reg_id", "")),
                        "deviation": bool(row.get("deviation", False)),
                        "types": [self._normalize_spaces(value) for value in types if self._normalize_spaces(value)],
                        "evidence_rea": [self._normalize_spaces(value) for value in evidence_rea if self._normalize_spaces(value)],
                        "evidence_reg": [self._normalize_spaces(value) for value in evidence_reg if self._normalize_spaces(value)],
                        "reasoning_short": self._normalize_spaces(row.get("reasoning_short", "")),
                        "confidence": self._normalize_spaces(row.get("confidence", "")),
                        "needs_more_context": bool(row.get("needs_more_context", False)),
                    }
                )

            normalized["per_reg_comparisons"] = rows
            normalized["overall_deviation"] = bool(parsed.get("overall_deviation", any(r.get("deviation", False) for r in rows)))
            normalized["overall_confidence"] = self._normalize_spaces(parsed.get("overall_confidence", ""))
            if not normalized["overall_confidence"]:
                # Conservative aggregate confidence from per-reg rows.
                conf_rank = {"low": 1, "medium": 2, "high": 3}
                inv = {1: "low", 2: "medium", 3: "high"}
                min_rank = min((conf_rank.get(str(r.get("confidence", "")).lower(), 1) for r in rows), default=1)
                normalized["overall_confidence"] = inv.get(min_rank, "low")
            return normalized

        # Backward-compatible single-decision shape.
        types = parsed.get("types", [])
        if not isinstance(types, list):
            types = [str(types)] if str(types).strip() else []
        evidence_rea = parsed.get("evidence_rea", [])
        if not isinstance(evidence_rea, list):
            evidence_rea = [str(evidence_rea)] if str(evidence_rea).strip() else []
        evidence_reg = parsed.get("evidence_reg", [])
        if not isinstance(evidence_reg, list):
            evidence_reg = [str(evidence_reg)] if str(evidence_reg).strip() else []

        normalized.update(
            {
                "deviation": bool(parsed.get("deviation", False)),
                "types": [self._normalize_spaces(value) for value in types if self._normalize_spaces(value)],
                "evidence_rea": [self._normalize_spaces(value) for value in evidence_rea if self._normalize_spaces(value)],
                "evidence_reg": [self._normalize_spaces(value) for value in evidence_reg if self._normalize_spaces(value)],
                "reasoning_short": self._normalize_spaces(parsed.get("reasoning_short", "")),
                "confidence": self._normalize_spaces(parsed.get("confidence", "")),
                "needs_more_context": bool(parsed.get("needs_more_context", False)),
            }
        )
        return normalized

    @staticmethod
    def _build_markdown(decision: dict[str, Any], source_file: Path) -> str:
        if isinstance(decision.get("per_reg_comparisons"), list):
            rows = decision.get("per_reg_comparisons", [])
            lines = [
                "# LLM Deviation Result (Per REG)",
                "",
                f"- source_file: {source_file}",
                f"- id: {decision.get('id', '')}",
                f"- model: {decision.get('model', '')}",
                f"- overall_deviation: {decision.get('overall_deviation', False)}",
                f"- overall_confidence: {decision.get('overall_confidence', '')}",
                "",
                "## Per REG Comparisons",
            ]
            if not rows:
                lines.append("- none")
            for row in rows:
                reg_id = row.get("reg_id", "")
                lines.extend(
                    [
                        "",
                        f"### {reg_id or 'REG-?'}",
                        f"- deviation: {row.get('deviation', False)}",
                        f"- confidence: {row.get('confidence', '')}",
                        f"- needs_more_context: {row.get('needs_more_context', False)}",
                        f"- types: {', '.join(row.get('types', [])) if row.get('types') else 'none'}",
                    ]
                )
                lines.extend(
                    [
                        "",
                        f"reasoning: {row.get('reasoning_short', '')}",
                        "",
                        "evidence_rea:",
                    ]
                )
                ev_rea = row.get("evidence_rea", [])
                if isinstance(ev_rea, list) and ev_rea:
                    lines.extend([f"- \"{item}\"" for item in ev_rea])
                else:
                    lines.append("- none")
                lines.append("evidence_reg:")
                ev_reg = row.get("evidence_reg", [])
                if isinstance(ev_reg, list) and ev_reg:
                    lines.extend([f"- \"{item}\"" for item in ev_reg])
                else:
                    lines.append("- none")
            lines.extend(["", "## Prompt Source", f"- {decision.get('prompt_json', '')}", ""])
            return "\n".join(lines)

        types = decision.get("types", [])
        if not isinstance(types, list):
            types = []
        evidence_rea = decision.get("evidence_rea", [])
        if not isinstance(evidence_rea, list):
            evidence_rea = []
        evidence_reg = decision.get("evidence_reg", [])
        if not isinstance(evidence_reg, list):
            evidence_reg = []

        lines = [
            "# LLM Deviation Result",
            "",
            f"- source_file: {source_file}",
            f"- id: {decision.get('id', '')}",
            f"- model: {decision.get('model', '')}",
            f"- deviation: {decision.get('deviation', False)}",
            f"- confidence: {decision.get('confidence', '')}",
            f"- needs_more_context: {decision.get('needs_more_context', False)}",
            "",
            "## Types",
        ]

        if types:
            lines.extend([f"- {item}" for item in types])
        else:
            lines.append("- none")

        lines.extend(["", "## Reasoning", decision.get("reasoning_short", "") or ""])

        lines.extend(["", "## Evidence REA"])
        if evidence_rea:
            lines.extend([f"- \"{item}\"" for item in evidence_rea])
        else:
            lines.append("- none")

        lines.extend(["", "## Evidence REG"])
        if evidence_reg:
            lines.extend([f"- \"{item}\"" for item in evidence_reg])
        else:
            lines.append("- none")

        lines.extend(["", "## Prompt Source", f"- {decision.get('prompt_json', '')}"])
        lines.append("")
        return "\n".join(lines)

    def run(
        self,
        llm_response_json: str | Path,
        output_json: str | Path | None = None,
        output_md: str | Path | None = None,
    ) -> dict[str, str]:
        input_path = Path(llm_response_json).expanduser().resolve()
        payload = self._load_json(input_path)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object JSON: {input_path}")

        decision = self._extract_decision(payload)

        out_json_path = (
            Path(output_json).expanduser().resolve()
            if output_json is not None
            else input_path.with_name(f"{input_path.stem}_readable.json")
        )
        out_md_path = (
            Path(output_md).expanduser().resolve()
            if output_md is not None
            else input_path.with_name(f"{input_path.stem}_readable.md")
        )

        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
        out_md_path.write_text(self._build_markdown(decision, source_file=input_path), encoding="utf-8")

        return {
            "input": str(input_path),
            "output_json": str(out_json_path),
            "output_md": str(out_md_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Make LLM response JSON more readable.")
    parser.add_argument("llm_response_json", help="Path to *_prompt_llm_response.json")
    parser.add_argument("--output-json", default="", help="Optional normalized JSON output path.")
    parser.add_argument("--output-md", default="", help="Optional markdown output path.")
    args = parser.parse_args()

    formatter = ReadableLlmResponse()
    saved = formatter.run(
        llm_response_json=Path(args.llm_response_json).expanduser().resolve(),
        output_json=Path(args.output_json).expanduser().resolve() if args.output_json else None,
        output_md=Path(args.output_md).expanduser().resolve() if args.output_md else None,
    )
    print(json.dumps(saved, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
