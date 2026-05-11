from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    # -------------------------------
    # Project root and imports
    # -------------------------------
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from pipeline.handlePdfInput.DoclingProcessor import DoclingProcessor
    from pipeline.extractor.RequirementsExtractor import RequirementsExtractor
    from pipeline.graphBuilder.additional_reference_detector import AdditionalReferenceDetector
    from pipeline.graphBuilder.RequirementsGraphBuilder import RequirementsGraphBuilder

    # -------------------------------
    # Configuration
    # -------------------------------
    input_pdf = project_root / "input" / "reg_eu_ai_act" / "EU_AI_ACT.pdf"
    output_md = project_root / "input" / "reg_eu_ai_act" / "eu_ai_act.md"
    output_docling_json = project_root / "input" / "reg_eu_ai_act" / "eu_ai_act.json"

    output_requirements_json = (
        project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements.json"
    )
    output_requirements_with_refs_json = (
        project_root
        / "intermediate_results"
        / "reg_eu_ai_act"
        / "eu_ai_requirements_with_additional_references.json"
    )
    output_graph_graphml = (
        project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_graph.graphml"
    )
    output_graph_json = (
        project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_graph.json"
    )

    # Optional: limit to selected articles. Set to None for full document.
    include_articles: list[int] | None = None
    # Example:
    # include_articles = [8, 9, 10, 11, 12, 13, 14, 15, 26, 60, 72, 79, 97]

    # -------------------------------
    # Run flags
    # -------------------------------
    run_docling = True
    run_requirements_extractor = True
    run_additional_reference_detector = True
    run_graph_builder = True

    print("Project root:", project_root)
    print("Config loaded.")

    # -------------------------------
    # Step 1: Docling (PDF -> MD -> JSON)
    # -------------------------------
    if run_docling:
        processor = DoclingProcessor()

        markdown_output = processor.pdf_to_markdown_for_articles(
            pdf_path=input_pdf,
            include_articles=include_articles,
        )
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(markdown_output, encoding="utf-8")
        print(f"Saved markdown: {output_md}")

        json_payload = processor.markdown_to_json(
            md_path=output_md,
            include_articles=include_articles,
        )
        output_docling_json.parent.mkdir(parents=True, exist_ok=True)
        output_docling_json.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved Docling JSON: {output_docling_json}")
    else:
        print("Skipped Step 1 (Docling).")

    # -------------------------------
    # Step 2: RequirementsExtractor
    # -------------------------------
    if run_requirements_extractor:
        extractor = RequirementsExtractor(output_docling_json)
        saved_requirements = extractor.save_requirements(output_requirements_json)
        print(f"Saved requirements: {saved_requirements}")
    else:
        print("Skipped Step 2 (RequirementsExtractor).")

    # -------------------------------
    # Step 3: AdditionalReferenceDetector
    # -------------------------------
    if run_additional_reference_detector:
        payload = json.loads(output_requirements_json.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected list in requirements JSON: {output_requirements_json}")

        detector = AdditionalReferenceDetector()
        enriched = detector.add_additional_references_to_clauses(
            clauses=payload,
            text_field="Text",
            article_field="Article",
            references_field="references",
        )
        output_requirements_with_refs_json.parent.mkdir(parents=True, exist_ok=True)
        output_requirements_with_refs_json.write_text(
            json.dumps(enriched, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved requirements with references: {output_requirements_with_refs_json}")
    else:
        print("Skipped Step 3 (AdditionalReferenceDetector).")

    # -------------------------------
    # Step 4: RequirementsGraphBuilder
    # -------------------------------
    if run_graph_builder:
        builder = RequirementsGraphBuilder(output_requirements_with_refs_json)
        graph = builder.build_graph()
        graphml_path = builder.save_graph_graphml(output_graph_graphml)
        json_path = builder.save_graph_json(output_graph_json)
        print(f"Graph nodes: {graph.number_of_nodes()} | edges: {graph.number_of_edges()}")
        print(f"Saved GraphML: {graphml_path}")
        print(f"Saved graph JSON: {json_path}")
    else:
        print("Skipped Step 4 (RequirementsGraphBuilder).")


if __name__ == "__main__":
    main()

