from __future__ import annotations

"""
Beginner-friendly demo for the REG preparation pipeline.

What this script does:
1) Loads regulation input from input/<reg_input_name>
2) Extracts requirements (main + extended)
3) Runs deontic slot extraction
4) Filters slots to main requirements
5) Builds embedding index for main requirements
6) Builds + visualizes regulation graph

Safe note:
- This script writes outputs under intermediate_results/01_preprocessing/reg_prep/...
"""

import json
import sys
from pathlib import Path

project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pipeline.Orchestrate_RegPrepPipeline import RegPrepPipeline


def main() -> None:
    # Project root (your local repo)
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()

    # Folder name under /input
    reg_input_name = "reg"

    # Set True only if you provide PDF input and want Docling PDF->JSON first
    pdf_to_json = False

    # Articles of primary interest
    # use case 1 : 6, 13, 14, 15, 17, 18, 20, 21, 46, 71
    # use case 2: 6, 12, 13, 15, 16, 17, 20, 21, 33, 34, 46, 49
    # use case 3: 9, 10, 11, 13, 14, 15
    main_articles = [6, 13, 14, 15, 17, 18, 20, 21, 46, 71] # embedding index on these

    # One-hop context additions (extra articles for wider context)
    context_articles = []

    pipeline = RegPrepPipeline(
        project_root=project_root,
        reg_input_name=reg_input_name,
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
