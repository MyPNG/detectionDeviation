from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from pipeline.retrieval.MainClauseExtractor import MainClauseExtractor
except ModuleNotFoundError:
    # Allow direct script execution without package install.
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from pipeline.retrieval.MainClauseExtractor import MainClauseExtractor


class RerankerCutoffTuner:
    """
    Tune reranker cutoff (top-k per REA file) on a dev set (goldstandard chunks).
    The tuned cutoff is then usable to generate cleaner reg_main_clauses.csv files.
    """

    def __init__(self, gold_root: str | Path, reranked_artifact_root: str | Path):
        self.gold_root = Path(gold_root).expanduser().resolve()
        self.reranked_artifact_root = Path(reranked_artifact_root).expanduser().resolve()

    @staticmethod
    def _normalize_chunk_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.strip().lower())

    @staticmethod
    def _chunk_sort_key(name: str) -> tuple[int, int, str]:
        lowered = name.strip().lower()
        match = re.search(r"chunk\D*(\d+)", lowered)
        if match:
            return (0, int(match.group(1)), lowered)
        return (1, 10**9, lowered)

    @staticmethod
    def _safe_div(n: float, d: float) -> float:
        return float(n / d) if d else 0.0

    @staticmethod
    def _find_gold_output_json(chunk_dir: Path) -> Path | None:
        preferred = chunk_dir / "output.json"
        if preferred.exists():
            return preferred
        typo = chunk_dir / "ouput.json"
        if typo.exists():
            return typo
        candidates = sorted(chunk_dir.glob("*.json"))
        return candidates[0] if candidates else None

    @staticmethod
    def _load_gold_reg_ids(path: Path) -> set[str]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return set()
        out: set[str] = set()
        for row in payload:
            if not isinstance(row, dict):
                continue
            reg_id = str(row.get("reg_id", "")).strip()
            if reg_id:
                out.add(reg_id)
        return out

    @staticmethod
    def _load_top_k_reg_ids_from_chunk(chunk_dir: Path, k: int) -> set[str]:
        """
        Build retrieved REG ID set from reranked REA JSON files:
        - take top-k from each file's `top matches`
        - union + deduplicate by REG ID
        """
        out: set[str] = set()
        for file_path in sorted(chunk_dir.glob("*.json")):
            if file_path.name == "reg_main_clauses.json":
                continue
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            top_matches = payload.get("top matches", [])
            if not isinstance(top_matches, list):
                continue
            for row in top_matches[:k]:
                if not isinstance(row, dict):
                    continue
                reg_id = str(row.get("ID", "") or row.get("reg_id", "")).strip()
                if reg_id:
                    out.add(reg_id)
        return out

    @classmethod
    def _score_sets(cls, gold_ids: set[str], retrieved_ids: set[str]) -> dict[str, Any]:
        tp_ids = sorted(gold_ids & retrieved_ids)
        fn_ids = sorted(gold_ids - retrieved_ids)
        fp_ids = sorted(retrieved_ids - gold_ids)
        tp = len(tp_ids)
        fn = len(fn_ids)
        fp = len(fp_ids)
        precision = cls._safe_div(tp, tp + fp)
        recall = cls._safe_div(tp, tp + fn)
        f1 = cls._safe_div(2 * precision * recall, precision + recall) if (precision + recall) else 0.0
        return {
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "tp_ids": tp_ids,
            "fn_ids": fn_ids,
            "fp_ids": fp_ids,
        }

    def evaluate_top_k(self, top_k: int) -> dict[str, Any]:
        if top_k <= 0:
            raise ValueError("top_k must be > 0")
        if not self.gold_root.exists() or not self.gold_root.is_dir():
            raise FileNotFoundError(f"Gold root not found: {self.gold_root}")
        if not self.reranked_artifact_root.exists() or not self.reranked_artifact_root.is_dir():
            raise FileNotFoundError(f"Reranked artifact root not found: {self.reranked_artifact_root}")

        reranked_by_norm: dict[str, Path] = {}
        for chunk_dir in sorted(path for path in self.reranked_artifact_root.iterdir() if path.is_dir()):
            reranked_by_norm[self._normalize_chunk_name(chunk_dir.name)] = chunk_dir

        chunk_reports: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        total_tp = total_fn = total_fp = 0

        gold_chunks = sorted(
            (path for path in self.gold_root.iterdir() if path.is_dir()),
            key=lambda p: self._chunk_sort_key(p.name),
        )
        for gold_chunk in gold_chunks:
            norm = self._normalize_chunk_name(gold_chunk.name)
            reranked_chunk = reranked_by_norm.get(norm)
            if reranked_chunk is None:
                skipped.append({"chunk": gold_chunk.name, "reason": "matching reranked chunk not found"})
                continue

            gold_file = self._find_gold_output_json(gold_chunk)
            if gold_file is None:
                skipped.append({"chunk": gold_chunk.name, "reason": "gold output json missing"})
                continue

            gold_ids = self._load_gold_reg_ids(gold_file)
            retrieved_ids = self._load_top_k_reg_ids_from_chunk(reranked_chunk, top_k)
            scores = self._score_sets(gold_ids, retrieved_ids)

            total_tp += int(scores["tp"])
            total_fn += int(scores["fn"])
            total_fp += int(scores["fp"])
            chunk_reports.append(
                {
                    "chunk": gold_chunk.name,
                    "gold_file": str(gold_file),
                    "reranked_chunk_dir": str(reranked_chunk),
                    "top_k": top_k,
                    "metrics": {
                        "tp": scores["tp"],
                        "fn": scores["fn"],
                        "fp": scores["fp"],
                        "precision": scores["precision"],
                        "recall": scores["recall"],
                        "f1": scores["f1"],
                    },
                    "missed_reg_ids": scores["fn_ids"],
                    "false_positive_reg_ids": scores["fp_ids"],
                }
            )

        overall_precision = self._safe_div(total_tp, total_tp + total_fp)
        overall_recall = self._safe_div(total_tp, total_tp + total_fn)
        overall_f1 = (
            self._safe_div(2 * overall_precision * overall_recall, overall_precision + overall_recall)
            if (overall_precision + overall_recall)
            else 0.0
        )

        return {
            "top_k": top_k,
            "gold_root": str(self.gold_root),
            "reranked_artifact_root": str(self.reranked_artifact_root),
            "evaluated_chunks": len(chunk_reports),
            "skipped_chunks": len(skipped),
            "overall_metrics": {
                "tp": total_tp,
                "fn": total_fn,
                "fp": total_fp,
                "precision": round(overall_precision, 6),
                "recall": round(overall_recall, 6),
                "f1": round(overall_f1, 6),
            },
            "chunks": chunk_reports,
            "skipped": skipped,
        }

    def tune_top_k(
        self,
        min_k: int = 1,
        max_k: int = 20,
        objective: str = "f1",
    ) -> dict[str, Any]:
        if min_k <= 0 or max_k <= 0:
            raise ValueError("min_k and max_k must be > 0")
        if min_k > max_k:
            raise ValueError("min_k must be <= max_k")
        if objective not in {"f1", "precision", "recall"}:
            raise ValueError("objective must be one of: f1, precision, recall")

        sweep: list[dict[str, Any]] = []
        best_report: dict[str, Any] | None = None
        best_key: tuple[float, float, float] | None = None

        for k in range(min_k, max_k + 1):
            report = self.evaluate_top_k(k)
            metrics = report.get("overall_metrics", {})
            score = float(metrics.get(objective, 0.0))
            # Tie-breakers:
            # 1) higher objective
            # 2) higher recall
            # 3) higher precision
            candidate_key = (score, float(metrics.get("recall", 0.0)), float(metrics.get("precision", 0.0)))

            sweep.append(
                {
                    "top_k": k,
                    "precision": float(metrics.get("precision", 0.0)),
                    "recall": float(metrics.get("recall", 0.0)),
                    "f1": float(metrics.get("f1", 0.0)),
                    "tp": int(metrics.get("tp", 0)),
                    "fn": int(metrics.get("fn", 0)),
                    "fp": int(metrics.get("fp", 0)),
                }
            )

            if best_key is None or candidate_key > best_key:
                best_key = candidate_key
                best_report = report

        assert best_report is not None
        return {
            "objective": objective,
            "range": {"min_k": min_k, "max_k": max_k},
            "best_top_k": int(best_report["top_k"]),
            "best_overall_metrics": best_report["overall_metrics"],
            "sweep": sweep,
            "best_report": best_report,
        }

    def apply_best_top_k_to_main_clauses(
        self,
        best_top_k: int,
        output_csv_name: str = "reg_main_clauses.csv",
    ) -> dict[str, Any]:
        """
        Use the tuned best_top_k to regenerate per-chunk reg_main_clauses.csv
        from reranked artifact files.
        """
        extractor = MainClauseExtractor()
        return extractor.extract_main_clauses_for_artifact(
            reranked_artifact_root_dir=self.reranked_artifact_root,
            k=best_top_k,
            output_csv_name=output_csv_name,
        )

    def run_tuning_pipeline(
        self,
        min_k: int,
        max_k: int,
        objective: str,
        output_json: str | Path,
        apply_best: bool = False,
        output_csv_name: str = "reg_main_clauses.csv",
    ) -> dict[str, Any]:
        """
        High-level method for IDE usage:
        1) tune top-k
        2) optionally apply best k to regenerate reg_main_clauses.csv
        3) save report JSON
        """
        tuning_report = self.tune_top_k(min_k=min_k, max_k=max_k, objective=objective)

        if apply_best:
            best_k = int(tuning_report["best_top_k"])
            applied = self.apply_best_top_k_to_main_clauses(
                best_top_k=best_k,
                output_csv_name=output_csv_name,
            )
            tuning_report["applied_best_top_k"] = applied

        saved = self.save_json(tuning_report, output_json)
        tuning_report["saved_report"] = str(saved)
        return tuning_report

    @staticmethod
    def save_json(payload: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def main() -> None:
    gold_root = "/Users/my/Documents/projects/detectionDeviation/goldstandard"
    reranked_artifact_root = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_reranked_100"
    min_k = 1
    max_k = 20
    objective = "f1"  # "f1" | "precision" | "recall"
    apply_best = True
    output_json = "/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/with_reranker/reranker_cutoff_tuning_reranked100.json"

    tuner = RerankerCutoffTuner(gold_root=gold_root, reranked_artifact_root=reranked_artifact_root)
    tuning_report = tuner.run_tuning_pipeline(
        min_k=min_k,
        max_k=max_k,
        objective=objective,
        output_json=output_json,
        apply_best=apply_best,
        output_csv_name="reg_main_clauses.csv",
    )

    print(f"Saved tuning report: {tuning_report['saved_report']}")
    print(f"Best top_k ({objective}): {tuning_report['best_top_k']}")
    print(json.dumps(tuning_report["best_overall_metrics"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
