from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ReaDeonticStagePipeline import ReaDeonticStagePipeline


class ReaDeonticStagePipelineStage14Test:
    """
    Run stage1-4 on one REA input JSON file (list of rows with rea_id + text).
    """

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
    def _load_input_rows(input_json: Path) -> list[dict[str, Any]]:
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

    def run(self, input_json: Path, output_json: Path) -> Path:
        rows = self._load_input_rows(input_json=input_json)
        nodes = self._build_nodes(rows)
        if not nodes:
            raise ValueError("No valid rows found. Require fields: rea_id, text.")

        # Stage 1: split first
        stage1_output = self.pipeline._split_nodes_for_stage_processing(nodes)

        # Stage 2: missing actor + anaphora on split units
        stage2_output = self.pipeline._resolve_split_nodes_for_stage4(stage1_output)

        # Stage 3: passive->active on stage2 text
        stage3_input = [{"ID": row["ID"], "Text": row["Text"]} for row in stage2_output if row.get("ID") and row.get("Text")]
        stage3_output = self.pipeline.extractor.make_passive_to_active(stage3_input)

        # Stage 4 (split + re-resolve + slot extraction)
        group = self.pipeline._build_stage4_group(chunk_name="single_input", stage3_rows=stage3_output)
        stage4_output = self.pipeline.extractor.extract_slots_for_group(group)
        for slot_row in stage4_output:
            slot_id = self._normalize_text(str(slot_row.get("id", "")))
            if "#" in slot_id:
                base, sub = slot_id.split("#", 1)
                slot_row["rea_id"] = base
                slot_row["sub_id"] = slot_id
                slot_row["id"] = base
                slot_row["split_index"] = sub

        payload = {
            "test_type": "rea_stage1_4_single_file",
            "input_file": str(input_json),
            "model": self.pipeline.extractor.model_name,
            "endpoint": self.pipeline.extractor.endpoint_url,
            "input_rows": rows,
            "stage1_output": stage1_output,
            "stage2_output": stage2_output,
            "stage3_output": stage3_output,
            "stage4_output": stage4_output,
        }
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_json


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_input = (
        project_root
        / "intermediate_results"
        / "rea_case3_injections_deontic_stages"
        / "rea_stage1_4_test_input.json"
    )
    default_output = (
        project_root
        / "intermediate_results"
        / "rea_case3_injections_deontic_stages"
        / "rea_stage1_4_test_report.json"
    )

    input_json = default_input
    output_json = default_output
    if len(sys.argv) > 1:
        input_json = Path(sys.argv[1]).expanduser().resolve()
    if len(sys.argv) > 2:
        output_json = Path(sys.argv[2]).expanduser().resolve()

    tester = ReaDeonticStagePipelineStage14Test(
        endpoint_url="http://localhost:11434/api/chat",
        model_name="llama3",
        timeout_seconds=240,
        max_retries=3,
        temperature=0.1,
    )
    saved = tester.run(input_json=input_json, output_json=output_json)
    print(f"Saved stage1-4 test report: {saved}")


if __name__ == "__main__":
    main()
