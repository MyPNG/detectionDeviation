from __future__ import annotations

import json
import importlib
import sys
import tempfile
from pathlib import Path
from typing import Any


class RegPrepPipeline:
    """
    REG preparation pipeline:
    0) Optional PDF -> JSON via DoclingProcessor
    1) Requirements extractor (main + extended) via RequirementsExtractor
    2) Deontic slot extractor (stage1-4 on extended)
    3) Main requirements slot filter
    4) Embedding index build for main requirement slots
    5) Graph building (from extended requirements)
    6) Graph visualization
    """

    def __init__(
        self,
        project_root: str | Path,
        reg_input_name: str = "reg_eu_ai_act",
        reg_input_path: str | Path | None = None,
        pdf_to_json: bool = False,
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

        RequirementsExtractor = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.01_extracting.RequirementsExtractor"
        ).RequirementsExtractor
        RequirementsGraphBuilder = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.03_graphbuilder.RequirementsGraphBuilder"
        ).RequirementsGraphBuilder
        GraphVisualizer = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.03_graphbuilder.graphVisualizer"
        ).GraphVisualizer
        DoclingProcessor = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.01_extracting.DoclingProcessor"
        ).DoclingProcessor
        DeonticSlotExtractor = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.01_extracting.DeonticSlotExtractor"
        ).DeonticSlotExtractor
        MainRequirementsSlotFilter = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.01_extracting.MainRequirementsSlotFilter"
        ).MainRequirementsSlotFilter
        EmbeddingIndexBuilder = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.02_vector_embedding.EmbeddingIndexBuilder"
        ).EmbeddingIndexBuilder

        self.RequirementsExtractorClass = RequirementsExtractor
        self.DeonticSlotExtractorClass = DeonticSlotExtractor
        self.MainRequirementsSlotFilter = MainRequirementsSlotFilter
        self.EmbeddingIndexBuilderClass = EmbeddingIndexBuilder
        self.RequirementsGraphBuilder = RequirementsGraphBuilder
        self.GraphVisualizer = GraphVisualizer
        self.DoclingProcessor = DoclingProcessor

        self.reg_input_name = str(reg_input_name).strip()
        self.pdf_to_json = bool(pdf_to_json)
        self.reg_input_path = Path(reg_input_path).expanduser().resolve() if reg_input_path else None
        default_main = [8, 9, 10, 11, 12, 13, 14, 15] if self.reg_input_name == "reg_eu_ai_act" else []
        default_depth_one = [72, 79, 60, 97, 26] if self.reg_input_name == "reg_eu_ai_act" else []
        self.main_articles = main_articles if main_articles is not None else default_main
        self.depth_one_articles = depth_one_articles if depth_one_articles is not None else default_depth_one
        # Extended set is the graph/deontic context set:
        # - with context articles: main + context
        # - without context articles: main only
        self.extended_articles = list(dict.fromkeys(self.main_articles + self.depth_one_articles))

        reg_input_root = self.project_root / "input" / self.reg_input_name
        pre_root = self.project_root / "intermediate_results" / "01_preprocessing" / "reg_prep"
        extract_root = pre_root / "01_extracting"
        graph_root = pre_root / "03_graphbuilder"
        reg_output_root = pre_root / self.reg_input_name

        self.reg_input_root = reg_input_root
        self.reg_output_root = reg_output_root

        docling_dir = extract_root / "doclingprocessor" / self.reg_input_name
        req_dir = extract_root / "requirementsextractor" / self.reg_input_name
        deontic_dir = extract_root / "deonticextractor" / self.reg_input_name
        slot_filter_dir = extract_root / "mainrequirementsslotfilter" / self.reg_input_name
        graph_builder_dir = graph_root / "requirementsgraphbuilder" / self.reg_input_name
        graph_viz_dir = graph_root / "graphvisualizer" / self.reg_input_name

        self.input_reg_json = docling_dir / f"{self.reg_input_name}_docling_from_pdf.json"
        self.output_docling_markdown = docling_dir / f"{self.reg_input_name}_docling_from_pdf.md"

        self.output_main_requirements = req_dir / f"{self.reg_input_name}_requirements.json"
        self.output_extended_requirements = req_dir / f"{self.reg_input_name}_requirements_extended.json"

        self.output_stage13_report = deontic_dir / f"{self.reg_input_name}_requirements_extended_passive_active_report_llama3.json"
        self.output_extended_slots = deontic_dir / f"{self.reg_input_name}_requirements_extended_slots_llama3.json"
        self.output_main_slots = slot_filter_dir / f"{self.reg_input_name}_requirements_slots_main.json"

        self.output_graph_graphml = graph_builder_dir / f"{self.reg_input_name}_requirements_graph.graphml"
        self.output_graph_json = graph_builder_dir / f"{self.reg_input_name}_requirements_graph.json"
        self.output_graph_html = graph_viz_dir / f"{self.reg_input_name}_requirements_graph_viz.html"
        self.embedding_persist_dir = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reg_prep"
            / "02_vector_embedding"
            / "embeddingindexbuilder"
            / self.reg_input_name
            / "chromadb_store"
        )
        self.embedding_collection_name = f"requirements_{self.reg_input_name}"

        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature
        self._docling_prepared = False

    @staticmethod
    def _maybe_run(enabled: bool, fn: Any) -> Any:
        """Run function when enabled, otherwise return standardized skipped marker."""
        return fn() if enabled else {"status": "skipped"}

    @staticmethod
    def _log(message: str) -> None:
        """Print a consistent REG pipeline progress message."""
        print(f"[REG] {message}")

    def _run_step(self, step_name: str, enabled: bool, fn: Any) -> Any:
        """Run one REG pipeline step with terminal progress logs."""
        if not enabled:
            self._log(f"{step_name}: skipped")
            return {"status": "skipped"}
        self._log(f"{step_name}: started")
        result = fn()
        self._log(f"{step_name}: done")
        return result

    def _resolve_pdf_input_path(self) -> Path:
        """Resolve and validate PDF input path for optional Docling stage."""
        if self.reg_input_path is not None:
            if self.reg_input_path.suffix.lower() != ".pdf":
                raise ValueError(
                    f"pdf_to_json=True requires a PDF input path, got: {self.reg_input_path}"
                )
            if not self.reg_input_path.exists():
                raise FileNotFoundError(f"PDF input not found: {self.reg_input_path}")
            return self.reg_input_path

        candidates = sorted(self.reg_input_root.glob("*.pdf"))
        if not candidates:
            raise FileNotFoundError(
                f"pdf_to_json=True but no PDF found in {self.reg_input_root}. "
                "Provide reg_input_path=<path-to-pdf> or place one PDF in the folder."
            )
        return candidates[0]

    def _resolve_json_input_path(self) -> Path:
        """Resolve and validate JSON input path for requirements extraction stage."""
        if self.reg_input_path is not None:
            if self.reg_input_path.suffix.lower() != ".json":
                raise ValueError(
                    f"pdf_to_json=False expects JSON input path when reg_input_path is set, got: {self.reg_input_path}"
                )
            if not self.reg_input_path.exists():
                raise FileNotFoundError(f"JSON input not found: {self.reg_input_path}")
            return self.reg_input_path

        existing_json = sorted(self.reg_input_root.glob("*.json"))
        if not existing_json:
            raise FileNotFoundError(
                f"No .json found in {self.reg_input_root}. "
                "Set pdf_to_json=True with a PDF path or provide a JSON input."
            )
        return existing_json[0]

    @staticmethod
    def _ensure_exists(path: Path, label: str) -> Path:
        """Fail fast with a readable message when a required artifact is missing."""
        if not path.exists():
            raise FileNotFoundError(f"Missing {label}: {path}")
        return path

    def run_docling_pdf_to_json(self) -> dict[str, str]:
        """Convert PDF to markdown+JSON and persist them as pipeline input artifacts."""
        pdf_path = self._resolve_pdf_input_path()
        processor = self.DoclingProcessor()
        markdown_output = processor.pdf_to_markdown_for_articles(
            pdf_path=pdf_path,
            include_articles=None,
        )

        self.output_docling_markdown.parent.mkdir(parents=True, exist_ok=True)
        self.output_docling_markdown.write_text(markdown_output, encoding="utf-8")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as temp_md:
            temp_md.write(markdown_output)
            temp_md_path = Path(temp_md.name)
        try:
            docling_json = processor.markdown_to_json(temp_md_path, include_articles=None)
        finally:
            temp_md_path.unlink(missing_ok=True)

        self.input_reg_json.parent.mkdir(parents=True, exist_ok=True)
        self.input_reg_json.write_text(
            json.dumps(docling_json, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._docling_prepared = True
        return {
            "pdf_input": str(pdf_path),
            "markdown_output": str(self.output_docling_markdown),
            "json_output": str(self.input_reg_json),
        }

    def run_requirements_extractor(self) -> dict[str, str]:
        """Extract main and extended requirement rows from REG input JSON."""
        if self.pdf_to_json:
            if self._docling_prepared:
                pass
            elif self.input_reg_json.exists():
                # Reuse previously generated Docling JSON when stage-0 is skipped in this run.
                self._log(f"extracting requirements: reusing existing docling json at {self.input_reg_json}")
            else:
                raise RuntimeError(
                    "Docling stage output is missing while pdf_to_json=True. "
                    "Either run docling now (run_pdf_to_json=True) or ensure this file exists:\n"
                    f"- {self.input_reg_json}"
                )
        else:
            try:
                self.input_reg_json = self._resolve_json_input_path()
            except (FileNotFoundError, ValueError):
                # Independence mode:
                # if user supplied a PDF reg_input_path but wants to skip PDF->JSON,
                # reuse the expected docling JSON when it already exists.
                if self.input_reg_json.exists():
                    self._log(f"extracting requirements: reusing existing docling json at {self.input_reg_json}")
                else:
                    raise

        extractor = self.RequirementsExtractorClass(self.input_reg_json)
        # If extended article selection is identical to main selection (e.g. context=[]),
        # write once and mirror the same payload to extended output.
        same_selection = (
            bool(self.main_articles)
            and bool(self.extended_articles)
            and [int(x) for x in self.main_articles] == [int(x) for x in self.extended_articles]
        )

        if same_selection:
            saved_main = extractor.save_requirements(
                self.output_main_requirements,
                include_articles=self.main_articles,
            )
            self.output_extended_requirements.parent.mkdir(parents=True, exist_ok=True)
            self.output_extended_requirements.write_text(
                Path(saved_main).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            saved_extended = self.output_extended_requirements
            return {
                "main_requirements": str(saved_main),
                "extended_requirements": str(saved_extended),
                "same_article_selection": "true",
            }

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
            "same_article_selection": "false",
        }

    def run_deontic_slot_extractor(self) -> dict[str, str]:
        """Run stage1-4 deontic extraction over extended requirements."""
        self._ensure_exists(
            self.output_extended_requirements,
            "extended requirements input for deontic extraction",
        )
        extractor = self.DeonticSlotExtractorClass(
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
        """Keep slot rows that correspond to main requirement IDs only."""
        self._ensure_exists(self.output_main_requirements, "main requirements input for main slot filter")
        self._ensure_exists(self.output_extended_slots, "extended slots input for main slot filter")
        slot_filter = self.MainRequirementsSlotFilter()
        saved = slot_filter.build_main_slots(
            main_requirements_json=self.output_main_requirements,
            extended_slots_json=self.output_extended_slots,
            output_json=self.output_main_slots,
        )
        return str(saved)

    def run_embedding(self) -> dict[str, Any]:
        """Build and persist dense embeddings for main requirement slot rows."""
        if not self.output_main_slots.exists():
            raise FileNotFoundError(
                "Main slots file not found for embedding. "
                f"Expected: {self.output_main_slots}. "
                "Run main slot filter first (or point output_main_slots to an existing file)."
            )
        embedder = self.EmbeddingIndexBuilderClass(
            model_name="BAAI/bge-large-en-v1.5",
            collection_name=self.embedding_collection_name,
        )
        saved = embedder.embed_and_store(
            input_json_path=self.output_main_slots,
            chroma_persist_dir=self.embedding_persist_dir,
            batch_size=32,
        )
        return saved

    def run_graph_builder(self) -> dict[str, Any]:
        """Build graph artifacts (JSON/GraphML) from extended requirements."""
        self._ensure_exists(self.output_extended_requirements, "extended requirements input for graph builder")
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
        """Render HTML visualization from previously built graph artifacts."""
        self._ensure_exists(self.output_graph_graphml, "graphml input for graph visualization")
        self._ensure_exists(self.output_graph_json, "graph json input for graph visualization")
        visualizer = self.GraphVisualizer(
            graphml_path=self.output_graph_graphml,
            graph_json_path=self.output_graph_json,
        )
        visualizer.load_graph()
        saved_html = visualizer.visualize(output_html_path=self.output_graph_html)
        return str(saved_html)

    def run(
        self,
        run_pdf_to_json: bool | None = None,
        run_requirements_extractor: bool = True,
        run_deontic_slot_extractor: bool = True,
        run_main_slot_filter: bool = True,
        run_embedding: bool = True,
        run_graph_builder: bool = True,
        run_graph_visualization: bool = True,
    ) -> dict[str, Any]:
        """Run configurable REG preparation steps and return consolidated summary."""
        self._log("pipeline run started")
        run_pdf_enabled = self.pdf_to_json if run_pdf_to_json is None else bool(run_pdf_to_json)
        self.pdf_to_json = run_pdf_enabled
        self._docling_prepared = False

        result: dict[str, Any] = {
            "project_root": str(self.project_root),
            "reg_input_path": str(self.reg_input_path) if self.reg_input_path else "",
            "pdf_to_json": self.pdf_to_json,
            "reg_input_json": str(self.input_reg_json),
            "article_selection": {
                "main_articles": [int(x) for x in self.main_articles] if self.main_articles else [],
                "context_articles": [int(x) for x in self.depth_one_articles] if self.depth_one_articles else [],
                "extended_articles": [int(x) for x in self.extended_articles] if self.extended_articles else [],
            },
            "steps": {},
        }
        result["steps"]["docling_pdf_to_json"] = self._run_step(
            "docling pdf->json",
            self.pdf_to_json,
            self.run_docling_pdf_to_json,
        )
        result["steps"]["requirements_extractor"] = self._run_step(
            "extracting requirements",
            run_requirements_extractor,
            self.run_requirements_extractor,
        )
        result["steps"]["deontic_slot_extractor"] = self._run_step(
            "deontic stage1-4 (slot extraction)",
            run_deontic_slot_extractor,
            self.run_deontic_slot_extractor,
        )
        result["steps"]["main_requirements_slot_filter"] = self._run_step(
            "filtering main requirement slots",
            run_main_slot_filter,
            self.run_main_slot_filter,
        )
        result["steps"]["embedding"] = self._run_step(
            "building embedding index",
            run_embedding,
            self.run_embedding,
        )
        result["steps"]["graph_builder"] = self._run_step(
            "building requirement graph",
            run_graph_builder,
            self.run_graph_builder,
        )
        result["steps"]["graph_visualization"] = self._run_step(
            "rendering graph visualization",
            run_graph_visualization,
            self.run_graph_visualization,
        )

        self._log("pipeline run finished")
        return result


def main() -> None:
    # -------------------------------
    # Edit config here
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    reg_input_name = "reg_for_injectiontest"  # folder under input/
    reg_input_path: str | Path | None = None  # optional explicit input path (.pdf or .json)
    pdf_to_json = False  # True: run Docling PDF->JSON first

    # main: 8, 9, 10, 11, 12, 13, 14, 15
    main_articles = [8, 9, 10, 11, 12, 13, 14, 15]
    # 1-depth context additions: 72, 79, 60, 97, 26
    context_articles = [72, 79, 60, 97, 26]

    pipeline = RegPrepPipeline(
        project_root=project_root,
        reg_input_name=reg_input_name,
        reg_input_path=reg_input_path,
        pdf_to_json=pdf_to_json,
        main_articles=main_articles,
        depth_one_articles=context_articles,
    )
    summary = pipeline.run(
        run_pdf_to_json=pdf_to_json,
        run_requirements_extractor=True,
        run_deontic_slot_extractor=True,
        run_main_slot_filter=True,
        run_embedding=True,
        run_graph_builder=True,
        run_graph_visualization=True,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
