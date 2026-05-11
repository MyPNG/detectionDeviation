from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    # -------------------------------
    # Bootstrap
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    print("Project root:", project_root)
    print("Exists:", project_root.exists())

    # -------------------------------
    # Core input/output paths
    # -------------------------------
    input_rea_with_injections = project_root / "input" / "rea_no_injections"
    policy_full_text_file = input_rea_with_injections / "rea_full_text.txt.txt"
    # Fallback if typo-path does not exist.
    if not policy_full_text_file.exists():
        fallback_policy = input_rea_with_injections / "rea_full_text.txt"
        if fallback_policy.exists():
            policy_full_text_file = fallback_policy

    chunked_text_dir = input_rea_with_injections / "chunked_texts"
    chunked_policy_json = chunked_text_dir / "chunked_policy.json"
    chunked_text_overlap_dir = input_rea_with_injections / "chunked_texts_overlapping_window"

    # REA requirements extracted from chunk*.txt files
    rea_requirements_root = project_root / "intermediate_results" / "rea_no_injections"

    # REG requirements (for vector DB + graph)
    reg_requirements_json = (
        project_root / "intermediate_results" / "reg" / "gdpr_requirements_with_additional_references.json"
    )

    # Vector DB + retrieval outputs
    chroma_persist_dir = project_root / "pipeline" / "retrieval" / "chromadb_store"
    artifact_01_dir = project_root / "intermediate_outputs" / "artifact_01_reranked"
    artifact_01_reranked_dir = project_root / "intermediate_outputs" / "artifact_01_reranked"
    artifact_02_dir = project_root / "intermediate_outputs" / "artifact_02_reranked"
    artifact_03_dir = project_root / "intermediate_outputs" / "artifact_03_reranked_schema_v2"

    # Prompt sender / OpenAI config
    reasoning_env_path = project_root / "pipeline" / "reasoning" / ".env"
    openai_model = "gpt-5"

    # -------------------------------
    # Run flags
    # -------------------------------
    run_policy_chunker = True
    run_overlap_builder = True
    run_rea_requirements_extractor = True
    run_vector_search = True
    run_reranker = True
    run_main_clause_extractor = True
    run_graph_traversal = True
    run_prompt_generation = True
    run_prompt_sending = False  # keep False by default to avoid accidental API spend

    # -------------------------------
    # Pipeline behavior
    # -------------------------------
    use_overlap_for_rea_requirements = True
    build_vector_index = True

    vector_model = "BAAI/bge-large-en-v1.5"
    vector_collection_name = "gdpr_requirements"
    vector_top_k = 20

    rerank_model = "kanon-2-reranker"
    rerank_top_n = 20
    rerank_llm_max_items = None
    main_clause_top_k = 5
    graph_max_hop = 1

    windowed_chunk_for_prompt_sender = False

    # -------------------------------
    # Evaluation config
    # -------------------------------
    goldstandard_root = project_root / "goldstandard"

    eval_experiment_name = "schema_v32"
    eval_experiment_dir = project_root / "evaluation" / "artifact3" / eval_experiment_name
    eval_experiment_dir.mkdir(parents=True, exist_ok=True)

    eval_compare_input_root = project_root / "evaluation" / "artifact3"
    eval_compare_output_dir = project_root / "evaluation" / "artifact3" / "compare_reranker_visuals"

    run_llm_output_extraction = True
    run_eval_retrieval = True
    run_eval_analysis = True
    run_eval_visualization = True

    print("Config loaded.")
    print("Eval experiment dir:", eval_experiment_dir)

    # -------------------------------
    # Step 1: Policy chunker
    # -------------------------------
    if run_policy_chunker:
        from pipeline.retrieval.Llama3PolicyChunker import Llama3PolicyChunker

        chunked_text_dir.mkdir(parents=True, exist_ok=True)
        chunker = Llama3PolicyChunker(
            endpoint_url="http://localhost:11434/api/chat",
            model_name="llama3",
            timeout_seconds=300,
            max_retries=3,
        )
        saved = chunker.chunk_policy(
            input_file=policy_full_text_file,
            output_file=chunked_policy_json,
        )
        print("Saved:", saved)
    else:
        print("Skipped Step 1")

    # -------------------------------
    # Step 2: Overlap builder
    # -------------------------------
    if run_overlap_builder:
        from pipeline.retrieval.ChunkedTextOverlapBuilder import ChunkedTextOverlapBuilder

        builder = ChunkedTextOverlapBuilder(overlap_hops=1)
        result = builder.build_overlapping_chunks(
            input_dir=chunked_text_dir,
            output_dir=chunked_text_overlap_dir,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Skipped Step 2")

    # -------------------------------
    # Step 3: REA requirements extractor
    # -------------------------------
    if run_rea_requirements_extractor:
        from pipeline.extractor.ReaRequirementsExtractor import ReaRequirementsExtractor

        source_txt_dir = chunked_text_overlap_dir if use_overlap_for_rea_requirements else chunked_text_dir
        saved_paths = ReaRequirementsExtractor.process_folder(
            input_folder=source_txt_dir,
            output_root_folder=rea_requirements_root,
        )
        print(f"Processed {len(saved_paths)} files from {source_txt_dir}")
        for path in saved_paths[:5]:
            print(" -", path)
        if len(saved_paths) > 5:
            print(" ...")
    else:
        print("Skipped Step 3")

    # -------------------------------
    # Step 4: Vector search
    # -------------------------------
    if run_vector_search:
        from pipeline.retrieval.VectorEmbedding import VectorSearch

        search = VectorSearch(
            model_name=vector_model,
            collection_name=vector_collection_name,
        )

        if build_vector_index:
            embed_result = search.embed_and_store(
                input_json_path=reg_requirements_json,
                chroma_persist_dir=chroma_persist_dir,
                batch_size=32,
            )
            print("Index build:", json.dumps(embed_result, indent=2, ensure_ascii=False))
        else:
            print("Index build skipped (reusing existing Chroma collection).")

        search_result = search.vector_search_for_rea_folder(
            rea_json_root_path=rea_requirements_root,
            chroma_persist_dir=chroma_persist_dir,
            artifact_root_dir=artifact_01_dir,
            top_k=vector_top_k,
        )
        print("Vector search:", json.dumps(search_result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 4")

    # -------------------------------
    # Step 5: Reranker
    # -------------------------------
    from dotenv import load_dotenv

    load_dotenv(reasoning_env_path)
    if run_reranker:
        from pipeline.retrieval.Reranker import Reranker

        reranker = Reranker(
            model_name=rerank_model,
            api_key_env="ISAACUS_API_KEY",
        )
        rerank_result = reranker.rerank_artifact_root(
            input_artifact_01_dir=artifact_01_dir,
            output_artifact_dir=artifact_01_reranked_dir,
            top_n=rerank_top_n,
            llm_max_items=rerank_llm_max_items,
        )
        print(json.dumps(rerank_result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 5")

    # -------------------------------
    # Step 6: Main clause extractor
    # -------------------------------
    if run_main_clause_extractor:
        from pipeline.retrieval.MainClauseExtractor import MainClauseExtractor

        extractor = MainClauseExtractor()
        result = extractor.extract_main_clauses_for_artifact(
            reranked_artifact_root_dir=artifact_01_reranked_dir,
            k=main_clause_top_k,
            output_csv_name="reg_main_clauses.csv",
        )
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 6")

    # -------------------------------
    # Step 7: Graph traversal
    # -------------------------------
    if run_graph_traversal:
        from pipeline.retrieval.GraphTraversal import GraphTraversal

        traversal = GraphTraversal(reg_requirements_json)
        graph_result = traversal.process_artifact_chunks(
            artifact_01_dir=artifact_01_reranked_dir,
            artifact_02_dir=artifact_02_dir,
            max_hop=graph_max_hop,
        )
        print(json.dumps(graph_result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 7")

    # -------------------------------
    # Step 8: Prompt generation
    # -------------------------------
    if run_prompt_generation:
        from pipeline.reasoning.PromptSender import PromptSender

        sender = PromptSender(env_path=reasoning_env_path, model_name=openai_model)
        generation_result = sender.generate_prompts_for_all_chunks(
            artifact_01_dir=artifact_01_reranked_dir,
            artifact_02_dir=artifact_02_dir,
            artifact_03_dir=artifact_03_dir,
            rea_intermediate_root_dir=rea_requirements_root,
            windowed_chunk=windowed_chunk_for_prompt_sender,
        )
        print(json.dumps(generation_result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 8")

    # -------------------------------
    # Step 9: Prompt sending
    # -------------------------------
    if run_prompt_sending:
        from pipeline.reasoning.PromptSender import PromptSender

        sender = PromptSender(env_path=reasoning_env_path, model_name=openai_model)
        sending_result = sender.send_prompts_for_all_chunks(
            artifact_03_dir=artifact_03_dir,
            temperature=None,
        )
        print(json.dumps(sending_result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 9 (run_prompt_sending=False)")

    # -------------------------------
    # Step 9.5: Existence check
    # -------------------------------
    for path in [
        chunked_policy_json,
        chunked_text_overlap_dir,
        rea_requirements_root,
        artifact_01_dir,
        artifact_01_reranked_dir,
        artifact_02_dir,
        artifact_03_dir,
    ]:
        print(path, "->", path.exists())

    # -------------------------------
    # Step 10: LLM output extraction
    # -------------------------------
    if run_llm_output_extraction:
        from pipeline.extractor.ExtractLLMOutput import ExtractLLMOutput

        extraction_result = ExtractLLMOutput.process_artifact_root(
            artifact_03_root=artifact_03_dir,
            response_filename="llm_response.json",
            output_json_filename="llm_extracted_normalized.json",
            output_csv_filename="llm_extracted_table.csv",
            output_md_filename="llm_extracted_readable.md",
        )
        print(json.dumps(extraction_result, indent=2, ensure_ascii=False)[:2000], "...")
    else:
        print("Skipped Step 10")

    # -------------------------------
    # Step 11: Retrieval evaluation (article-level merged)
    # -------------------------------
    if run_eval_retrieval:
        from evaluation.artifact3.RetrievalConfusionMatrix import RetrievalConfusionMatrix

        system_retrieval_root = artifact_01_reranked_dir if artifact_01_reranked_dir.exists() else artifact_01_dir
        analyzer = RetrievalConfusionMatrix(
            gold_root=goldstandard_root,
            system_root=system_retrieval_root,
        )

        article_gold_json = project_root / "goldstandard" / "relevant_non_relevant_articles_no_injections.json"
        reg_metadata_json = project_root / "intermediate_results" / "reg" / "gdpr_requirements_with_additional_references.json"

        merged_csv = eval_experiment_dir / "merged_main_clauses_deduplicated.csv"
        article_json = eval_experiment_dir / "retrieval_confusion_matrix_articles.json"
        article_md = eval_experiment_dir / "retrieval_confusion_matrix_articles.md"

        merged_saved = analyzer.build_deduplicated_merged_main_clauses_csv(
            output_csv=merged_csv,
            reg_metadata_json=reg_metadata_json,
        )

        saved_article_json = analyzer.save_article_relevance_json(
            article_gold_json=article_gold_json,
            merged_main_clauses_csv=merged_saved,
            output_json=article_json,
        )
        saved_article_md = analyzer.save_article_relevance_markdown(
            article_gold_json=article_gold_json,
            merged_main_clauses_csv=merged_saved,
            output_md=article_md,
        )

        print("Saved merged CSV:", merged_saved)
        print("Saved article-level JSON:", saved_article_json)
        print("Saved article-level MD:", saved_article_md)
    else:
        print("Skipped Step 11")

    # -------------------------------
    # Step 12: Analysis evaluation (merged)
    # -------------------------------
    if run_eval_analysis:
        from evaluation.artifact3.AnalysisConfusionMatrix import AnalysisConfusionMatrix

        evaluator = AnalysisConfusionMatrix(
            gold_root=goldstandard_root,
            system_root=artifact_03_dir,
        )

        gold_inj_json = project_root / "goldstandard" / "rea_no_injections.json"
        merged_system_json = eval_experiment_dir / "merged_llm_extracted_normalized.json"
        merged_eval_json = eval_experiment_dir / "analysis_confusion_matrix_merged_injections.json"
        merged_eval_md = eval_experiment_dir / "analysis_confusion_matrix_merged_injections.md"

        merged_saved = evaluator.build_merged_system_output(merged_system_json)
        saved_json = evaluator.save_merged_injection_json(gold_inj_json, merged_saved, merged_eval_json)
        saved_md = evaluator.save_merged_injection_markdown(gold_inj_json, merged_saved, merged_eval_md)

        print("Saved merged system:", merged_saved)
        print("Saved merged analysis JSON:", saved_json)
        print("Saved merged analysis MD:", saved_md)
    else:
        print("Skipped Step 12")

    # -------------------------------
    # Step 13: Visualization
    # -------------------------------
    if run_eval_visualization:
        from evaluation.artifact3.compare_retrieval_confusion_matrices import visualize_from_folder

        viz_result = visualize_from_folder(
            comparison_input_folder=eval_compare_input_root,
            output_dir=eval_compare_output_dir,
        )
        print("Visualization outputs:")
        print(json.dumps(viz_result, indent=2, ensure_ascii=False))
    else:
        print("Skipped Step 13")


if __name__ == "__main__":
    main()

