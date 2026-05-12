from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class InjectionAutoPipeline:
    """
    End-to-end pipeline runner using input folder names only.
    Default inputs:
    - REA: input/rea_with_injections
    - REG: input/reg_for_injectiontest
    """

    def __init__(
        self,
        project_root: str | Path,
        rea_input_name: str = "rea_with_injections",
        reg_input_name: str = "reg_for_injectiontest",
        main_articles: list[int] | None = None,
        context_articles: list[int] | None = None,
        vector_k: int = 100,
        rerank_k: int = 100,
        retrieve_k: int = 5,
        send_prompts: bool = False,
        prompt_model_name: str = "gpt-4o",
        overwrite_output_folders_if_exist: bool = True,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))

        self.rea_input_name = rea_input_name.strip()
        self.reg_input_name = reg_input_name.strip()
        self.send_prompts = bool(send_prompts)
        self.prompt_model_name = str(prompt_model_name or "gpt-4o").strip()
        self.overwrite_output_folders_if_exist = bool(overwrite_output_folders_if_exist)
        self.main_articles = main_articles if main_articles is not None else [8, 9, 10, 11, 12, 13, 14, 15]
        self.context_articles = context_articles if context_articles is not None else [72, 79, 60, 97, 26]
        self.vector_k = max(1, int(vector_k))
        self.rerank_k = max(1, int(rerank_k))
        self.prompt_top_k = max(1, int(retrieve_k))

        from pipeline.Orchestrate_RegPrepPipeline import RegPrepPipeline
        from pipeline.extractor.ReaRequirementsExtractor import ReaRequirementsExtractor
        from pipeline.reasoning.ReaDeonticStagePipeline import ReaDeonticStagePipeline
        from pipeline.reasoning.ReadableLlmResponse import ReadableLlmResponse
        from pipeline.reasoning.SendPrompt import SendPrompt
        from pipeline.reasoning.SingleReaStep2To4Pipeline import SingleReaStep2To4Pipeline
        from pipeline.retrieval.GraphTraversal_v2 import GraphTraversal
        from pipeline.retrieval.Reranker import Reranker
        from pipeline.retrieval.VectorEmbedding_v2 import VectorSearch

        self.RegPrepPipeline = RegPrepPipeline
        self.ReaRequirementsExtractor = ReaRequirementsExtractor
        self.ReaDeonticStagePipeline = ReaDeonticStagePipeline
        self.VectorSearch = VectorSearch
        self.Reranker = Reranker
        self.GraphTraversal = GraphTraversal
        self.SingleReaStep2To4Pipeline = SingleReaStep2To4Pipeline
        self.SendPrompt = SendPrompt
        self.ReadableLlmResponse = ReadableLlmResponse

        self.env_path = self.project_root / "pipeline" / "reasoning" / ".env"

        self.rea_input_root = self.project_root / "input" / self.rea_input_name
        self.rea_chunked_dir = self.rea_input_root / "chunked_texts"
        if not self.rea_chunked_dir.exists():
            self.rea_chunked_dir = self.rea_input_root

        self.reg_input_root = self.project_root / "input" / self.reg_input_name
        self.reg_output_root = self.project_root / "intermediate_results" / self.reg_input_name

        self.rea_requirements_root = self.project_root / "intermediate_results" / self.rea_input_name
        self.rea_deontic_root = self.project_root / "intermediate_results" / f"{self.rea_input_name}_deontic_stages"

        tag = self._safe_name(f"{self.rea_input_name}__{self.reg_input_name}")
        self.artifact_01_root = self.project_root / "intermediate_outputs" / f"artifact_01_{tag}"
        self.artifact_01_reranked_root = self.project_root / "intermediate_outputs" / f"artifact_01_{tag}_reranked"
        self.graph_context_root = self.project_root / "intermediate_outputs" / f"graph_context_{tag}"
        self.prompts_root = self.project_root / "intermediate_outputs" / f"prompts_{tag}"
        self.chroma_persist_dir = self.project_root / "pipeline" / "retrieval" / "chromadb_store" / self.reg_input_name
        self.collection_name = f"requirements_{self._safe_name(self.reg_input_name)}"

    @staticmethod
    def _safe_name(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_\\-]+", "_", value).strip("_").lower()

    @staticmethod
    def _dir_has_content(path: Path) -> bool:
        if not path.exists() or not path.is_dir():
            return False
        return any(path.iterdir())

    def _clean_output_dir(self, path: Path) -> None:
        if not self.overwrite_output_folders_if_exist:
            return
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    def _resolve_reg_artifacts(self, reg_pipeline: Any | None = None) -> tuple[Path, Path]:
        """
        Resolve REG artifacts needed by downstream REA stages.
        Allows REA stages to run independently from REG stages.
        """
        if reg_pipeline is not None:
            return Path(reg_pipeline.output_main_slots), Path(reg_pipeline.output_graph_json)
        reg_main_slots = self.reg_output_root / f"{self.reg_input_name}_requirements_slots_main.json"
        reg_graph_json = self.reg_output_root / f"{self.reg_input_name}_requirements_graph.json"
        if not reg_main_slots.exists():
            raise FileNotFoundError(f"Missing REG slots file for REA retrieval: {reg_main_slots}")
        if not reg_graph_json.exists():
            raise FileNotFoundError(f"Missing REG graph file for prompt generation: {reg_graph_json}")
        return reg_main_slots, reg_graph_json

    def run_reg_pipeline(self) -> dict[str, Any]:
        reg_pipeline = self.RegPrepPipeline(
            project_root=self.project_root,
            reg_input_name=self.reg_input_name,
            main_articles=self.main_articles,
            depth_one_articles=self.context_articles,
        )

        reg_summary = reg_pipeline.run(
            run_requirements_extractor=True,
            run_deontic_slot_extractor=True,
            run_main_slot_filter=True,
            run_graph_builder=True,
            run_graph_visualization=True,
        )
        return reg_summary

    def run_rea_requirements_extractor(self) -> dict[str, Any]:
        self._clean_output_dir(self.rea_requirements_root)
        saved_paths = self.ReaRequirementsExtractor.process_folder(
            input_folder=self.rea_chunked_dir,
            output_root_folder=self.rea_requirements_root,
        )
        return {
            "input_folder": str(self.rea_chunked_dir),
            "output_root": str(self.rea_requirements_root),
            "file_count": len(saved_paths),
        }

    def run_rea_deontic_stage_pipeline(self) -> dict[str, Any]:
        stage_runner = self.ReaDeonticStagePipeline(
            endpoint_url="http://localhost:11434/api/chat",
            model_name="llama3",
            timeout_seconds=240,
            max_retries=3,
            temperature=0.1,
        )
        stage_report = stage_runner.run_folder(
            input_root=self.rea_requirements_root,
            output_root=self.rea_deontic_root,
        )
        return {"report": str(stage_report)}

    def run_rea_deontic_stage1_3(self) -> dict[str, Any]:
        self._clean_output_dir(self.rea_deontic_root)
        stage_runner = self.ReaDeonticStagePipeline(
            endpoint_url="http://localhost:11434/api/chat",
            model_name="llama3",
            timeout_seconds=240,
            max_retries=3,
            temperature=0.1,
        )
        stage_report = stage_runner.run_folder_stage1_3(
            input_root=self.rea_requirements_root,
            output_root=self.rea_deontic_root,
        )
        return {"report": str(stage_report)}

    def run_rea_deontic_stage4_from_saved_stage3(self) -> dict[str, Any]:
        stage_runner = self.ReaDeonticStagePipeline(
            endpoint_url="http://localhost:11434/api/chat",
            model_name="llama3",
            timeout_seconds=240,
            max_retries=3,
            temperature=0.1,
        )
        stage_report = stage_runner.run_folder_stage4_from_saved_stage3(
            input_root=self.rea_requirements_root,
            output_root=self.rea_deontic_root,
        )
        return {"report": str(stage_report)}

    def run_vector_embedding_and_search(self, reg_main_slots: str | Path) -> dict[str, Any]:
        self._clean_output_dir(self.artifact_01_root)
        reg_main_slots_path = Path(reg_main_slots).expanduser().resolve()
        embedding_input_path = reg_main_slots_path
        fallback_reason = ""

        # If slot-main file is empty, fall back to requirements file so
        # embedding + retrieval can still proceed.
        try:
            payload = json.loads(reg_main_slots_path.read_text(encoding="utf-8"))
            rows = payload.get("results", []) if isinstance(payload, dict) else payload
            is_empty = not isinstance(rows, list) or len(rows) == 0
            if is_empty:
                candidate = self.reg_output_root / f"{self.reg_input_name}_requirements.json"
                if candidate.exists():
                    embedding_input_path = candidate
                    fallback_reason = (
                        f"{reg_main_slots_path.name} had no rows; "
                        f"fallback to {candidate.name}"
                    )
        except Exception:
            # Keep default input if inspection fails.
            pass

        vector = self.VectorSearch(
            model_name="BAAI/bge-large-en-v1.5",
            collection_name=self.collection_name,
        )
        embed_result = vector.embed_and_store(
            input_json_path=embedding_input_path,
            chroma_persist_dir=self.chroma_persist_dir,
            batch_size=32,
        )
        search_result = vector.vector_search_for_rea_folder(
            rea_json_root_path=self.rea_deontic_root,
            chroma_persist_dir=self.chroma_persist_dir,
            artifact_root_dir=self.artifact_01_root,
            top_k=self.vector_k,
        )
        return {
            "embedding_input_path": str(embedding_input_path),
            "fallback_reason": fallback_reason,
            "embed_result": embed_result,
            "search_result": {
                "chunk_count": search_result.get("chunk_count"),
                "artifact_root_dir": search_result.get("artifact_root_dir"),
                "files_written": len(search_result.get("files_written", [])),
            },
        }

    def run_reranker(self) -> dict[str, Any]:
        self._clean_output_dir(self.artifact_01_reranked_root)
        load_dotenv(self.env_path)
        reranker = self.Reranker(
            model_name="kanon-2-reranker",
            api_key_env="ISAACUS_API_KEY",
        )
        rerank_result = reranker.rerank_artifact_root(
            input_artifact_01_dir=self.artifact_01_root,
            output_artifact_dir=self.artifact_01_reranked_root,
            top_n=self.rerank_k,
        )
        return {
            "input_root": rerank_result.get("input_root"),
            "output_root": rerank_result.get("output_root"),
            "chunk_count": rerank_result.get("chunk_count"),
        }

    def run_graph_traversal_v2(self, reg_graph_json: str | Path) -> dict[str, Any]:
        self._clean_output_dir(self.graph_context_root)
        reranked_input_root = self.artifact_01_reranked_root
        traversal = self.GraphTraversal(Path(reg_graph_json).expanduser().resolve())
        result = traversal.process_reranked_root(
            reranked_root=reranked_input_root,
            output_root=self.graph_context_root,
            top_k=max(1, self.prompt_top_k),
            max_hop=1,
        )
        result["reranked_input_root_resolved"] = str(reranked_input_root)
        return result

    def run_prompt_generation(self, reg_graph_json: str | Path, reg_main_slots: str | Path) -> dict[str, Any]:
        self._clean_output_dir(self.prompts_root)
        prompt_pipeline = self.SingleReaStep2To4Pipeline(
            project_root=self.project_root,
            reg_graph_json=Path(reg_graph_json).expanduser().resolve(),
            reg_slots_json=Path(reg_main_slots).expanduser().resolve(),
            rea_stage_root=self.rea_deontic_root,
        )
        # Prefer precomputed graph context artifacts from Block 3 so prompt
        # generation uses exactly those edges (no graph-context rebuild here).
        if self._dir_has_content(self.graph_context_root):
            prompt_report = prompt_pipeline.run_folder_from_graph_context_root(
                graph_context_root=self.graph_context_root,
                output_root=self.prompts_root,
                top_k=self.prompt_top_k,
            )
        else:
            # Backward-compatible fallback if Block 3 was skipped.
            prompt_report = prompt_pipeline.run_folder(
                reranked_root=self.artifact_01_reranked_root,
                output_root=self.prompts_root,
                top_k=self.prompt_top_k,
            )
        return {"report": str(prompt_report)}

    def run_send_prompt(self) -> dict[str, Any]:
        if self.send_prompts:
            sender = self.SendPrompt(
                env_path=self.env_path,
                model_name=self.prompt_model_name,
            )
            prompt_files = sorted(self.prompts_root.rglob("step4_prompt_payload.json"))
            sent: list[str] = []
            for prompt_file in prompt_files:
                saved = sender.send_prompt_json(prompt_json_path=prompt_file)
                sent.append(str(saved))
            return {
                "enabled": True,
                "model": self.prompt_model_name,
                "sent_count": len(sent),
            }
        return {"enabled": False, "model": self.prompt_model_name, "sent_count": 0}

    def run_readable_llm_response(self) -> dict[str, Any]:
        formatter = self.ReadableLlmResponse()
        response_files = sorted(self.prompts_root.rglob("*_llm_response.json"))
        formatted: list[dict[str, str]] = []
        for response_file in response_files:
            formatted.append(formatter.run(llm_response_json=response_file))
        return {
            "input_count": len(response_files),
            "output_count": len(formatted),
        }

    def run_block_rea_preprocessing(self) -> dict[str, Any]:
        """
        Block 1:
        - run_rea_requirements_extractor()
        - run_rea_deontic_stage1_3()
        (manual review/edit of stage3_output happens after this block)
        """
        return {
            "rea_requirements_extractor": self.run_rea_requirements_extractor(),
            "rea_deontic_stage1_3": self.run_rea_deontic_stage1_3(),
        }

    def run_block_retrieval(self, reg_main_slots: str | Path) -> dict[str, Any]:
        """
        Block 2:
        - run_rea_deontic_stage4_from_saved_stage3()  # consumes reviewed stage3_output
        - run_vector_embedding_and_search(...)
        - run_reranker()
        """
        return {
            "rea_deontic_stage4": self.run_rea_deontic_stage4_from_saved_stage3(),
            "vector_embedding_v2": self.run_vector_embedding_and_search(reg_main_slots=reg_main_slots),
            "reranker": self.run_reranker(),
        }

    def run_block_graph_traversal(self, reg_graph_json: str | Path) -> dict[str, Any]:
        """
        Block 3:
        - run_graph_traversal_v2(...)
        """
        return {
            "graph_traversal_v2": self.run_graph_traversal_v2(reg_graph_json=reg_graph_json),
        }

    def run_block_reasoning(self, reg_graph_json: str | Path, reg_main_slots: str | Path) -> dict[str, Any]:
        """
        Block 4:
        - run_prompt_generation(...)
        - run_send_prompt()  # optional, controlled by send_prompts flag
        - run_readable_llm_response()
        """
        return {
            "generate_prompt": self.run_prompt_generation(
                reg_graph_json=reg_graph_json,
                reg_main_slots=reg_main_slots,
            ),
            "send_prompt": self.run_send_prompt(),
            "readable_llm_response": self.run_readable_llm_response(),
        }

    def run_rea_pipeline(self, reg_pipeline: Any | None = None) -> dict[str, Any]:
        """
        Backward-compatible full REA run.
        """
        reg_main_slots, reg_graph_json = self._resolve_reg_artifacts(reg_pipeline)
        summary: dict[str, Any] = {"steps": {}}
        summary["steps"]["rea_requirements_extractor"] = self.run_rea_requirements_extractor()
        summary["steps"]["rea_deontic_stage1_3"] = self.run_rea_deontic_stage1_3()
        summary["steps"]["rea_deontic_stage4"] = self.run_rea_deontic_stage4_from_saved_stage3()
        summary["steps"]["vector_embedding_v2"] = self.run_vector_embedding_and_search(reg_main_slots=reg_main_slots)
        summary["steps"]["reranker"] = self.run_reranker()
        summary["steps"]["generate_prompt"] = self.run_prompt_generation(
            reg_graph_json=reg_graph_json,
            reg_main_slots=reg_main_slots,
        )
        summary["steps"]["send_prompt"] = self.run_send_prompt()
        summary["steps"]["readable_llm_response"] = self.run_readable_llm_response()
        return summary

    def run(
        self,
        run_reg_pipeline: bool = True,
        run_rea_requirements_extractor: bool = True,
        run_rea_deontic_stage_pipeline: bool = True,
        run_vector_embedding: bool = True,
        run_reranker: bool = True,
        run_prompt_generation: bool = True,
        run_send_prompt: bool = True,
        run_readable_llm_response: bool = True,
    ) -> dict[str, Any]:
        reg_pipeline: Any | None = None
        reg_summary: dict[str, Any] | dict[str, str]
        if run_reg_pipeline:
            reg_pipeline = self.RegPrepPipeline(
                project_root=self.project_root,
                reg_input_name=self.reg_input_name,
                main_articles=self.main_articles,
                depth_one_articles=self.context_articles,
            )
            reg_summary = reg_pipeline.run(
                run_requirements_extractor=True,
                run_deontic_slot_extractor=True,
                run_main_slot_filter=True,
                run_graph_builder=True,
                run_graph_visualization=True,
            )
        else:
            reg_summary = {"status": "skipped"}

        reg_main_slots, reg_graph_json = self._resolve_reg_artifacts(reg_pipeline)
        rea_summary: dict[str, Any] = {"steps": {}}

        if run_rea_requirements_extractor:
            rea_summary["steps"]["rea_requirements_extractor"] = self.run_rea_requirements_extractor()
        else:
            rea_summary["steps"]["rea_requirements_extractor"] = {"status": "skipped"}

        if run_rea_deontic_stage_pipeline:
            rea_summary["steps"]["rea_deontic_stage1_3"] = self.run_rea_deontic_stage1_3()
            rea_summary["steps"]["rea_deontic_stage4"] = self.run_rea_deontic_stage4_from_saved_stage3()
        else:
            rea_summary["steps"]["rea_deontic_stage1_3"] = {"status": "skipped"}
            rea_summary["steps"]["rea_deontic_stage4"] = {"status": "skipped"}

        if run_vector_embedding:
            rea_summary["steps"]["vector_embedding_v2"] = self.run_vector_embedding_and_search(reg_main_slots=reg_main_slots)
        else:
            rea_summary["steps"]["vector_embedding_v2"] = {"status": "skipped"}

        if run_reranker:
            rea_summary["steps"]["reranker"] = self.run_reranker()
        else:
            rea_summary["steps"]["reranker"] = {"status": "skipped"}

        if run_prompt_generation:
            rea_summary["steps"]["generate_prompt"] = self.run_prompt_generation(
                reg_graph_json=reg_graph_json,
                reg_main_slots=reg_main_slots,
            )
        else:
            rea_summary["steps"]["generate_prompt"] = {"status": "skipped"}

        if run_send_prompt:
            rea_summary["steps"]["send_prompt"] = self.run_send_prompt()
        else:
            rea_summary["steps"]["send_prompt"] = {"status": "skipped"}

        if run_readable_llm_response:
            rea_summary["steps"]["readable_llm_response"] = self.run_readable_llm_response()
        else:
            rea_summary["steps"]["readable_llm_response"] = {"status": "skipped"}

        return {
            "project_root": str(self.project_root),
            "inputs": {
                "rea_input_name": self.rea_input_name,
                "reg_input_name": self.reg_input_name,
            },
            "runtime": {
                "send_prompts": self.send_prompts,
                "prompt_model_name": self.prompt_model_name,
                "overwrite_output_folders_if_exist": self.overwrite_output_folders_if_exist,
                "main_articles": self.main_articles,
                "context_articles": self.context_articles,
                "vector_k": self.vector_k,
                "rerank_k": self.rerank_k,
                "prompt_top_k": self.prompt_top_k,
            },
            "outputs": {
                "reg_output_root": str(self.reg_output_root),
                "rea_requirements_root": str(self.rea_requirements_root),
                "rea_deontic_root": str(self.rea_deontic_root),
                "artifact_01_root": str(self.artifact_01_root),
                "artifact_01_reranked_root": str(self.artifact_01_reranked_root),
                "graph_context_root": str(self.graph_context_root),
                "prompts_root": str(self.prompts_root),
            },
            "reg_pipeline": reg_summary,
            "rea_pipeline": rea_summary,
        }


def main() -> None:
    # -------------------------------
    # Edit config here (code-first)
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    rea_input_name = "rea_with_injections"      # folder under input/
    reg_input_name = "reg_for_injectiontest"    # folder under input/

    # main: 8, 9, 10, 11, 12, 13, 14, 15
    main_articles = [8, 9, 10, 11, 12, 13, 14, 15]
    # 1-depth context additions: 72, 79, 60, 97, 26
    context_articles = [72, 79, 60, 97, 26]

    # retrieval knobs
    vector_k = 100   # dense retrieval top-k
    rerank_k = 100   # reranker top-k
    retrieve_k = 5   # prompt generation top-k

    runner = InjectionAutoPipeline(
        project_root=project_root,
        rea_input_name=rea_input_name,
        reg_input_name=reg_input_name,
        main_articles=main_articles,
        context_articles=context_articles,
        vector_k=vector_k,
        rerank_k=rerank_k,
        retrieve_k=retrieve_k,
        send_prompts=False,
        prompt_model_name="gpt-4o",
    )

    # -------------------------------
    # Block flags
    # -------------------------------
    run_reg_pipeline = True
    run_block_rea_preprocessing = True
    run_block_retrieval = True
    run_block_reasoning = True

    summary: dict[str, Any] = {"blocks": {}}
    if run_reg_pipeline:
        summary["blocks"]["reg_pipeline"] = runner.run_reg_pipeline()
    else:
        summary["blocks"]["reg_pipeline"] = {"status": "skipped"}

    reg_main_slots = runner.reg_output_root / f"{runner.reg_input_name}_requirements_slots_main.json"
    reg_graph_json = runner.reg_output_root / f"{runner.reg_input_name}_requirements_graph.json"

    if run_block_rea_preprocessing:
        summary["blocks"]["rea_preprocessing"] = runner.run_block_rea_preprocessing()
    else:
        summary["blocks"]["rea_preprocessing"] = {"status": "skipped"}

    if run_block_retrieval:
        summary["blocks"]["retrieval"] = runner.run_block_retrieval(reg_main_slots=reg_main_slots)
    else:
        summary["blocks"]["retrieval"] = {"status": "skipped"}

    if run_block_reasoning:
        summary["blocks"]["reasoning"] = runner.run_block_reasoning(
            reg_graph_json=reg_graph_json,
            reg_main_slots=reg_main_slots,
        )
    else:
        summary["blocks"]["reasoning"] = {"status": "skipped"}

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
