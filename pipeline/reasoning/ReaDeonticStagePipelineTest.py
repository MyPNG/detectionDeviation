from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ReaDeonticStagePipeline import ReaDeonticStagePipeline


class ReaDeonticStagePipelineTest:
    """
    Stage 1-3 tester for REA chunks:
    - stage 1: rule-based anaphora + missing actor
    - stage 2: trace pass-through
    - stage 3: passive->active (LLM + deterministic guards)
    """

    SAMPLE_REA_CHUNK: list[dict[str, str]] = [
        {
            "title": "",
            "rea_id": "REA-01",
            "text": (
                "Microsoft AI systems are assessed using Impact Assessments. Applies to: All AI systems. "
                "Assess the impact of the system on people, organizations, and society by completing an "
                "Impact Assessment early in the system's development, typically when defining the product "
                "vision and requirements. Do not document the effort using the Impact Assessment template "
                "provided by the Office of Responsible AI."
            ),
        },
        {
            "title": "",
            "rea_id": "REA-02",
            "text": (
                "Review the completed Impact Assessment with the reviewers identified according to your "
                "organization's compliance process before development starts. Secure all required approvals "
                "from those reviewers."
            ),
        },
        {
            "title": "",
            "rea_id": "REA-03",
            "text": (
                "Update and review the Impact Assessment at least annually, when new intended uses are added, "
                "and before advancing to a new release stage. Update and review the Impact Assessment at least "
                "annually, when new intended uses are added, and before advancing to a new release stage."
            ),
        },
    ]

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 240,
        max_retries: int = 3,
        temperature: float = 0.1,
    ) -> None:
        self.pipeline = ReaDeonticStagePipeline(
            endpoint_url=endpoint_url,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _load_input_rows(input_json: Path | None) -> list[dict[str, Any]]:
        if input_json is None:
            return [dict(item) for item in ReaDeonticStagePipelineTest.SAMPLE_REA_CHUNK]
        payload = json.loads(input_json.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected list JSON in: {input_json}")
        rows = [row for row in payload if isinstance(row, dict)]
        return rows

    def _build_nodes(self, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
        nodes: list[dict[str, str]] = []
        for row in rows:
            rea_id = self._normalize_text(str(row.get("rea_id", "")))
            text = self._normalize_text(str(row.get("text", "")))
            if not rea_id or not text:
                continue
            nodes.append({"ID": rea_id, "Text": text})
        return nodes

    def run(self, output_json: Path, input_json: Path | None = None) -> Path:
        rows = self._load_input_rows(input_json=input_json)
        nodes = self._build_nodes(rows)
        if not nodes:
            raise ValueError("No valid REA nodes found (rea_id/text required).")

        stage1_output = self.pipeline.extractor.resolve_anaphora_and_missing_actor(nodes)
        stage2_output = [dict(node) for node in stage1_output]
        stage3_output = self.pipeline.extractor.make_passive_to_active(stage2_output)

        output_payload = {
            "test_type": "rea_stage1_3_test",
            "model": self.pipeline.extractor.model_name,
            "endpoint": self.pipeline.extractor.endpoint_url,
            "input_source": str(input_json) if input_json else "embedded_sample_chunk",
            "input_rows": rows,
            "stage1_output": stage1_output,
            "stage2_output": stage2_output,
            "stage3_output": stage3_output,
        }
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_json


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    tester = ReaDeonticStagePipelineTest(
        endpoint_url="http://localhost:11434/api/chat",
        model_name="llama3",
        timeout_seconds=240,
        max_retries=3,
        temperature=0.1,
    )

    # Optional:
    # .venv/bin/python .../ReaDeonticStagePipelineTest.py /abs/path/to/chunk_requirements.json
    input_json: Path | None = None
    if len(sys.argv) > 1:
        input_json = Path(sys.argv[1]).expanduser().resolve()

    output_json = (
        project_root
        / "intermediate_results"
        / "rea_case3_injections_deontic_stages"
        / "rea_stage1_3_test_report.json"
    )
    saved = tester.run(output_json=output_json, input_json=input_json)
    print(f"Saved stage1-3 test report: {saved}")


if __name__ == "__main__":
    main()

