from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class RegPrepPipeline:
    """
    REG preparation pipeline:
    1) Requirements extractor (main + extended) via RequirementsExtractor_v2
    2) Deontic slot extractor (stage1-4 on extended)
    3) Main requirements slot filter
    4) Graph building (from extended requirements)
    5) Graph visualization
    """

    def __init__(
        self,
        project_root: str | Path,
        reg_input_name: str = "reg_eu_ai_act",
        main_articles: list[int] | None = None,
        depth_one_articles: list[int] | None = None,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 240,
        max_retries: int = 3,
        temperature: float = 0.1,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))

        from pipeline.extractor.RequirementsExtractor_v2 import RequirementsExtractor as RequirementsExtractorV2
        from pipeline.graphBuilder.RequirementsGraphBuilder_v2 import RequirementsGraphBuilder
        from pipeline.graphBuilder.graphVisualizer_v2 import GraphVisualizerV2
        from pipeline.reasoning.DeonticSlotExtractorLlama import DeonticSlotExtractorLlama
        from pipeline.reasoning.MainRequirementsSlotFilter import MainRequirementsSlotFilter

        self.RequirementsExtractorV2 = RequirementsExtractorV2
        self.DeonticSlotExtractorLlama = DeonticSlotExtractorLlama
        self.MainRequirementsSlotFilter = MainRequirementsSlotFilter
        self.RequirementsGraphBuilder = RequirementsGraphBuilder
        self.GraphVisualizerV2 = GraphVisualizerV2

        self.reg_input_name = str(reg_input_name).strip()
        default_main = [8, 9, 10, 11, 12, 13, 14, 15] if self.reg_input_name == "reg_eu_ai_act" else []
        default_depth_one = [72, 79, 60, 97, 26] if self.reg_input_name == "reg_eu_ai_act" else []
        self.main_articles = main_articles if main_articles is not None else default_main
        self.depth_one_articles = depth_one_articles if depth_one_articles is not None else default_depth_one
        self.extended_articles = list(dict.fromkeys(self.main_articles + self.depth_one_articles))

        reg_input_root = self.project_root / "input" / self.reg_input_name
        reg_output_root = self.project_root / "intermediate_results" / self.reg_input_name

        self.reg_input_root = reg_input_root
        self.reg_output_root = reg_output_root

        # REG input source must be an existing Docling-style JSON file.
        existing_json = sorted(reg_input_root.glob("*.json"))
        if not existing_json:
            raise FileNotFoundError(
                f"No .json found in {reg_input_root}. "
                "Provide an input JSON for RequirementsExtractor_v2 (DoclingProcessor is removed)."
            )
        self.input_reg_json = existing_json[0]

        self.output_main_requirements = reg_output_root / f"{self.reg_input_name}_requirements.json"
        self.output_extended_requirements = reg_output_root / f"{self.reg_input_name}_requirements_extended.json"

        self.output_stage13_report = reg_output_root / f"{self.reg_input_name}_requirements_extended_passive_active_report_llama3.json"
        self.output_extended_slots = reg_output_root / f"{self.reg_input_name}_requirements_extended_slots_llama3.json"
        self.output_main_slots = reg_output_root / f"{self.reg_input_name}_requirements_slots_main.json"

        self.output_graph_graphml = reg_output_root / f"{self.reg_input_name}_requirements_graph.graphml"
        self.output_graph_json = reg_output_root / f"{self.reg_input_name}_requirements_graph.json"
        self.output_graph_html = reg_output_root / f"{self.reg_input_name}_requirements_graph_viz.html"

        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature

    def run_requirements_extractor(self) -> dict[str, str]:
        extractor = self.RequirementsExtractorV2(self.input_reg_json)
        if self.main_articles and self.extended_articles:
            saved_main, saved_extended = extractor.save_requirements_dual(
                main_output_path=self.output_main_requirements,
                extended_output_path=self.output_extended_requirements,
                main_articles=self.main_articles,
                extended_articles=self.extended_articles,
            )
        else:
            saved_main = extractor.save_requirements(self.output_main_requirements, include_articles=None)
            saved_extended = extractor.save_requirements(self.output_extended_requirements, include_articles=None)
        return {
            "main_requirements": str(saved_main),
            "extended_requirements": str(saved_extended),
        }

    def run_deontic_slot_extractor(self) -> dict[str, str]:
        extractor = self.DeonticSlotExtractorLlama(
            endpoint_url=self.endpoint_url,
            model_name=self.model_name,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            temperature=self.temperature,
        )
        saved_stage13 = extractor.run_passive_active_pipeline_on_file(
            input_json=self.output_extended_requirements,
            output_json=self.output_stage13_report,
        )
        stage4_input = Path(saved_stage13)
        fallback_used = False
        fallback_reason = ""

        # Fallback: if stage1-3 produced zero recovered outputs, run stage4 on
        # original extended requirements so downstream retrieval is not empty.
        try:
            payload = json.loads(stage4_input.read_text(encoding="utf-8"))
            recovered_count = 0
            if isinstance(payload, dict):
                scenarios = payload.get("results", [])
                if isinstance(scenarios, list):
                    for scenario in scenarios:
                        if not isinstance(scenario, dict):
                            continue
                        output_rows = scenario.get("output", [])
                        if isinstance(output_rows, list):
                            recovered_count += len(output_rows)
            if recovered_count == 0:
                stage4_input = self.output_extended_requirements
                fallback_used = True
                fallback_reason = "stage1-3 report had zero recovered output rows"
        except Exception:
            # Keep default behavior if report cannot be inspected.
            pass

        saved_stage4 = extractor.run(
            input_json=stage4_input,
            output_json=self.output_extended_slots,
        )
        return {
            "stage1_3_report": str(saved_stage13),
            "stage4_slots": str(saved_stage4),
            "stage4_input": str(stage4_input),
            "fallback_used": str(fallback_used),
            "fallback_reason": fallback_reason,
        }

    def run_main_slot_filter(self) -> str:
        slot_filter = self.MainRequirementsSlotFilter()
        saved = slot_filter.build_main_slots(
            main_requirements_json=self.output_main_requirements,
            extended_slots_json=self.output_extended_slots,
            output_json=self.output_main_slots,
        )
        return str(saved)

    def run_graph_builder(self) -> dict[str, Any]:
        builder = self.RequirementsGraphBuilder(self.output_extended_requirements)
        graph = builder.build_graph()
        saved_graphml = builder.save_graph_graphml(self.output_graph_graphml)
        saved_graph_json = builder.save_graph_json(self.output_graph_json)
        return {
            "nodes": int(graph.number_of_nodes()),
            "edges": int(graph.number_of_edges()),
            "graphml": str(saved_graphml),
            "graph_json": str(saved_graph_json),
        }

    def run_graph_visualization(self) -> str:
        visualizer = self.GraphVisualizerV2(
            graphml_path=self.output_graph_graphml,
            graph_json_path=self.output_graph_json,
        )
        visualizer.load_graph()
        saved_html = visualizer.visualize(output_html_path=self.output_graph_html)
        return str(saved_html)

    def run(
        self,
        run_requirements_extractor: bool = True,
        run_deontic_slot_extractor: bool = True,
        run_main_slot_filter: bool = True,
        run_graph_builder: bool = True,
        run_graph_visualization: bool = True,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project_root": str(self.project_root),
            "reg_input_json": str(self.input_reg_json),
            "steps": {},
        }

        if run_requirements_extractor:
            result["steps"]["requirements_extractor"] = self.run_requirements_extractor()
        else:
            result["steps"]["requirements_extractor"] = {"status": "skipped"}

        if run_deontic_slot_extractor:
            result["steps"]["deontic_slot_extractor"] = self.run_deontic_slot_extractor()
        else:
            result["steps"]["deontic_slot_extractor"] = {"status": "skipped"}

        if run_main_slot_filter:
            result["steps"]["main_requirements_slot_filter"] = self.run_main_slot_filter()
        else:
            result["steps"]["main_requirements_slot_filter"] = {"status": "skipped"}

        if run_graph_builder:
            result["steps"]["graph_builder"] = self.run_graph_builder()
        else:
            result["steps"]["graph_builder"] = {"status": "skipped"}

        if run_graph_visualization:
            result["steps"]["graph_visualization"] = self.run_graph_visualization()
        else:
            result["steps"]["graph_visualization"] = {"status": "skipped"}

        return result


def main() -> None:
    # -------------------------------
    # Edit config here
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    reg_input_name = "reg_for_injectiontest"  # folder under input/

    # main: 8, 9, 10, 11, 12, 13, 14, 15
    main_articles = [8, 9, 10, 11, 12, 13, 14, 15]
    # 1-depth context additions: 72, 79, 60, 97, 26
    context_articles = [72, 79, 60, 97, 26]

    pipeline = RegPrepPipeline(
        project_root=project_root,
        reg_input_name=reg_input_name,
        main_articles=main_articles,
        depth_one_articles=context_articles,
    )
    summary = pipeline.run(
        run_requirements_extractor=True,
        run_deontic_slot_extractor=True,
        run_main_slot_filter=True,
        run_graph_builder=True,
        run_graph_visualization=True,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
