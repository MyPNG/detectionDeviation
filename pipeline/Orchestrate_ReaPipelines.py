from __future__ import annotations

import importlib
import json
import os
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
        vector_k: int = 100,
        rerank_k: int = 100,
        retrieve_k: int = 5,
        send_prompts: bool = False,
        prompt_model_name: str = "gpt-5.4",
        cache_system_prompt: bool = True,
        use_rea_chunk_splitter: bool = False,
        rea_full_text_filename: str = "rea_full_text.txt",
        rea_chunk_output_folder_name: str = "chunked_texts_generated",
        rea_chunk_entries_per_file: int = 3,
        overwrite_output_folders_if_exist: bool = True,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))

        self.rea_input_name = rea_input_name.strip()
        self.reg_input_name = reg_input_name.strip()
        self.send_prompts = bool(send_prompts)
        self.prompt_model_name = str(prompt_model_name or "gpt-5.4").strip()
        self.cache_system_prompt = bool(cache_system_prompt)
        self.use_rea_chunk_splitter = bool(use_rea_chunk_splitter)
        self.rea_full_text_filename = str(rea_full_text_filename or "rea_full_text.txt").strip()
        self.rea_chunk_output_folder_name = str(rea_chunk_output_folder_name or "chunked_texts_generated").strip()
        self.rea_chunk_entries_per_file = max(1, int(rea_chunk_entries_per_file))
        self.overwrite_output_folders_if_exist = bool(overwrite_output_folders_if_exist)
        self.vector_k = max(1, int(vector_k))
        self.rerank_k = max(1, int(rerank_k))
        self.prompt_top_k = max(1, int(retrieve_k))

        RegPrepPipeline = importlib.import_module("pipeline.Orchestrate_RegPrepPipeline").RegPrepPipeline
        ReaRequirementsExtractor = importlib.import_module(
            "pipeline.01_preprocessing.reaPrep.01_extracting.ReaRequirementsExtractor"
        ).ReaRequirementsExtractor
        ReaChunkSplitter = importlib.import_module(
            "pipeline.01_preprocessing.reaPrep.01_extracting.ReaChunkSplitter"
        ).ReaChunkSplitter
        ReaPromptPreparation = importlib.import_module(
            "pipeline.02_processing.03_reasoning.ReaPromptPreparation"
        ).ReaPromptPreparation
        ReaDeonticStagePipeline = importlib.import_module(
            "pipeline.01_preprocessing.reaPrep.01_extracting.ReaDeonticStagePipeline"
        ).ReaDeonticStagePipeline
        EndResultExtractor = importlib.import_module(
            "pipeline.03_postprocessing.EndResultExtractor"
        ).EndResultExtractor
        ReadableLlmResponse = importlib.import_module(
            "pipeline.02_processing.03_reasoning.ReadableLlmResponse"
        ).ReadableLlmResponse
        SendPrompt = importlib.import_module(
            "pipeline.02_processing.03_reasoning.SendPrompt"
        ).SendPrompt
        GraphTraversal = importlib.import_module(
            "pipeline.02_processing.02_graph_traversal.GraphTraversal"
        ).GraphTraversal
        Reranker = importlib.import_module(
            "pipeline.02_processing.01_retrieval.Reranker"
        ).Reranker
        VectorSearch = importlib.import_module(
            "pipeline.02_processing.01_retrieval.VectorSearch"
        ).VectorSearch
        EmbeddingIndexBuilder = importlib.import_module(
            "pipeline.01_preprocessing.reg_prep.02_vector_embedding.EmbeddingIndexBuilder"
        ).EmbeddingIndexBuilder

        self.RegPrepPipeline = RegPrepPipeline
        self.ReaRequirementsExtractor = ReaRequirementsExtractor
        self.ReaChunkSplitter = ReaChunkSplitter
        self.ReaDeonticStagePipeline = ReaDeonticStagePipeline
        self.EmbeddingIndexBuilder = EmbeddingIndexBuilder
        self.VectorSearch = VectorSearch
        self.Reranker = Reranker
        self.GraphTraversal = GraphTraversal
        self.ReaPromptPreparation = ReaPromptPreparation
        self.EndResultExtractor = EndResultExtractor
        self.SendPrompt = SendPrompt
        self.ReadableLlmResponse = ReadableLlmResponse

        # API keys are loaded from repository root .env by default.
        self.env_path = self.project_root / ".env"

        self.rea_input_root = self.project_root / "input" / self.rea_input_name
        self.rea_chunked_dir = self.rea_input_root / "chunked_texts"
        if not self.rea_chunked_dir.exists():
            self.rea_chunked_dir = self.rea_input_root
        self.rea_full_text_path = self.rea_input_root / self.rea_full_text_filename
        self.rea_generated_chunk_dir = self.rea_input_root / self.rea_chunk_output_folder_name

        self.reg_input_root = self.project_root / "input" / self.reg_input_name
        self.reg_output_root = self.project_root / "intermediate_results" / "01_preprocessing" / "reg_prep" / self.reg_input_name
        self.reg_main_slots_path = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reg_prep"
            / "01_extracting"
            / "mainrequirementsslotfilter"
            / self.reg_input_name
            / f"{self.reg_input_name}_requirements_slots_main.json"
        )
        self.reg_main_requirements_path = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reg_prep"
            / "01_extracting"
            / "requirementsextractor"
            / self.reg_input_name
            / f"{self.reg_input_name}_requirements.json"
        )
        self.reg_graph_json_path = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reg_prep"
            / "03_graphbuilder"
            / "requirementsgraphbuilder"
            / self.reg_input_name
            / f"{self.reg_input_name}_requirements_graph.json"
        )

        self.rea_requirements_root = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reaPrep"
            / "01_extracting"
            / "rearequirementsextractor"
            / self.rea_input_name
        )
        self.rea_deontic_root = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reaPrep"
            / "01_extracting"
            / "readeonticstagepipeline"
            / self.rea_input_name
        )

        tag = self._safe_name(f"{self.rea_input_name}__{self.reg_input_name}")
        self.artifact_01_root = (
            self.project_root
            / "intermediate_results"
            / "02_processing"
            / "01_retrieval"
            / "vectorsearch"
            / f"artifact_01_{tag}"
        )
        self.artifact_01_reranked_root = (
            self.project_root
            / "intermediate_results"
            / "02_processing"
            / "01_retrieval"
            / "reranker"
            / f"artifact_01_{tag}_reranked"
        )
        self.graph_context_root = (
            self.project_root
            / "intermediate_results"
            / "02_processing"
            / "02_graph_traversal"
            / "graphtraversal"
            / f"graph_context_{tag}"
        )
        self.prompts_root = (
            self.project_root
            / "intermediate_results"
            / "02_processing"
            / "03_reasoning"
            / "reapromptpreparation"
            / f"prompts_{tag}"
        )
        self.chroma_persist_dir = (
            self.project_root
            / "intermediate_results"
            / "01_preprocessing"
            / "reg_prep"
            / "02_vector_embedding"
            / "embeddingindexbuilder"
            / self.reg_input_name
            / "chromadb_store"
        )
        self.collection_name = f"requirements_{self._safe_name(self.reg_input_name)}"

    def run_rea_chunk_splitter(self) -> dict[str, Any]:
        """
        Optional preprocessing step:
        split one full REA text file into chunk*.txt files.
        """
        if self.rea_generated_chunk_dir.exists() and self.overwrite_output_folders_if_exist:
            shutil.rmtree(self.rea_generated_chunk_dir)
        splitter = self.ReaChunkSplitter(
            input_txt_path=self.rea_full_text_path,
            output_chunk_dir=self.rea_generated_chunk_dir,
            entries_per_chunk=self.rea_chunk_entries_per_file,
        )
        result = splitter.split()
        self.rea_chunked_dir = self.rea_generated_chunk_dir
        return {
            "input_txt": result.input_txt,
            "output_dir": result.output_dir,
            "entries_per_chunk": self.rea_chunk_entries_per_file,
            "chunk_count": result.chunk_count,
            "rea_count": result.rea_count,
            "manifest_json": result.manifest_json,
        }

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a folder/model label into a filesystem-safe slug."""
        return re.sub(r"[^a-zA-Z0-9_\\-]+", "_", value).strip("_").lower()

    @staticmethod
    def _dir_has_content(path: Path) -> bool:
        """Return True when the directory exists and has at least one entry."""
        if not path.exists() or not path.is_dir():
            return False
        return any(path.iterdir())

    def _clean_output_dir(self, path: Path, force: bool = False) -> None:
        """Clear and recreate an output directory before writing results.
        - force=False: respect overwrite_output_folders_if_exist flag
        - force=True: always clear for deterministic fresh outputs
        """
        if not force and not self.overwrite_output_folders_if_exist:
            return
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _maybe_run(enabled: bool, fn: Any) -> Any:
        """Run function when enabled, otherwise return a standardized skipped marker."""
        return fn() if enabled else {"status": "skipped"}

    def _safe_collect_files(self, root: Path, filename_pattern: re.Pattern[str]) -> tuple[list[Path], list[str]]:
        """
        Collect files under root while tolerating filesystem scan errors/timeouts.
        Returns (matched_files, scan_errors).
        """
        files: list[Path] = []
        scan_errors: list[str] = []

        if not root.exists() or not root.is_dir():
            return files, [f"missing directory: {root}"]

        def _on_error(err: OSError) -> None:
            scan_errors.append(str(err))

        for dirpath, _dirnames, filenames in os.walk(root, onerror=_on_error):
            base = Path(dirpath)
            for name in filenames:
                if filename_pattern.match(name):
                    files.append(base / name)

        return sorted(files), scan_errors

    @staticmethod
    def _log(message: str) -> None:
        """Print a consistent REA pipeline progress message."""
        print(f"[REA] {message}")

    def _run_step(self, step_name: str, enabled: bool, fn: Any) -> Any:
        """Run one REA pipeline step with terminal progress logs."""
        if not enabled:
            self._log(f"{step_name}: skipped")
            return {"status": "skipped"}
        self._log(f"{step_name}: started")
        result = fn()
        self._log(f"{step_name}: done")
        return result

    def _create_rea_deontic_stage_runner(self) -> Any:
        """Create the REA stage extractor instance with shared runtime settings."""
        return self.ReaDeonticStagePipeline(
            endpoint_url="http://localhost:11434/api/chat",
            model_name="llama3",
            timeout_seconds=240,
            max_retries=3,
            temperature=0.1,
        )

    def _resolve_reg_artifacts(self) -> tuple[Path, Path]:
        """
        Resolve REG artifacts needed by downstream REA stages.
        REA pipeline always reuses prebuilt REG artifacts.
        Expected behavior:
        - retrieval corpus comes from *_requirements_slots_main.json (main articles only)
        - graph traversal context comes from *_requirements_graph.json
          (built from extended set = main + context, or main-only if context is empty)
        """
        reg_main_slots = self.reg_main_slots_path
        reg_graph_json = self.reg_graph_json_path
        if not reg_main_slots.exists():
            raise FileNotFoundError(f"Missing REG slots file for REA retrieval: {reg_main_slots}")
        if not reg_graph_json.exists():
            raise FileNotFoundError(f"Missing REG graph file for prompt generation: {reg_graph_json}")
        return reg_main_slots, reg_graph_json

    def run_rea_requirements_extractor(self) -> dict[str, Any]:
        """Extract REA requirements from input chunks into intermediate JSON files."""
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
        """Run full REA deontic stage pipeline (stage1-4) in a single call."""
        stage_runner = self._create_rea_deontic_stage_runner()
        stage_report = stage_runner.run_folder(
            input_root=self.rea_requirements_root,
            output_root=self.rea_deontic_root,
        )
        return {"report": str(stage_report)}

    def run_rea_deontic_stage1_3(self) -> dict[str, Any]:
        """Run only REA stage1-3 and persist outputs for manual review/edit."""
        self._clean_output_dir(self.rea_deontic_root)
        stage_runner = self._create_rea_deontic_stage_runner()
        stage_report = stage_runner.run_folder_stage1_3(
            input_root=self.rea_requirements_root,
            output_root=self.rea_deontic_root,
        )
        return {"report": str(stage_report)}

    def run_rea_deontic_stage4_from_saved_stage3(self) -> dict[str, Any]:
        """Run REA stage4 using previously saved/reviewed stage3 outputs."""
        stage_runner = self._create_rea_deontic_stage_runner()
        stage_report = stage_runner.run_folder_stage4_from_saved_stage3(
            input_root=self.rea_requirements_root,
            output_root=self.rea_deontic_root,
        )
        return {"report": str(stage_report)}

    def _run_rea_steps(
        self,
        *,
        reg_main_slots: Path,
        reg_graph_json: Path,
        run_rea_requirements_extractor: bool = True,
        run_rea_deontic_stage_pipeline: bool = True,
        run_vector_embedding: bool = True,
        run_reranker: bool = True,
        run_prompt_generation: bool = True,
        run_send_prompt: bool = True,
        run_readable_llm_response: bool = True,
    ) -> dict[str, Any]:
        """Execute the configurable REA pipeline steps and return per-step results."""
        steps: dict[str, Any] = {}
        steps["rea_requirements_extractor"] = self._run_step(
            "extracting REA requirements",
            run_rea_requirements_extractor,
            self.run_rea_requirements_extractor,
        )

        if run_rea_deontic_stage_pipeline:
            steps["rea_deontic_stage1_3"] = self._run_step(
                "REA deontic stage1-3",
                True,
                self.run_rea_deontic_stage1_3,
            )
            steps["rea_deontic_stage4"] = self._run_step(
                "REA deontic stage4 (slot extraction)",
                True,
                self.run_rea_deontic_stage4_from_saved_stage3,
            )
        else:
            steps["rea_deontic_stage1_3"] = {"status": "skipped"}
            steps["rea_deontic_stage4"] = {"status": "skipped"}

        steps["vector_embedding"] = self._run_step(
            "vector embedding + dense retrieval",
            run_vector_embedding,
            lambda: self.run_vector_embedding_and_search(reg_main_slots=reg_main_slots),
        )
        steps["reranker"] = self._run_step(
            "reranking retrieval candidates",
            run_reranker,
            self.run_reranker,
        )
        steps["generate_prompt"] = self._run_step(
            "generating prompt payloads",
            run_prompt_generation,
            lambda: self.run_prompt_generation(
                reg_graph_json=reg_graph_json,
                reg_main_slots=reg_main_slots,
            ),
        )

        # Reasoning execution policy:
        # - send_prompts=False -> generate prompt only
        # - send_prompts=True  -> generate + send + readable
        if run_prompt_generation and run_send_prompt and self.send_prompts:
            steps["send_prompt"] = self._run_step(
                "sending prompts to LLM",
                True,
                self.run_send_prompt,
            )
            if run_readable_llm_response:
                steps["readable_llm_response"] = self._run_step(
                    "formatting readable LLM responses",
                    True,
                    self.run_readable_llm_response,
                )
            else:
                steps["readable_llm_response"] = {"status": "skipped"}
        else:
            steps["send_prompt"] = {"status": "skipped"}
            steps["readable_llm_response"] = {"status": "skipped"}
        return steps

    def run_vector_embedding_and_search(self, reg_main_slots: str | Path) -> dict[str, Any]:
        """Embed REG corpus and run dense vector retrieval for all REA stage outputs."""
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
                candidate = self.reg_main_requirements_path
                if candidate.exists():
                    embedding_input_path = candidate
                    fallback_reason = (
                        f"{reg_main_slots_path.name} had no rows; "
                        f"fallback to {candidate.name}"
                    )
        except Exception:
            # Keep default input if inspection fails.
            pass

        embedder = self.EmbeddingIndexBuilder(
            model_name="BAAI/bge-large-en-v1.5",
            collection_name=self.collection_name,
        )
        embed_result = embedder.embed_and_store(
            input_json_path=embedding_input_path,
            chroma_persist_dir=self.chroma_persist_dir,
            batch_size=32,
        )
        vector = self.VectorSearch(
            model_name="BAAI/bge-large-en-v1.5",
            collection_name=self.collection_name,
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
        """Rerank dense retrieval candidates and save reranked artifacts."""
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

    def run_graph_traversal(self, reg_graph_json: str | Path) -> dict[str, Any]:
        """Expand reranked REG matches with graph neighbors for legal context."""
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

    def run_prompt_generation(
        self,
        reg_graph_json: str | Path,
        reg_main_slots: str | Path,
        use_graph_context: bool = True,
    ) -> dict[str, Any]:
        """Generate per-REA prompt payloads.
        If use_graph_context=False, prompts are generated with empty graph context.
        """
        # Always start prompt generation from a clean folder so no stale
        # `chunk... 2/3` directories can survive from earlier runs.
        self._clean_output_dir(self.prompts_root, force=True)
        prompt_pipeline = self.ReaPromptPreparation(
            project_root=self.project_root,
            reg_graph_json=Path(reg_graph_json).expanduser().resolve(),
            reg_slots_json=Path(reg_main_slots).expanduser().resolve(),
            rea_stage_root=self.rea_deontic_root,
        )
        if not use_graph_context:
            prompt_report = prompt_pipeline.run_folder_without_graph_context(
                reranked_root=self.artifact_01_reranked_root,
                output_root=self.prompts_root,
                top_k=self.prompt_top_k,
            )
            return {"report": str(prompt_report), "graph_context_mode": "empty"}

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
        return {"report": str(prompt_report), "graph_context_mode": "computed"}

    def run_send_prompt(self) -> dict[str, Any]:
        """Send generated prompt payloads to LLM endpoint when sending is enabled."""
        if self.send_prompts:
            sender = self.SendPrompt(
                env_path=self.env_path,
                model_name=self.prompt_model_name,
                enable_prompt_cache=self.cache_system_prompt,
            )
            prompt_files, scan_errors = self._safe_collect_files(
                self.prompts_root,
                re.compile(r"^step4_prompt_payload(?:_\d+)?\.json$", flags=re.IGNORECASE),
            )
            sent: list[str] = []
            for prompt_file in prompt_files:
                saved = sender.send_prompt_json(prompt_json_path=prompt_file)
                sent.append(str(saved))
            return {
                "enabled": True,
                "model": self.prompt_model_name,
                "cache_system_prompt": self.cache_system_prompt,
                "sent_count": len(sent),
                "scan_error_count": len(scan_errors),
                "scan_errors": scan_errors,
            }
        return {
            "enabled": False,
            "model": self.prompt_model_name,
            "cache_system_prompt": self.cache_system_prompt,
            "sent_count": 0,
        }

    def run_readable_llm_response(self) -> dict[str, Any]:
        """Normalize and render raw LLM responses into readable JSON/Markdown outputs."""
        formatter = self.ReadableLlmResponse()
        response_files, scan_errors = self._safe_collect_files(
            self.prompts_root,
            re.compile(r"^.+_llm_response\.json$", flags=re.IGNORECASE),
        )
        formatted: list[dict[str, str]] = []
        for response_file in response_files:
            formatted.append(formatter.run(llm_response_json=response_file))
        return {
            "input_count": len(response_files),
            "output_count": len(formatted),
            "scan_error_count": len(scan_errors),
            "scan_errors": scan_errors,
        }

    def run_end_result_extractor(self) -> dict[str, Any]:
        """
        Optional postprocessing step:
        create final CSV/Markdown report from per-prompt LLM responses.
        """
        extractor = self.EndResultExtractor(project_root=self.project_root)
        return extractor.run(prompt_root=self.prompts_root, output_root=None, drop_columns=None)

    def run_block_rea_preprocessing(self) -> dict[str, Any]:
        """
        Block 1:
        - run_rea_requirements_extractor()
        - run_rea_deontic_stage1_3()
        (manual review/edit of stage3_output happens after this block)
        """
        return {
            "rea_requirements_extractor": self._run_step(
                "extracting REA requirements",
                True,
                self.run_rea_requirements_extractor,
            ),
            "rea_deontic_stage1_3": self._run_step(
                "REA deontic stage1-3",
                True,
                self.run_rea_deontic_stage1_3,
            ),
        }

    def run_block_rea_preprocessing_head(self, run_chunk_splitter: bool = True) -> dict[str, Any]:
        """
        Block 0 (head preprocessing):
        - optional chunk splitting from rea_full_text.txt
        """
        if run_chunk_splitter:
            return {
                "rea_chunk_splitter": self._run_step(
                    "splitting REA full text into chunks",
                    True,
                    self.run_rea_chunk_splitter,
                )
            }
        return {"rea_chunk_splitter": {"status": "skipped"}}

    def run_block_retrieval(self, reg_main_slots: str | Path) -> dict[str, Any]:
        """
        Block 2:
        - run_rea_deontic_stage4_from_saved_stage3()  # consumes reviewed stage3_output
        - run_vector_embedding_and_search(...)
        - run_reranker()
        """
        return {
            "rea_deontic_stage4": self._run_step(
                "REA deontic stage4 (slot extraction)",
                True,
                self.run_rea_deontic_stage4_from_saved_stage3,
            ),
            "vector_embedding": self._run_step(
                "vector embedding + dense retrieval",
                True,
                lambda: self.run_vector_embedding_and_search(reg_main_slots=reg_main_slots),
            ),
            "reranker": self._run_step(
                "reranking retrieval candidates",
                True,
                self.run_reranker,
            ),
        }

    def run_block_graph_traversal(self, reg_graph_json: str | Path) -> dict[str, Any]:
        """
        Block 3:
        - run_graph_traversal(...)
        """
        return {
            "graph_traversal": self._run_step(
                "building graph context",
                True,
                lambda: self.run_graph_traversal(reg_graph_json=reg_graph_json),
            ),
        }

    def run_block_prompt_generation(
        self,
        reg_graph_json: str | Path,
        reg_main_slots: str | Path,
        use_graph_context: bool = True,
    ) -> dict[str, Any]:
        """
        Block 4A:
        - run_prompt_generation(...)
        """
        return {
            "generate_prompt": self._run_step(
                "generating prompt payloads",
                True,
                lambda: self.run_prompt_generation(
                    reg_graph_json=reg_graph_json,
                    reg_main_slots=reg_main_slots,
                    use_graph_context=use_graph_context,
                ),
            )
        }

    def run_block_send_and_readable(self) -> dict[str, Any]:
        """
        Block 4B:
        - run_send_prompt()
        - run_readable_llm_response()
        """
        return {
            "send_prompt": self._run_step(
                "sending prompts to LLM",
                True,
                self.run_send_prompt,
            ),
            "readable_llm_response": self._run_step(
                "formatting readable LLM responses",
                True,
                self.run_readable_llm_response,
            ),
        }

    def run_block_reasoning(
        self,
        reg_graph_json: str | Path,
        reg_main_slots: str | Path,
        use_graph_context: bool = True,
    ) -> dict[str, Any]:
        """
        Block 4:
        - if send_prompts=False: prompt generation only
        - if send_prompts=True: prompt generation + send prompt + readable response
        """
        out = self.run_block_prompt_generation(
            reg_graph_json=reg_graph_json,
            reg_main_slots=reg_main_slots,
            use_graph_context=use_graph_context,
        )
        if self.send_prompts:
            out.update(self.run_block_send_and_readable())
        return out

    def run_block_postprocessing(self, run_end_result_extractor: bool = True) -> dict[str, Any]:
        """
        Block 5 (tail postprocessing):
        - optional EndResultExtractor report creation
        """
        if not run_end_result_extractor:
            return {"end_result_extractor": {"status": "skipped"}}
        return {"end_result_extractor": self.run_end_result_extractor()}

    def run_rea_pipeline(self) -> dict[str, Any]:
        """
        Backward-compatible full REA run.
        """
        self._log("REA pipeline run started")
        pre_head: dict[str, Any]
        if self.use_rea_chunk_splitter:
            pre_head = self.run_block_rea_preprocessing_head(run_chunk_splitter=True)
        else:
            pre_head = {"rea_chunk_splitter": {"status": "skipped"}}
        reg_main_slots, reg_graph_json = self._resolve_reg_artifacts()
        steps = self._run_rea_steps(
                reg_main_slots=reg_main_slots,
                reg_graph_json=reg_graph_json,
            )
        post_tail: dict[str, Any]
        if self.send_prompts:
            post_tail = self.run_block_postprocessing(run_end_result_extractor=True)
        else:
            post_tail = {"end_result_extractor": {"status": "skipped", "reason": "send_prompts=False"}}
        self._log("REA pipeline run finished")
        return {"preprocessing_head": pre_head, "steps": steps, "postprocessing_tail": post_tail}

    def run(
        self,
        run_rea_chunk_splitter: bool = False,
        run_rea_requirements_extractor: bool = True,
        run_rea_deontic_stage_pipeline: bool = True,
        run_vector_embedding: bool = True,
        run_reranker: bool = True,
        run_prompt_generation: bool = True,
        run_send_prompt: bool = True,
        run_readable_llm_response: bool = True,
        run_end_result_extractor: bool = True,
    ) -> dict[str, Any]:
        """Run configurable REA steps and return global run summary."""
        self._log("REA pipeline run started")

        pre_head: dict[str, Any]
        if run_rea_chunk_splitter:
            pre_head = self.run_block_rea_preprocessing_head(run_chunk_splitter=True)
        else:
            pre_head = {"rea_chunk_splitter": {"status": "skipped"}}

        reg_main_slots, reg_graph_json = self._resolve_reg_artifacts()
        rea_summary: dict[str, Any] = {
            "preprocessing_head": pre_head,
            "steps": self._run_rea_steps(
                reg_main_slots=reg_main_slots,
                reg_graph_json=reg_graph_json,
                run_rea_requirements_extractor=run_rea_requirements_extractor,
                run_rea_deontic_stage_pipeline=run_rea_deontic_stage_pipeline,
                run_vector_embedding=run_vector_embedding,
                run_reranker=run_reranker,
                run_prompt_generation=run_prompt_generation,
                run_send_prompt=run_send_prompt,
                run_readable_llm_response=run_readable_llm_response,
            )
        }
        if run_end_result_extractor and self.send_prompts and run_send_prompt and run_readable_llm_response:
            rea_summary["postprocessing_tail"] = self.run_block_postprocessing(run_end_result_extractor=True)
        else:
            rea_summary["postprocessing_tail"] = {
                "end_result_extractor": {"status": "skipped", "reason": "sending/readable disabled or send_prompts=False"}
            }

        result = {
            "project_root": str(self.project_root),
            "inputs": {
                "rea_input_name": self.rea_input_name,
                "reg_input_name": self.reg_input_name,
            },
            "runtime": {
                "send_prompts": self.send_prompts,
                "prompt_model_name": self.prompt_model_name,
                "cache_system_prompt": self.cache_system_prompt,
                "use_rea_chunk_splitter": self.use_rea_chunk_splitter,
                "rea_full_text_filename": self.rea_full_text_filename,
                "rea_chunk_output_folder_name": self.rea_chunk_output_folder_name,
                "rea_chunk_entries_per_file": self.rea_chunk_entries_per_file,
                "overwrite_output_folders_if_exist": self.overwrite_output_folders_if_exist,
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
            "rea_pipeline": rea_summary,
        }
        self._log("REA pipeline run finished")
        return result


def main() -> None:
    # -------------------------------
    # Edit config here (code-first)
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    rea_input_name = "rea_with_injections"      # folder under input/
    reg_input_name = "reg_for_injectiontest"    # folder under input/

    # retrieval knobs
    vector_k = 100   # dense retrieval top-k
    rerank_k = 100   # reranker top-k
    retrieve_k = 5   # prompt generation top-k

    # prompt/runtime knobs
    send_prompts = False
    prompt_model_name = "gpt-5.4"
    cache_system_prompt = True
    use_rea_chunk_splitter = False
    rea_full_text_filename = "rea_full_text.txt"
    rea_chunk_output_folder_name = "chunked_texts_generated"
    rea_chunk_entries_per_file = 3

    # keep True unless you want to skip a step
    run_block_rea_preprocessing_head = use_rea_chunk_splitter
    run_block_rea_preprocessing = True
    run_block_retrieval = True
    run_block_graph_traversal = True
    run_block_prompt_generation = True
    # send/readable block should typically follow send_prompts setting
    run_block_send_and_readable = send_prompts
    run_block_postprocessing_tail = send_prompts

    runner = InjectionAutoPipeline(
        project_root=project_root,
        rea_input_name=rea_input_name,
        reg_input_name=reg_input_name,
        vector_k=vector_k,
        rerank_k=rerank_k,
        retrieve_k=retrieve_k,
        send_prompts=send_prompts,
        prompt_model_name=prompt_model_name,
        cache_system_prompt=cache_system_prompt,
        use_rea_chunk_splitter=use_rea_chunk_splitter,
        rea_full_text_filename=rea_full_text_filename,
        rea_chunk_output_folder_name=rea_chunk_output_folder_name,
        rea_chunk_entries_per_file=rea_chunk_entries_per_file,
    )

    reg_main_slots = runner.reg_main_slots_path
    reg_graph_json = runner.reg_graph_json_path

    if run_block_rea_preprocessing_head:
        block0 = runner.run_block_rea_preprocessing_head(run_chunk_splitter=True)
    else:
        block0 = {"status": "skipped"}

    if run_block_rea_preprocessing:
        block1 = runner.run_block_rea_preprocessing()
    else:
        block1 = {"status": "skipped"}

    if run_block_retrieval:
        block2 = runner.run_block_retrieval(reg_main_slots=reg_main_slots)
    else:
        block2 = {"status": "skipped"}

    if run_block_graph_traversal:
        block3 = runner.run_block_graph_traversal(
            reg_graph_json=reg_graph_json,
        )
    else:
        block3 = {"status": "skipped"}

    if run_block_prompt_generation:
        block4a = runner.run_block_prompt_generation(
            reg_graph_json=reg_graph_json,
            reg_main_slots=reg_main_slots,
            use_graph_context=run_block_graph_traversal,
        )
    else:
        block4a = {"status": "skipped"}

    if run_block_send_and_readable:
        block4b = runner.run_block_send_and_readable()
    else:
        block4b = {"status": "skipped"}

    if run_block_postprocessing_tail and send_prompts:
        block5 = runner.run_block_postprocessing(run_end_result_extractor=True)
    else:
        block5 = {"status": "skipped"}

    print(json.dumps({"block0_preprocessing_head": block0}, indent=2, ensure_ascii=False))
    print(json.dumps({"block1_rea_preprocessing": block1}, indent=2, ensure_ascii=False))
    print(json.dumps({"block2_retrieval": block2}, indent=2, ensure_ascii=False))
    print(json.dumps({"block3_graph_traversal": block3}, indent=2, ensure_ascii=False))
    print(json.dumps({"block4a_prompt_generation": block4a}, indent=2, ensure_ascii=False))
    print(json.dumps({"block4b_send_and_readable": block4b}, indent=2, ensure_ascii=False))
    print(json.dumps({"block5_postprocessing_tail": block5}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
