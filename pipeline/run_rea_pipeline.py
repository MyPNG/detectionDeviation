from __future__ import annotations

"""
Beginner-friendly demo for the REA pipeline.

Pipeline blocks:
0) REA head preprocessing (optional): ReaChunkSplitter
1) REA preprocessing: requirements extractor + deontic stage1-3
2) Retrieval: deontic stage4 + vector search + reranker
3) Graph context traversal
4) Reasoning prep: prompt generation (+ optional send prompt) + readable output
5) REA tail postprocessing (optional): EndResultExtractor

Safe note:
- `send_prompts=False` by default, so no external LLM API call is made.
- Intermediate outputs are written under intermediate_results/01_preprocessing and intermediate_results/02_processing.
- You can run Block 4B + Block 5 later (send/readable/report only) without rerunning Blocks 1-4A.
"""

import json
import sys
from pathlib import Path

project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pipeline.Orchestrate_ReaPipelines import InjectionAutoPipeline


def main() -> None:
    # Project root (your local repo).
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    # Run mode:
    # - "prepare_prompts": run REA up to prompt generation (no API send)
    # - "send_only": send/read existing prompts only
    run_mode = "send_only"

    send_prompts = run_mode == "send_only"
    use_rea_chunk_splitter = False # set this to False if you already have chunks


    # Keep True unless you explicitly want to skip a block.
    if run_mode == "send_only":
        run_block0_head = False # chunk splitting
        run_block1_rea_preprocessing = False # requirements extraction/stage1-3
        run_block2_retrieval = False # stage4/retrieval/rerank again
        run_block3_graph_traversal = False
        run_block4a_prompt_generation = True
        run_block4b_send_and_readable = True
        run_block5_postprocessing = True
    else:
        run_block0_head = use_rea_chunk_splitter
        run_block1_rea_preprocessing = True
        run_block2_retrieval = True
        run_block3_graph_traversal = False
        run_block4a_prompt_generation = True
        run_block4b_send_and_readable = False
        run_block5_postprocessing = False

    runner = InjectionAutoPipeline(
        project_root=project_root,
        rea_input_name="rea_case3_injections", # set name of folder where rea chunks are
        reg_input_name="reg_eu_ai_act", # set name of folder where reg pdf is
        vector_k=100,
        rerank_k=100,
        retrieve_k=3,
        send_prompts=send_prompts,
        prompt_model_name="gpt-5.4",
        cache_system_prompt=True,
        use_rea_chunk_splitter=use_rea_chunk_splitter,
        rea_full_text_filename="rea_full_text.txt",
        rea_chunk_output_folder_name="chunked_texts_generated",
        rea_chunk_entries_per_file=5,
    )

    # These files are expected from REG preparation.
    reg_main_slots = runner.reg_main_slots_path
    reg_graph_json = runner.reg_graph_json_path

    # Block 0 (optional): REA full text -> chunked_texts_generated
    block0 = (
        runner.run_block_rea_preprocessing_head(run_chunk_splitter=True)
        if run_block0_head
        else {"rea_chunk_splitter": {"status": "skipped"}}
    )

    # Block 1: REA preprocessing (stage1-3)
    block1 = (
        runner.run_block_rea_preprocessing()
        if run_block1_rea_preprocessing
        else {"status": "skipped"}
    )

    # Optional manual review step:
    # At this point you can inspect/edit stage3 output before running block2.

    # Block 2: stage4 + retrieval
    block2 = (
        runner.run_block_retrieval(reg_main_slots=reg_main_slots)
        if run_block2_retrieval
        else {"status": "skipped"}
    )

    # Block 3: graph traversal context
    block3 = (
        runner.run_block_graph_traversal(reg_graph_json=reg_graph_json)
        if run_block3_graph_traversal
        else {"status": "skipped"}
    )

    # Block 4: prompt generation + (optional send) + readable formatting
    block4a = (
        runner.run_block_prompt_generation(
            reg_graph_json=reg_graph_json,
            reg_main_slots=reg_main_slots,
            use_graph_context=run_block3_graph_traversal,
        )
        if run_block4a_prompt_generation
        else {"status": "skipped"}
    )

    block4b = (
        runner.run_block_send_and_readable()
        if run_block4b_send_and_readable
        else {"status": "skipped", "reason": "run_block4b_send_and_readable=False"}
    )

    # Block 5 (optional): extract final end report from LLM responses.
    block5 = (
        runner.run_block_postprocessing(run_end_result_extractor=True)
        if run_block5_postprocessing
        else {"status": "skipped", "reason": "run_block5_postprocessing=False"}
    )

    print(json.dumps({"block0_preprocessing_head": block0}, indent=2, ensure_ascii=False))
    print(json.dumps({"block1_rea_preprocessing": block1}, indent=2, ensure_ascii=False))
    print(json.dumps({"block2_retrieval": block2}, indent=2, ensure_ascii=False))
    print(json.dumps({"block3_graph_traversal": block3}, indent=2, ensure_ascii=False))
    print(json.dumps({"block4a_prompt_generation": block4a}, indent=2, ensure_ascii=False))
    print(json.dumps({"block4b_send_and_readable": block4b}, indent=2, ensure_ascii=False))
    print(json.dumps({"block5_postprocessing_tail": block5}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
