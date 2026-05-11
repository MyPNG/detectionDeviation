from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from .GeneratePrompt import DeviationPromptBuilder
    from ..retrieval.GraphTraversal_v2 import GraphTraversal
except ImportError:  # pragma: no cover - fallback for direct script execution
    from GeneratePrompt import DeviationPromptBuilder
    from pipeline.retrieval.GraphTraversal_v2 import GraphTraversal


class SingleReaStep2To4Pipeline:
    """
    Pipeline for one reranked REA unit JSON (e.g., rea-01#4.json):
    - Step 2: extract top-k main REG matches
    - Step 3: collect graph context for those REGs via GraphTraversal_v2
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
        self.project_root = Path(project_root).expanduser().resolve()
        self.reg_graph_json = (
            Path(reg_graph_json).expanduser().resolve()
            if reg_graph_json is not None
            else self.project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_graph.json"
        )
        self.reg_slots_json = (
            Path(reg_slots_json).expanduser().resolve()
            if reg_slots_json is not None
            else self.project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_slots_main.json"
        )
        self.rea_stage_root = (
            Path(rea_stage_root).expanduser().resolve()
            if rea_stage_root is not None
            else self.project_root / "intermediate_results" / "rea_case3_injections_deontic_stages"
        )
        self.graph_traversal = GraphTraversal(self.reg_graph_json)

    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _reranked_file_sort_key(path: Path) -> tuple[str, int, int, str]:
        stem = path.stem.lower()
        match = re.match(r"rea-(\d+)(?:#(\d+))?$", stem)
        if match:
            rea_idx = int(match.group(1))
            sub_idx = int(match.group(2) or 0)
            return (path.parent.name.lower(), rea_idx, sub_idx, path.name.lower())
        return (path.parent.name.lower(), 10**9, 10**9, path.name.lower())

    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_prompt_payload_files(prompt_payload: dict[str, Any], output_json_path: Path) -> Path:
        output_json_path.write_text(json.dumps(prompt_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        output_md_path = output_json_path.with_suffix(".md")
        output_md_path.write_text(DeviationPromptBuilder._to_markdown(prompt_payload), encoding="utf-8")
        return output_md_path

    @classmethod
    def _limit_prompt_top_k(cls, top_k: int) -> int:
        return min(max(1, int(top_k)), cls.MAX_MAIN_REG_PER_PROMPT)

    @staticmethod
    def _sort_top_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def _key(row: dict[str, Any]) -> tuple[int, float]:
            rank_raw = row.get("rerank rank", "")
            try:
                rank = int(rank_raw)
            except Exception:
                rank = 10**9
            score_raw = row.get("rerank score", row.get("similarity score", 0.0))
            try:
                score = float(score_raw)
            except Exception:
                score = 0.0
            return rank, -score

        return sorted(matches, key=_key)

    def step2_extract_main_reg_matches(self, reranked_json_path: Path, top_k: int) -> dict[str, Any]:
        payload = self._load_json(reranked_json_path)
        matches = payload.get("top matches", [])
        if not isinstance(matches, list):
            matches = []

        sorted_matches = self._sort_top_matches([row for row in matches if isinstance(row, dict)])
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

    def run_single(
        self,
        reranked_json_path: str | Path,
        output_dir: str | Path,
        top_k: int = 3,
        include_relations: list[str] | None = None,
    ) -> dict[str, Any]:
        reranked_path = Path(reranked_json_path).expanduser().resolve()
        output_root = Path(output_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        prompt_top_k = self._limit_prompt_top_k(top_k)

        step2 = self.step2_extract_main_reg_matches(reranked_path, top_k=prompt_top_k)
        step3 = self.step3_collect_graph_context(
            reranked_json_path=reranked_path,
            top_k=prompt_top_k,
            max_hop=1,
        )
        step4 = self.step4_generate_prompt(reranked_path, top_k=prompt_top_k, graph_context=step3)

        step2_file = output_root / "step2_main_reg_matches.json"
        step3_file = output_root / "step3_graph_context.json"
        step4_file = output_root / "step4_prompt_payload.json"
        step2_file.write_text(json.dumps(step2, indent=2, ensure_ascii=False), encoding="utf-8")
        step3_file.write_text(json.dumps(step3, indent=2, ensure_ascii=False), encoding="utf-8")
        step4_md_file = self._write_prompt_payload_files(step4, step4_file)
        stale_step3_5 = output_root / "step3_5_rule_comparison_hints.json"
        if stale_step3_5.exists():
            stale_step3_5.unlink()

        return {
            "input_reranked_json": str(reranked_path),
            "top_k": prompt_top_k,
            "output_dir": str(output_root),
            "step2_file": str(step2_file),
            "step3_file": str(step3_file),
            "step4_file": str(step4_file),
            "step4_md_file": str(step4_md_file),
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
                    top_k=max(1, top_k),
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
            "top_k": self._limit_prompt_top_k(top_k),
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
        set already decided by GraphTraversal_v2 output.
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

        prompt_top_k = self._limit_prompt_top_k(top_k)
        results: list[dict[str, Any]] = []
        for step3_file in step3_files:
            relative_parent = step3_file.parent.relative_to(gc_root)
            single_out = out_root / relative_parent
            single_out.mkdir(parents=True, exist_ok=True)
            step4_file = single_out / "step4_prompt_payload.json"
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

                prompt_payload = self.step4_generate_prompt(
                    reranked_json_path=reranked_path,
                    top_k=prompt_top_k,
                    graph_context=graph_context,
                )
                step4_md_file = self._write_prompt_payload_files(prompt_payload, step4_file)
                stale_step3_5 = single_out / "step3_5_rule_comparison_hints.json"
                if stale_step3_5.exists():
                    stale_step3_5.unlink()

                results.append(
                    {
                        "status": "ok",
                        "step3_graph_context_json": str(step3_file),
                        "step4_prompt_payload_json": str(step4_file),
                        "step4_prompt_payload_md": str(step4_md_file),
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
            "top_k": prompt_top_k,
            "file_count": len(step3_files),
            "results": results,
        }
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run step2-step4 pipeline for one REA reranked JSON or a folder.")
    parser.add_argument("reranked_json", nargs="?", default="", help="Path to one reranked JSON, e.g. rea-01#4.json")
    parser.add_argument(
        "--reranked-root",
        default="",
        help="Optional root folder containing reranked REA json files (rea-*.json).",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Top-k REG matches to keep")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Output folder. Single mode: .../<rea_id>. Folder mode: root folder for all outputs.",
    )
    args = parser.parse_args()

    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    pipeline = SingleReaStep2To4Pipeline(project_root=project_root)
    if args.reranked_root:
        reranked_root = Path(args.reranked_root).expanduser().resolve()
        output_root = (
            Path(args.output_dir).expanduser().resolve()
            if args.output_dir
            else project_root / "intermediate_outputs" / "single_rea_step2_4"
        )
        report = pipeline.run_folder(
            reranked_root=reranked_root,
            output_root=output_root,
            top_k=max(1, args.top_k),
        )
        print(json.dumps({"saved_report": str(report)}, indent=2, ensure_ascii=False))
        return

    if not args.reranked_json:
        raise SystemExit("Provide either reranked_json or --reranked-root.")

    reranked_path = Path(args.reranked_json).expanduser().resolve()
    default_output_dir = project_root / "intermediate_outputs" / "single_rea_step2_4" / reranked_path.stem
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir

    result = pipeline.run_single(reranked_json_path=reranked_path, output_dir=output_dir, top_k=max(1, args.top_k))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
