from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


class ExtractMainClauses:
    """
    Extract REG IDs used in one artifact_01 chunk and map them to main clauses
    (for example Art5(2)) using a GDPR metadata JSON file.
    """

    def __init__(self, reg_metadata_json_path: str | Path):
        self.reg_metadata_json_path = Path(reg_metadata_json_path).expanduser().resolve()

    @staticmethod
    def _normalize_reg_id(value: str) -> str:
        return value.strip().upper()

    @staticmethod
    def _build_clause(article: Any, paragraph: Any, point: Any = "") -> str:
        article_str = str(article).strip()
        paragraph_str = str(paragraph).strip()
        point_str = str(point).strip().strip("()")

        if not article_str:
            return ""
        if not paragraph_str:
            return f"Art{article_str}"
        if point_str:
            return f"Art{article_str}({paragraph_str})({point_str})"
        return f"Art{article_str}({paragraph_str})"

    def _load_reg_to_clause_map(self) -> dict[str, str]:
        payload = json.loads(self.reg_metadata_json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Metadata JSON must be a list of REG entries.")

        reg_to_clause: dict[str, str] = {}
        for row in payload:
            if not isinstance(row, dict):
                continue

            reg_id = self._normalize_reg_id(str(row.get("ID", "")))
            if not reg_id:
                continue

            article = row.get("Article", "")
            paragraph = row.get("Paragraph", "")
            point = row.get("Point", row.get("point", ""))
            clause = self._build_clause(article=article, paragraph=paragraph, point=point)
            reg_to_clause[reg_id] = clause

        return reg_to_clause

    @staticmethod
    def _extract_reg_ids_from_result_payload(payload: dict[str, Any], top_k: int | None = None) -> list[str]:
        """
        Extract REG IDs from one artifact_01 result file.
        Expected structure:
        {
          "top matches": [{"ID": "REG-001", ...}, ...]
        }
        """
        reg_ids: list[str] = []
        top_matches = payload.get("top matches", [])
        if not isinstance(top_matches, list):
            return reg_ids

        selected_matches = top_matches
        if top_k is not None:
            if top_k <= 0:
                return reg_ids
            selected_matches = top_matches[:top_k]

        for item in selected_matches:
            if not isinstance(item, dict):
                continue
            reg_id = str(item.get("ID", "")).strip().upper()
            if re.fullmatch(r"REG-\d+", reg_id):
                reg_ids.append(reg_id)
        return reg_ids

    def extract_from_chunk(self, chunk_dir: str | Path, top_k: int | None = None) -> list[dict[str, str]]:
        """
        Take one chunk folder (for example artifact_01/chunk_19),
        read all JSON files, and return rows with:
        - reg_id
        - clause
        top_k: number of top matches to consider per result file.
               If None, uses all matches in each file.
        """
        chunk_path = Path(chunk_dir).expanduser().resolve()
        if not chunk_path.exists() or not chunk_path.is_dir():
            raise FileNotFoundError(f"Chunk directory not found: {chunk_path}")

        reg_to_clause = self._load_reg_to_clause_map()
        collected_ids: set[str] = set()

        for json_file in sorted(chunk_path.glob("*.json")):
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            for reg_id in self._extract_reg_ids_from_result_payload(payload, top_k=top_k):
                collected_ids.add(reg_id)

        rows: list[dict[str, str]] = []
        for reg_id in sorted(collected_ids):
            rows.append(
                {
                    "reg_id": reg_id,
                    "clause": reg_to_clause.get(reg_id, ""),
                }
            )
        return rows

    def save_chunk_table(self, chunk_dir: str | Path, output_csv_path: str | Path, top_k: int | None = None) -> Path:
        rows = self.extract_from_chunk(chunk_dir=chunk_dir, top_k=top_k)
        output_path = Path(output_csv_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["reg_id", "clause"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        return output_path

    def process_all_chunks(self, artifact_01_root: str | Path, top_k: int | None = None) -> list[Path]:
        """
        Process every chunk directory in artifact_01 root and write:
        <artifact_01_root>/<chunk_name>/reg_main_clauses.csv
        top_k: number of top matches to consider per result file.
        """
        root = Path(artifact_01_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"artifact_01 root not found: {root}")

        saved_paths: list[Path] = []
        for chunk_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            output_csv = chunk_dir / "reg_main_clauses.csv"
            saved_paths.append(
                self.save_chunk_table(
                    chunk_dir=chunk_dir,
                    output_csv_path=output_csv,
                    top_k=top_k,
                )
            )
        return saved_paths


def main() -> None:
    metadata_json = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/reg_eu_ai_act/eu_ai_requirements.json"
    artifact_01_root = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_case3_v3_reranked"
    top_k = 5

    extractor = ExtractMainClauses(reg_metadata_json_path=metadata_json)
    saved_paths = extractor.process_all_chunks(
        artifact_01_root=artifact_01_root,
        top_k=top_k,
    )
    print(f"Processed {len(saved_paths)} chunk folder(s).")
    print(f"top_k per result file: {top_k}")
    for saved in saved_paths:
        print(f"Saved REG main clauses table: {saved}")


if __name__ == "__main__":
    main()
