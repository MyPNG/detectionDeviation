from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


ARTICLE_NUMBER_PATTERN = re.compile(r"(?:Article|Art\.?)\s*(\d+)", flags=re.IGNORECASE)


class RetrievalConfusionMatrix:
    """
    Minimal retrieval confusion evaluator focused on merged evaluation flow:
    1) Build merged deduplicated main clauses CSV from chunk-level CSVs.
    2) Evaluate article-level relevance.
    3) Evaluate clause-level relevance.
    """

    def __init__(self, gold_root: str | Path, system_root: str | Path):
        self.gold_root = Path(gold_root).expanduser().resolve()
        self.system_root = Path(system_root).expanduser().resolve()

    @staticmethod
    def _chunk_sort_key(path: Path) -> tuple[int, int, str]:
        name = path.name.strip().lower()
        match = re.search(r"chunk\D*(\d+)", name)
        if match:
            return (0, int(match.group(1)), name)
        return (1, 10**9, name)

    @staticmethod
    def _safe_div(n: float, d: float) -> float:
        return float(n / d) if d else 0.0

    @staticmethod
    def _article_key_from_text(value: str) -> str | None:
        text = str(value).strip()
        if not text:
            return None
        match = ARTICLE_NUMBER_PATTERN.search(text)
        if not match:
            return None
        return f"Article {int(match.group(1))}"

    @staticmethod
    def _normalize_clause_key(value: str) -> str:
        text = str(value).strip().lower()
        if not text:
            return ""
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"^article", "art", text, flags=re.IGNORECASE)
        text = re.sub(r"^art\.?", "art", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _find_system_main_clauses_csv(chunk_dir: Path) -> Path | None:
        preferred = chunk_dir / "reg_main_clauses.csv"
        if preferred.exists():
            return preferred
        candidates = sorted(chunk_dir.glob("*.csv"))
        return candidates[0] if candidates else None

    @staticmethod
    def _load_reg_to_article_map(reg_metadata_json: Path) -> dict[str, str]:
        mapping: dict[str, str] = {}
        if not reg_metadata_json.exists():
            return mapping

        payload = json.loads(reg_metadata_json.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return mapping

        for row in payload:
            if not isinstance(row, dict):
                continue
            reg_id = str(row.get("ID", "")).strip().upper()
            article_raw = str(row.get("Article", "")).strip()
            if not reg_id or not article_raw:
                continue
            key = RetrievalConfusionMatrix._article_key_from_text(article_raw)
            if key:
                mapping[reg_id] = key
        return mapping

    @staticmethod
    def _load_article_gold_json(path: Path) -> tuple[set[str], set[str]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object JSON for article gold data: {path}")

        relevant: set[str] = set()
        non_relevant: set[str] = set()

        relevant_rows = payload.get("relevant_articles", [])
        if isinstance(relevant_rows, list):
            for row in relevant_rows:
                if not isinstance(row, dict):
                    continue
                key = RetrievalConfusionMatrix._article_key_from_text(str(row.get("article", "")))
                if key:
                    relevant.add(key)

        non_relevant_rows = payload.get("non_relevant_articles", [])
        if isinstance(non_relevant_rows, list):
            for row in non_relevant_rows:
                if not isinstance(row, dict):
                    continue
                key = RetrievalConfusionMatrix._article_key_from_text(str(row.get("article", "")))
                if key:
                    non_relevant.add(key)

        return relevant, non_relevant

    @staticmethod
    def _load_clause_gold_json(path: Path) -> tuple[set[str], set[str]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object JSON for clause gold data: {path}")

        relevant: set[str] = set()
        non_relevant: set[str] = set()

        relevant_rows = payload.get("relevant_clauses", [])
        if isinstance(relevant_rows, list):
            for row in relevant_rows:
                clause_value = str(row.get("clause", "")).strip() if isinstance(row, dict) else str(row).strip()
                key = RetrievalConfusionMatrix._normalize_clause_key(clause_value)
                if key:
                    relevant.add(key)

        non_relevant_rows = payload.get("non_relevant_clauses", [])
        if isinstance(non_relevant_rows, list):
            for row in non_relevant_rows:
                clause_value = str(row.get("clause", "")).strip() if isinstance(row, dict) else str(row).strip()
                key = RetrievalConfusionMatrix._normalize_clause_key(clause_value)
                if key:
                    non_relevant.add(key)

        return relevant, non_relevant

    @staticmethod
    def _load_retrieved_articles_from_merged_csv(merged_csv: Path) -> set[str]:
        retrieved: set[str] = set()
        with merged_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                article = str(row.get("article", "")).strip()
                clause = str(row.get("clause", "")).strip()
                key = RetrievalConfusionMatrix._article_key_from_text(article) if article else None
                if key is None and clause:
                    key = RetrievalConfusionMatrix._article_key_from_text(clause)
                if key:
                    retrieved.add(key)
        return retrieved

    @staticmethod
    def _load_retrieved_clauses_from_merged_csv(merged_csv: Path) -> set[str]:
        retrieved: set[str] = set()
        with merged_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                clause = str(row.get("clause", "")).strip()
                key = RetrievalConfusionMatrix._normalize_clause_key(clause)
                if key:
                    retrieved.add(key)
        return retrieved

    @staticmethod
    def _build_result_payload(
        mode: str,
        expected_file: Path,
        actual_file: Path,
        relevant: set[str],
        non_relevant: set[str],
        retrieved: set[str],
        entity_label: str,
    ) -> dict[str, Any]:
        tp_ids = sorted(relevant & retrieved)
        fn_ids = sorted(relevant - retrieved)
        fp_ids = sorted(retrieved - relevant)
        tn_ids = sorted(non_relevant - retrieved) if non_relevant else []
        unknown = sorted(retrieved - (relevant | non_relevant)) if non_relevant else []

        tp = len(tp_ids)
        fn = len(fn_ids)
        fp = len(fp_ids)
        tn = len(tn_ids)

        precision = RetrievalConfusionMatrix._safe_div(tp, tp + fp)
        recall = RetrievalConfusionMatrix._safe_div(tp, tp + fn)
        f1 = (
            RetrievalConfusionMatrix._safe_div(2 * precision * recall, precision + recall)
            if (precision + recall)
            else 0.0
        )

        return {
            "mode": mode,
            "expected_file": str(expected_file),
            "actual_file": str(actual_file),
            f"relevant_{entity_label}": sorted(relevant),
            f"non_relevant_{entity_label}": sorted(non_relevant),
            f"retrieved_{entity_label}": sorted(retrieved),
            f"true_positive_{entity_label}": tp_ids,
            f"false_negative_{entity_label}": fn_ids,
            f"false_positive_{entity_label}": fp_ids,
            f"true_negative_{entity_label}": tn_ids,
            f"unknown_retrieved_{entity_label}": unknown,
            "confusion_table": [
                {
                    "row_label": "Relevant (Gold Standard)",
                    "retrieved": tp,
                    "not_retrieved": fn,
                    "retrieved_label": "True Positives",
                    "not_retrieved_label": "False Negatives",
                },
                {
                    "row_label": "Irrelevant (Gold Standard)",
                    "retrieved": fp,
                    "not_retrieved": tn,
                    "retrieved_label": "False Positives",
                    "not_retrieved_label": "True Negatives",
                },
            ],
            "metrics": {
                "tp": tp,
                "fn": fn,
                "fp": fp,
                "tn": tn,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "f1": round(f1, 6),
            },
        }

    def build_deduplicated_merged_main_clauses_csv(
        self,
        output_csv: str | Path,
        reg_metadata_json: str | Path | None = None,
    ) -> Path:
        output_path = Path(output_csv).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        reg_to_article: dict[str, str] = {}
        if reg_metadata_json is not None:
            reg_to_article = self._load_reg_to_article_map(Path(reg_metadata_json).expanduser().resolve())

        merged_rows: list[dict[str, str]] = []
        seen_keys: set[str] = set()
        for chunk_dir in sorted((path for path in self.system_root.iterdir() if path.is_dir()), key=self._chunk_sort_key):
            csv_path = self._find_system_main_clauses_csv(chunk_dir)
            if csv_path is None:
                continue

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if not isinstance(row, dict):
                        continue
                    reg_id = str(row.get("reg_id", "")).strip().upper()
                    clause = str(row.get("clause", "")).strip()
                    article_key = self._article_key_from_text(clause) if clause else None
                    if article_key is None and reg_id:
                        article_key = reg_to_article.get(reg_id)

                    dedup_key = reg_id if reg_id else (article_key or "")
                    if not dedup_key or dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)

                    merged_rows.append(
                        {
                            "reg_id": reg_id,
                            "clause": clause,
                            "article": article_key or "",
                        }
                    )

        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["reg_id", "clause", "article"])
            writer.writeheader()
            writer.writerows(merged_rows)

        return output_path

    def analyze_against_relevant_non_relevant_articles(
        self,
        article_gold_json: str | Path,
        merged_main_clauses_csv: str | Path,
    ) -> dict[str, Any]:
        gold_path = Path(article_gold_json).expanduser().resolve()
        merged_csv_path = Path(merged_main_clauses_csv).expanduser().resolve()
        relevant, non_relevant = self._load_article_gold_json(gold_path)
        retrieved = self._load_retrieved_articles_from_merged_csv(merged_csv_path)
        return self._build_result_payload(
            mode="article_relevance",
            expected_file=gold_path,
            actual_file=merged_csv_path,
            relevant=relevant,
            non_relevant=non_relevant,
            retrieved=retrieved,
            entity_label="articles",
        )

    def analyze_against_relevant_clauses(
        self,
        clause_gold_json: str | Path,
        merged_main_clauses_csv: str | Path,
    ) -> dict[str, Any]:
        gold_path = Path(clause_gold_json).expanduser().resolve()
        merged_csv_path = Path(merged_main_clauses_csv).expanduser().resolve()
        relevant, non_relevant = self._load_clause_gold_json(gold_path)
        retrieved = self._load_retrieved_clauses_from_merged_csv(merged_csv_path)
        return self._build_result_payload(
            mode="clause_relevance",
            expected_file=gold_path,
            actual_file=merged_csv_path,
            relevant=relevant,
            non_relevant=non_relevant,
            retrieved=retrieved,
            entity_label="clauses",
        )

    def save_article_relevance_json(
        self,
        article_gold_json: str | Path,
        merged_main_clauses_csv: str | Path,
        output_json: str | Path,
    ) -> Path:
        result = self.analyze_against_relevant_non_relevant_articles(
            article_gold_json=article_gold_json,
            merged_main_clauses_csv=merged_main_clauses_csv,
        )
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def save_article_relevance_markdown(
        self,
        article_gold_json: str | Path,
        merged_main_clauses_csv: str | Path,
        output_md: str | Path,
    ) -> Path:
        result = self.analyze_against_relevant_non_relevant_articles(
            article_gold_json=article_gold_json,
            merged_main_clauses_csv=merged_main_clauses_csv,
        )
        output_path = Path(output_md).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_relevance_markdown(
            output_path=output_path,
            title="# Retrieval Confusion Matrix (Article Relevance)",
            result=result,
            missed_key="false_negative_articles",
            fp_key="false_positive_articles",
            unknown_key="unknown_retrieved_articles",
            missed_title="## Missed Relevant Articles",
            fp_title="## False Positive Articles",
            unknown_title="## Retrieved Articles Not Listed In Gold JSON",
        )
        return output_path

    def save_clause_relevance_json(
        self,
        clause_gold_json: str | Path,
        merged_main_clauses_csv: str | Path,
        output_json: str | Path,
    ) -> Path:
        result = self.analyze_against_relevant_clauses(
            clause_gold_json=clause_gold_json,
            merged_main_clauses_csv=merged_main_clauses_csv,
        )
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def save_clause_relevance_markdown(
        self,
        clause_gold_json: str | Path,
        merged_main_clauses_csv: str | Path,
        output_md: str | Path,
    ) -> Path:
        result = self.analyze_against_relevant_clauses(
            clause_gold_json=clause_gold_json,
            merged_main_clauses_csv=merged_main_clauses_csv,
        )
        output_path = Path(output_md).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_relevance_markdown(
            output_path=output_path,
            title="# Retrieval Confusion Matrix (Clause Relevance)",
            result=result,
            missed_key="false_negative_clauses",
            fp_key="false_positive_clauses",
            unknown_key="unknown_retrieved_clauses",
            missed_title="## Missed Relevant Clauses",
            fp_title="## False Positive Clauses",
            unknown_title="## Retrieved Clauses Not Listed In Gold JSON",
        )
        return output_path

    @staticmethod
    def _write_relevance_markdown(
        output_path: Path,
        title: str,
        result: dict[str, Any],
        missed_key: str,
        fp_key: str,
        unknown_key: str,
        missed_title: str,
        fp_title: str,
        unknown_title: str,
    ) -> None:
        lines: list[str] = [title, ""]
        lines.append(f"- Expected: `{result.get('expected_file', '')}`")
        lines.append(f"- Actual: `{result.get('actual_file', '')}`")
        lines.append("")
        metrics = result.get("metrics", {})
        lines.append(f"- Precision: {metrics.get('precision', 0.0)}")
        lines.append(f"- Recall: {metrics.get('recall', 0.0)}")
        lines.append(f"- F1: {metrics.get('f1', 0.0)}")
        lines.append("")
        lines.append("| | Retrieved (System found it) | Not Retrieved (System missed it) |")
        lines.append("|---|---:|---:|")
        for row in result.get("confusion_table", []):
            if not isinstance(row, dict):
                continue
            lines.append(
                f"| {row.get('row_label','')} | {row.get('retrieved',0)} ({row.get('retrieved_label','')}) | "
                f"{row.get('not_retrieved',0)} ({row.get('not_retrieved_label','')}) |"
            )
        lines.append("")

        lines.append(missed_title)
        lines.append("")
        missed = result.get(missed_key, [])
        lines.append(", ".join(missed) if isinstance(missed, list) and missed else "None")
        lines.append("")

        lines.append(fp_title)
        lines.append("")
        fps = result.get(fp_key, [])
        lines.append(", ".join(fps) if isinstance(fps, list) and fps else "None")
        lines.append("")

        lines.append(unknown_title)
        lines.append("")
        unknown = result.get(unknown_key, [])
        lines.append(", ".join(unknown) if isinstance(unknown, list) and unknown else "None")
        lines.append("")

        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def run_merged_article_and_clause_evaluation(
        self,
        article_gold_json: str | Path,
        clause_gold_json: str | Path,
        reg_metadata_json: str | Path,
        merged_csv: str | Path,
        article_json: str | Path,
        article_md: str | Path,
        clause_json: str | Path,
        clause_md: str | Path,
    ) -> dict[str, str]:
        """
        Convenience wrapper for merged retrieval evaluation.
        """
        merged_saved = self.build_deduplicated_merged_main_clauses_csv(
            output_csv=merged_csv,
            reg_metadata_json=reg_metadata_json,
        )

        saved_article_json = self.save_article_relevance_json(
            article_gold_json=article_gold_json,
            merged_main_clauses_csv=merged_saved,
            output_json=article_json,
        )
        saved_article_md = self.save_article_relevance_markdown(
            article_gold_json=article_gold_json,
            merged_main_clauses_csv=merged_saved,
            output_md=article_md,
        )

        saved_clause_json = self.save_clause_relevance_json(
            clause_gold_json=clause_gold_json,
            merged_main_clauses_csv=merged_saved,
            output_json=clause_json,
        )
        saved_clause_md = self.save_clause_relevance_markdown(
            clause_gold_json=clause_gold_json,
            merged_main_clauses_csv=merged_saved,
            output_md=clause_md,
        )

        return {
            "merged_csv": str(merged_saved),
            "article_json": str(saved_article_json),
            "article_md": str(saved_article_md),
            "clause_json": str(saved_clause_json),
            "clause_md": str(saved_clause_md),
        }


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    analyzer = RetrievalConfusionMatrix(
        gold_root=project_root / "goldstandard",
        system_root=project_root / "intermediate_outputs" / "artifact_01_case3_v3_reranked",
    )

    result = analyzer.run_merged_article_and_clause_evaluation(
        article_gold_json=project_root / "goldstandard" / "relevant_non_relevant_requirements_case3.json",
        clause_gold_json=project_root / "goldstandard" / "eu_ai_injections_relevant_clauses.json",
        reg_metadata_json=project_root / "intermediate_results" / "reg_eu_ai_act" / "eu_ai_requirements_with_additional_references.json",
        merged_csv=project_root / "evaluation" / "artifact3" / "case3_v3" / "merged_main_clauses_deduplicated.csv",
        article_json=project_root / "evaluation" / "artifact3" / "case3_v3" / "retrieval_confusion_matrix_articles.json",
        article_md=project_root / "evaluation" / "artifact3" / "case3_v3" / "retrieval_confusion_matrix_articles.md",
        clause_json=project_root / "evaluation" / "artifact3" / "case3_v3" / "retrieval_confusion_matrix_clauses.json",
        clause_md=project_root / "evaluation" / "artifact3" / "case3_v3" / "retrieval_confusion_matrix_clauses.md",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
