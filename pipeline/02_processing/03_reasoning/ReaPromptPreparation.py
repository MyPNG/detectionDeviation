from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from typing import Any

from common.io_text import load_json, normalize_spaces
from .GeneratePrompt import DeviationPromptBuilder

GraphTraversal = importlib.import_module(
    "pipeline.02_processing.02_graph_traversal.GraphTraversal"
).GraphTraversal
_ranking_mod = importlib.import_module("pipeline.02_processing.01_retrieval.ranking")
get_sorted_top_matches_from_payload = _ranking_mod.get_sorted_top_matches_from_payload
sort_top_matches = _ranking_mod.sort_top_matches


class ReaPromptPreparation:
    """
    Pipeline for one reranked REA unit JSON (e.g., rea-01#4.json):
    - Step 2: extract top-k main REG matches
    - Step 3: collect graph context for those REGs via GraphTraversal
    - Step 4: generate LLM prompt payload
    """

    MAX_MAIN_REG_PER_PROMPT = 3

    def __init__(
        self,
        project_root: str | Path,
        reg_graph_json: str | Path | None = None,
        reg_slots_json: str | Path | None = None,
        rea_stage_root: str | Path | None = None,
    ):
        """Initialize reusable dependencies for step2-step4 prompt preparation."""
        self.project_root = Path(project_root).expanduser().resolve()
        self.reg_graph_json = (
            Path(reg_graph_json).expanduser().resolve()
            if reg_graph_json is not None
            else self.project_root / "intermediate_results" / "01_preprocessing" / "reg_prep" / "03_graphbuilder" / "requirementsgraphbuilder" / "reg_for_injectiontest" / "reg_for_injectiontest_requirements_graph.json"
        )
        self.reg_slots_json = (
            Path(reg_slots_json).expanduser().resolve()
            if reg_slots_json is not None
            else self.project_root / "intermediate_results" / "01_preprocessing" / "reg_prep" / "01_extracting" / "mainrequirementsslotfilter" / "reg_for_injectiontest" / "reg_for_injectiontest_requirements_slots_main.json"
        )
        self.rea_stage_root = (
            Path(rea_stage_root).expanduser().resolve()
            if rea_stage_root is not None
            else self.project_root / "intermediate_results" / "01_preprocessing" / "reaPrep" / "01_extracting" / "readeonticstagepipeline" / "rea_with_injections"
        )
        self.graph_traversal = GraphTraversal(self.reg_graph_json)

    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        """Collapse repeated whitespace into a single-space representation."""
        return normalize_spaces(value)

    @staticmethod
    def _reranked_file_sort_key(path: Path) -> tuple[str, int, int, str]:
        """Sort reranked REA files by chunk, REA id, then sub-id."""
        stem = path.stem.lower()
        match = re.match(r"rea-(\d+)(?:#(\d+))?$", stem)
        if match:
            rea_idx = int(match.group(1))
            sub_idx = int(match.group(2) or 0)
            return (path.parent.name.lower(), rea_idx, sub_idx, path.name.lower())
        return (path.parent.name.lower(), 10**9, 10**9, path.name.lower())

    def _load_json(self, path: Path) -> Any:
        """Read a JSON file and return parsed payload."""
        return load_json(path)

    @staticmethod
    def _write_prompt_payload_files(prompt_payload: dict[str, Any], output_json_path: Path) -> Path:
        """Write prompt payload as JSON and companion Markdown file."""
        output_json_path.write_text(json.dumps(prompt_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        output_md_path = output_json_path.with_suffix(".md")
        output_md_path.write_text(DeviationPromptBuilder._to_markdown(prompt_payload), encoding="utf-8")
        return output_md_path

    @staticmethod
    def _normalize_top_k(top_k: int) -> int:
        """Normalize user top-k to a positive integer."""
        return max(1, int(top_k))

    @classmethod
    def _split_main_constraints_batches(
        cls,
        graph_context: dict[str, Any],
        requested_top_k: int,
    ) -> list[list[dict[str, Any]]]:
        """
        Split selected main REG constraints into prompt-sized batches.
        Example: k=5, MAX_MAIN_REG_PER_PROMPT=3 -> [3, 2].
        """
        main_constraints = graph_context.get("main_constraints", []) if isinstance(graph_context, dict) else []
        if not isinstance(main_constraints, list):
            return []
        selected = [row for row in main_constraints[: max(1, requested_top_k)] if isinstance(row, dict)]
        if not selected:
            return []
        batch_size = cls.MAX_MAIN_REG_PER_PROMPT
        return [selected[idx: idx + batch_size] for idx in range(0, len(selected), batch_size)]

    @staticmethod
    def _sort_top_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort candidate REG matches by rerank rank then score."""
        return sort_top_matches(matches)

    def step2_extract_main_reg_matches(self, reranked_json_path: Path, top_k: int) -> dict[str, Any]:
        """Step 2: extract top-k main REG entries from one reranked REA artifact."""
        payload = self._load_json(reranked_json_path)
        sorted_matches = get_sorted_top_matches_from_payload(payload if isinstance(payload, dict) else {})
        selected = []
        for row in sorted_matches[: max(1, top_k)]:
            selected.append(
                {
                    "reg_id": self._normalize_spaces(row.get("ID", "")),
                    "clause": self._normalize_spaces(row.get("article", "")),
                    "text": self._normalize_spaces(row.get("text", "")),
                    "rerank_rank": row.get("rerank rank", None),
                    "rerank_score": row.get("rerank score", None),
                    "similarity_score": row.get("similarity score", None),
                }
            )

        return {
            "rea_sub_id": self._normalize_spaces(payload.get("id", "")),
            "rea_search_query": self._normalize_spaces(payload.get("search query", "")),
            "top_k": max(1, top_k),
            "main_reg_matches": selected,
        }

    def step3_collect_graph_context(
        self,
        reranked_json_path: Path,
        top_k: int,
        max_hop: int = 1,
    ) -> dict[str, Any]:
        """Step 3: expand graph context around selected main REG entries."""
        return self.graph_traversal.build_graph_context_for_reranked(
            reranked_json_path=reranked_json_path,
            top_k=max(1, top_k),
            max_hop=max(0, max_hop),
        )

    def step4_generate_prompt(
        self,
        reranked_json_path: Path,
        top_k: int,
        graph_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Step 4: build final prompt payload using REA + REG + graph context."""
        builder = DeviationPromptBuilder(
            project_root=self.project_root,
            reg_slots_json=self.reg_slots_json,
            rea_stage_root=self.rea_stage_root,
        )
        prompt_payload = builder.build_prompt_payload(
            reranked_json_path=reranked_json_path,
            top_k=max(1, top_k),
            graph_context=graph_context,
        )
        return prompt_payload

    def _build_empty_graph_context(self, reranked_json_path: Path) -> dict[str, Any]:
        """
        Build an explicit empty graph-context payload.
        Used when prompt generation is requested without graph traversal.
        """
        payload = self._load_json(reranked_json_path)
        rea_sub_id = self._normalize_spaces(payload.get("id", "")) if isinstance(payload, dict) else ""
        return {
            "rea_sub_id": rea_sub_id,
            "reranked_json": str(reranked_json_path),
            "top_k": 0,
            "max_hop": 0,
            "allowed_relations": [],
            "main_constraints": [],
            "visited_reg_ids": [],
        }

    def run_single(
        self,
        reranked_json_path: str | Path,
        output_dir: str | Path,
        top_k: int = 3,
        include_relations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run step2-step4 for one reranked REA JSON file."""
        reranked_path = Path(reranked_json_path).expanduser().resolve()
        output_root = Path(output_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        requested_top_k = self._normalize_top_k(top_k)

        step2 = self.step2_extract_main_reg_matches(reranked_path, top_k=requested_top_k)
        step3 = self.step3_collect_graph_context(
            reranked_json_path=reranked_path,
            top_k=requested_top_k,
            max_hop=1,
        )
        batches = self._split_main_constraints_batches(step3, requested_top_k=requested_top_k)
        if not batches:
            batches = [[]]

        step2_file = output_root / "step2_main_reg_matches.json"
        step3_file = output_root / "step3_graph_context.json"
        step4_files: list[str] = []
        step4_md_files: list[str] = []

        batch_count = len(batches)
        for batch_idx, batch_main_constraints in enumerate(batches, start=1):
            graph_context_batch = dict(step3)
            graph_context_batch["main_constraints"] = batch_main_constraints
            step4 = self.step4_generate_prompt(
                reranked_path,
                top_k=max(1, len(batch_main_constraints)),
                graph_context=graph_context_batch,
            )
            step4["batch_index"] = batch_idx
            step4["batch_count"] = batch_count

            if batch_count == 1:
                step4_file = output_root / "step4_prompt_payload.json"
            else:
                step4_file = output_root / f"step4_prompt_payload_{batch_idx:02d}.json"
            step4_md_file = self._write_prompt_payload_files(step4, step4_file)
            step4_files.append(str(step4_file))
            step4_md_files.append(str(step4_md_file))

        step2_file.write_text(json.dumps(step2, indent=2, ensure_ascii=False), encoding="utf-8")
        step3_file.write_text(json.dumps(step3, indent=2, ensure_ascii=False), encoding="utf-8")
        stale_step3_5 = output_root / "step3_5_rule_comparison_hints.json"
        if stale_step3_5.exists():
            stale_step3_5.unlink()

        return {
            "input_reranked_json": str(reranked_path),
            "top_k": requested_top_k,
            "output_dir": str(output_root),
            "step2_file": str(step2_file),
            "step3_file": str(step3_file),
            "step4_files": step4_files,
            "step4_md_files": step4_md_files,
            "step4_file": step4_files[0] if step4_files else "",
            "step4_md_file": step4_md_files[0] if step4_md_files else "",
            "batch_count": batch_count,
            "main_reg_ids": [row.get("id", "") for row in step3.get("main_constraints", []) if isinstance(row, dict)],
            "main_constraint_count": len(step3.get("main_constraints", [])),
        }

    def run_folder(
        self,
        reranked_root: str | Path,
        output_root: str | Path,
        top_k: int = 3,
        include_relations: list[str] | None = None,
    ) -> Path:
        """Run step2-step4 for every reranked REA file under a folder."""
        reranked_dir = Path(reranked_root).expanduser().resolve()
        out_root = Path(output_root).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        if not reranked_dir.exists() or not reranked_dir.is_dir():
            raise FileNotFoundError(f"reranked root not found or not a directory: {reranked_dir}")

        reranked_files = [
            path
            for path in reranked_dir.rglob("*.json")
            if path.is_file() and re.match(r"rea-\d+(?:#\d+)?\.json$", path.name, flags=re.IGNORECASE)
        ]
        reranked_files = sorted(reranked_files, key=self._reranked_file_sort_key)

        results: list[dict[str, Any]] = []
        for reranked_file in reranked_files:
            relative_parent = reranked_file.parent.relative_to(reranked_dir)
            single_out = out_root / relative_parent / reranked_file.stem
            try:
                result = self.run_single(
                    reranked_json_path=reranked_file,
                    output_dir=single_out,
                        top_k=self._normalize_top_k(top_k),
                        include_relations=include_relations,
                    )
                result["status"] = "ok"
                result["relative_path"] = str(reranked_file.relative_to(reranked_dir))
                results.append(result)
            except Exception as exc:
                results.append(
                    {
                        "status": "error",
                        "input_reranked_json": str(reranked_file),
                        "relative_path": str(reranked_file.relative_to(reranked_dir)),
                        "error": str(exc),
                    }
                )

        report_path = out_root / "step2_4_prompt_pipeline_report.json"
        payload = {
            "reranked_root": str(reranked_dir),
            "output_root": str(out_root),
            "top_k": self._normalize_top_k(top_k),
            "max_main_reg_per_prompt": self.MAX_MAIN_REG_PER_PROMPT,
            "file_count": len(reranked_files),
            "results": results,
        }
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return report_path

    def run_folder_without_graph_context(
        self,
        reranked_root: str | Path,
        output_root: str | Path,
        top_k: int = 3,
    ) -> Path:
        """
        Generate prompts from reranked JSONs with intentionally empty graph context.
        This mode is used when graph traversal block is disabled.
        """
        reranked_dir = Path(reranked_root).expanduser().resolve()
        out_root = Path(output_root).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        if not reranked_dir.exists() or not reranked_dir.is_dir():
            raise FileNotFoundError(f"reranked root not found or not a directory: {reranked_dir}")

        reranked_files = [
            path
            for path in reranked_dir.rglob("*.json")
            if path.is_file() and re.match(r"rea-\d+(?:#\d+)?\.json$", path.name, flags=re.IGNORECASE)
        ]
        reranked_files = sorted(reranked_files, key=self._reranked_file_sort_key)

        requested_top_k = self._normalize_top_k(top_k)
        results: list[dict[str, Any]] = []

        for reranked_file in reranked_files:
            relative_parent = reranked_file.parent.relative_to(reranked_dir)
            single_out = out_root / relative_parent / reranked_file.stem
            single_out.mkdir(parents=True, exist_ok=True)

            try:
                empty_graph_context = self._build_empty_graph_context(reranked_file)
                prompt_payload = self.step4_generate_prompt(
                    reranked_json_path=reranked_file,
                    top_k=requested_top_k,
                    # Pass empty dict so prompt builder uses reranked top matches
                    # for MAIN REG MATCHES while keeping graph context empty.
                    graph_context={},
                )
                prompt_payload["batch_index"] = 1
                prompt_payload["batch_count"] = 1
                prompt_payload["graph_context"] = empty_graph_context

                step4_file = single_out / "step4_prompt_payload.json"
                step4_md_file = self._write_prompt_payload_files(prompt_payload, step4_file)
                step3_file = single_out / "step3_graph_context.json"
                step3_file.write_text(
                    json.dumps(empty_graph_context, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

                stale_step3_5 = single_out / "step3_5_rule_comparison_hints.json"
                if stale_step3_5.exists():
                    stale_step3_5.unlink()

                results.append(
                    {
                        "status": "ok",
                        "input_reranked_json": str(reranked_file),
                        "step3_graph_context_json": str(step3_file),
                        "step4_prompt_payload_json": str(step4_file),
                        "step4_prompt_payload_md": str(step4_md_file),
                        "batch_count": 1,
                        "relative_path": str(reranked_file.relative_to(reranked_dir)),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "status": "error",
                        "input_reranked_json": str(reranked_file),
                        "relative_path": str(reranked_file.relative_to(reranked_dir)),
                        "error": str(exc),
                    }
                )

        report_path = out_root / "step2_4_prompt_pipeline_report.json"
        payload = {
            "reranked_root": str(reranked_dir),
            "output_root": str(out_root),
            "top_k": requested_top_k,
            "max_main_reg_per_prompt": self.MAX_MAIN_REG_PER_PROMPT,
            "graph_context_mode": "empty",
            "file_count": len(reranked_files),
            "results": results,
        }
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return report_path

    def run_folder_from_graph_context_root(
        self,
        graph_context_root: str | Path,
        output_root: str | Path,
        top_k: int = 3,
    ) -> Path:
        """
        Generate prompts from precomputed step3 graph context artifacts.
        This avoids rebuilding graph context and preserves exactly the edge
        set already decided by GraphTraversal output.
        """
        gc_root = Path(graph_context_root).expanduser().resolve()
        out_root = Path(output_root).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        if not gc_root.exists() or not gc_root.is_dir():
            raise FileNotFoundError(f"graph context root not found or not a directory: {gc_root}")

        step3_files = sorted(
            [p for p in gc_root.rglob("step3_graph_context.json") if p.is_file()],
            key=lambda p: str(p).lower(),
        )

        requested_top_k = self._normalize_top_k(top_k)
        results: list[dict[str, Any]] = []
        for step3_file in step3_files:
            relative_parent = step3_file.parent.relative_to(gc_root)
            single_out = out_root / relative_parent
            single_out.mkdir(parents=True, exist_ok=True)
            try:
                graph_context = self._load_json(step3_file)
                if not isinstance(graph_context, dict):
                    raise ValueError(f"Invalid step3 graph context payload: {step3_file}")

                reranked_raw = self._normalize_spaces(graph_context.get("reranked_json", ""))
                if not reranked_raw:
                    raise ValueError(f"Missing reranked_json in {step3_file}")
                reranked_path = Path(reranked_raw).expanduser().resolve()
                if not reranked_path.exists():
                    raise FileNotFoundError(f"reranked_json not found referenced by {step3_file}: {reranked_path}")

                batches = self._split_main_constraints_batches(
                    graph_context,
                    requested_top_k=requested_top_k,
                )
                if not batches:
                    batches = [[]]

                step4_files: list[str] = []
                step4_md_files: list[str] = []
                batch_count = len(batches)
                for batch_idx, batch_main_constraints in enumerate(batches, start=1):
                    graph_context_batch = dict(graph_context)
                    graph_context_batch["main_constraints"] = batch_main_constraints
                    prompt_payload = self.step4_generate_prompt(
                        reranked_json_path=reranked_path,
                        top_k=max(1, len(batch_main_constraints)),
                        graph_context=graph_context_batch,
                    )
                    prompt_payload["batch_index"] = batch_idx
                    prompt_payload["batch_count"] = batch_count

                    if batch_count == 1:
                        step4_file = single_out / "step4_prompt_payload.json"
                    else:
                        step4_file = single_out / f"step4_prompt_payload_{batch_idx:02d}.json"
                    step4_md_file = self._write_prompt_payload_files(prompt_payload, step4_file)
                    step4_files.append(str(step4_file))
                    step4_md_files.append(str(step4_md_file))

                stale_step3_5 = single_out / "step3_5_rule_comparison_hints.json"
                if stale_step3_5.exists():
                    stale_step3_5.unlink()

                results.append(
                    {
                        "status": "ok",
                        "step3_graph_context_json": str(step3_file),
                        "step4_prompt_payload_jsons": step4_files,
                        "step4_prompt_payload_mds": step4_md_files,
                        "step4_prompt_payload_json": step4_files[0] if step4_files else "",
                        "step4_prompt_payload_md": step4_md_files[0] if step4_md_files else "",
                        "batch_count": batch_count,
                        "relative_path": str(step3_file.relative_to(gc_root)),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "status": "error",
                        "step3_graph_context_json": str(step3_file),
                        "relative_path": str(step3_file.relative_to(gc_root)),
                        "error": str(exc),
                    }
                )

        report_path = out_root / "step2_4_prompt_pipeline_report.json"
        payload = {
            "graph_context_root": str(gc_root),
            "output_root": str(out_root),
            "top_k": requested_top_k,
            "max_main_reg_per_prompt": self.MAX_MAIN_REG_PER_PROMPT,
            "file_count": len(step3_files),
            "results": results,
        }
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return report_path


def main() -> None:
    # -------------------------------
    # Edit config here (code-first)
    # -------------------------------
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()

    # Choose mode: "single" or "folder"
    mode = "single"
    top_k = 3

    # Single mode inputs
    reranked_json = (
        project_root
        / "intermediate_results"
        / "02_processing"
        / "01_retrieval"
        / "reranker"
        / "artifact_01_rea_with_injections__reg_for_injectiontest_reranked"
        / "chunk1_deontic_stages"
        / "rea-01#4.json"
    )
    output_dir_single: Path | None = None

    # Folder mode inputs
    reranked_root = (
        project_root
        / "intermediate_results"
        / "02_processing"
        / "01_retrieval"
        / "reranker"
        / "artifact_01_rea_with_injections__reg_for_injectiontest_reranked"
    )
    output_root_folder: Path | None = None

    pipeline = ReaPromptPreparation(project_root=project_root)

    if str(mode).strip().lower() == "folder":
        reranked_root = Path(reranked_root).expanduser().resolve()
        if not reranked_root.exists():
            raise FileNotFoundError(f"Set reranked_root to an existing folder. Not found: {reranked_root}")
        output_root = (
            Path(output_root_folder).expanduser().resolve()
            if output_root_folder is not None
            else project_root / "intermediate_results" / "02_processing" / "03_reasoning" / "reapromptpreparation" / "single_rea_step2_4"
        )
        report = pipeline.run_folder(
            reranked_root=reranked_root,
            output_root=output_root,
            top_k=max(1, int(top_k)),
        )
        print(json.dumps({"saved_report": str(report)}, indent=2, ensure_ascii=False))
        return

    reranked_path = Path(reranked_json).expanduser().resolve()
    if not reranked_path.exists():
        raise FileNotFoundError(f"Set reranked_json to an existing file. Not found: {reranked_path}")
    default_output_dir = (
        project_root
        / "intermediate_results"
        / "02_processing"
        / "03_reasoning"
        / "reapromptpreparation"
        / "single_rea_step2_4"
        / reranked_path.stem
    )
    output_dir = (
        Path(output_dir_single).expanduser().resolve()
        if output_dir_single is not None
        else default_output_dir
    )

    result = pipeline.run_single(
        reranked_json_path=reranked_path,
        output_dir=output_dir,
        top_k=max(1, int(top_k)),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
