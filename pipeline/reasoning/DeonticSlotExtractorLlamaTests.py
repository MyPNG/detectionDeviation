from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from DeonticSlotExtractorLlama import DeonticSlotExtractorLlama


class DeonticSlotExtractorLlamaLiveTester:
    """
    Live integration tester: calls local Ollama/Llama directly.
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 240,
        max_retries: int = 2,
    ) -> None:
        self.extractor = DeonticSlotExtractorLlama(
            endpoint_url=endpoint_url,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=0.1,
        )

    @staticmethod
    def _scenarios() -> list[dict[str, Any]]:
        return [
            {
                "name": "connector_inheritance_deployer",
                "nodes": [
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
                ],
            },
            {
                "name": "if_connector_inheritance",
                "nodes": [
                    {
                        "ID": "REG-801",
                        "Text": "If deployers detect a malfunction, the system shall not be used.",
                    },
                    {
                        "ID": "REG-802",
                        "Text": "and shall be reported immediately to the provider.",
                        "logic_relations": [{"type": "AND", "target": "REG-801"}],
                    },
                ],
            },
            {
                "name": "when_or_connector_chain",
                "nodes": [
                    {
                        "ID": "REG-811",
                        "Text": "When providers identify a non-conformity, corrective measures shall be implemented.",
                    },
                    {
                        "ID": "REG-812",
                        "Text": "or shall be documented with justification.",
                        "logic_relations": [{"type": "OR", "target": "REG-811"}],
                    },
                    {
                        "ID": "REG-813",
                        "Text": "and shall be communicated to the authority.",
                        "logic_relations": [{"type": "AND", "target": "REG-812"}],
                    },
                ],
            },
            {
                "name": "or_connector_with_prohibition",
                "nodes": [
                    {
                        "ID": "REG-501",
                        "Text": "When deployers identify a serious risk, that system shall not be used.",
                    },
                    {
                        "ID": "REG-502",
                        "Text": "or shall be withdrawn from service.",
                        "logic_relations": [{"type": "OR", "target": "REG-501"}],
                    },
                ],
            },
            {
                "name": "provider_passive_active",
                "nodes": [
                    {
                        "ID": "REG-601",
                        "Text": "The technical documentation shall be drawn up before that system is placed on the market.",
                    },
                    {
                        "ID": "REG-602",
                        "Text": "and shall be kept up to date.",
                        "logic_relations": [{"type": "AND", "target": "REG-601"}],
                    },
                ],
            },
            {
                "name": "but_connector_subject_carry",
                "nodes": [
                    {
                        "ID": "REG-901",
                        "Text": "The provider shall monitor post-market performance.",
                    },
                    {
                        "ID": "REG-902",
                        "Text": "but shall not place the system on the market before risk controls are validated.",
                        "logic_relations": [{"type": "BUT", "target": "REG-901"}],
                    },
                ],
            },
            {
                "name": "multi_passive_with_condition",
                "nodes": [
                    {
                        "ID": "REG-911",
                        "Text": "Where a serious incident is detected, the competent authority shall be informed without undue delay.",
                    },
                    {
                        "ID": "REG-912",
                        "Text": "and all relevant logs shall be preserved for investigation.",
                        "logic_relations": [{"type": "AND", "target": "REG-911"}],
                    },
                ],
            },
            {
                "name": "missing_subject_fallback",
                "nodes": [
                    {
                        "ID": "REG-701",
                        "Text": "and shall be monitored continuously.",
                    }
                ],
            },
        ]

    @staticmethod
    def _quick_checks(output_rows: list[dict[str, str]]) -> dict[str, Any]:
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

    def run(self, output_json: str | Path) -> Path:
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        scenario_results: list[dict[str, Any]] = []
        for scenario in self._scenarios():
            name = str(scenario["name"])
            nodes = list(scenario["nodes"])
            try:
                output_rows = self.extractor.make_passive_to_active_two_calls(nodes)
                checks = self._quick_checks(output_rows)
                scenario_results.append(
                    {
                        "scenario": name,
                        "input_nodes": nodes,
                        "output": output_rows,
                        "checks": checks,
                        "status": "ok" if checks["passed"] else "warning",
                    }
                )
            except Exception as exc:
                scenario_results.append(
                    {
                        "scenario": name,
                        "input_nodes": nodes,
                        "output": [],
                        "checks": {"passed": False},
                        "status": "error",
                        "error": str(exc),
                    }
                )

        payload = {
            "test_type": "live_llama",
            "model": self.extractor.model_name,
            "endpoint": self.extractor.endpoint_url,
            "scenario_count": len(scenario_results),
            "results": scenario_results,
        }

        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path


class DeonticSlotExtractorLlamaTestRunner:
    @staticmethod
    def run_live(output_json: str | Path | None = None) -> Path:
        project_root = Path(__file__).resolve().parents[2]
        default_output = project_root / "intermediate_results" / "reg_eu_ai_act" / "llama_live_test_report.json"
        out = Path(output_json).expanduser().resolve() if output_json is not None else default_output
        tester = DeonticSlotExtractorLlamaLiveTester()
        return tester.run(out)


def main() -> None:
    saved = DeonticSlotExtractorLlamaTestRunner.run_live()
    print(f"Saved live Llama test report: {saved}")


if __name__ == "__main__":
    main()
