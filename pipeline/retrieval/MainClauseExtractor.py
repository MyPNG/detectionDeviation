from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class MainClauseExtractor:
    """
    Extract main REG clauses from reranked retrieval outputs.
    For each REA JSON file, takes top-k entries from `top matches`.
    """

    @staticmethod
    def _extract_top_k_ids_from_file(file_path: Path, k: int) -> list[dict[str, str]]:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return []

        top_matches = payload.get("top matches", [])
        if not isinstance(top_matches, list):
            return []

        rows: list[dict[str, str]] = []
        for item in top_matches[:k]:
            if not isinstance(item, dict):
                continue
            reg_id = str(item.get("ID", "") or item.get("reg_id", "")).strip()
            clause = str(item.get("article", "") or item.get("clause", "")).strip()
            if not reg_id:
                continue
            rows.append({"reg_id": reg_id, "clause": clause})
        return rows

    def extract_main_clauses_for_chunk(
        self,
        chunk_dir: str | Path,
        k: int = 3,
        output_csv_name: str = "reg_main_clauses.csv",
    ) -> dict[str, Any]:
        if k <= 0:
            raise ValueError("k must be > 0")

        chunk_path = Path(chunk_dir).expanduser().resolve()
        if not chunk_path.exists() or not chunk_path.is_dir():
            raise FileNotFoundError(f"Chunk directory not found: {chunk_path}")

        seen_reg_ids: set[str] = set()
        selected_rows: list[dict[str, str]] = []
        json_files = sorted(
            file_path
            for file_path in chunk_path.glob("*.json")
            if file_path.name.lower() != "reg_main_clauses.json"
        )

        for file_path in json_files:
            for row in self._extract_top_k_ids_from_file(file_path=file_path, k=k):
                reg_id = row["reg_id"]
                if reg_id in seen_reg_ids:
                    continue
                seen_reg_ids.add(reg_id)
                selected_rows.append(row)

        output_csv = chunk_path / output_csv_name
        with output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["reg_id", "clause"])
            writer.writeheader()
            writer.writerows(selected_rows)

        return {
            "chunk_dir": str(chunk_path),
            "k": k,
            "source_json_files": len(json_files),
            "selected_main_clauses": len(selected_rows),
            "output_csv": str(output_csv),
        }

    def extract_main_clauses_for_artifact(
        self,
        reranked_artifact_root_dir: str | Path,
        k: int = 3,
        output_csv_name: str = "reg_main_clauses.csv",
    ) -> dict[str, Any]:
        if k <= 0:
            raise ValueError("k must be > 0")

        root = Path(reranked_artifact_root_dir).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Reranked artifact root not found: {root}")

        summaries: list[dict[str, Any]] = []
        chunk_dirs = sorted(path for path in root.iterdir() if path.is_dir())
        for chunk_dir in chunk_dirs:
            summary = self.extract_main_clauses_for_chunk(
                chunk_dir=chunk_dir,
                k=k,
                output_csv_name=output_csv_name,
            )
            summary["chunk"] = chunk_dir.name
            summaries.append(summary)

        return {
            "reranked_artifact_root": str(root),
            "chunk_count": len(summaries),
            "k": k,
            "chunks": summaries,
        }


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    reranked_artifact = project_root / "intermediate_outputs" / "artifact_01_reranked"
    extractor = MainClauseExtractor()
    result = extractor.extract_main_clauses_for_artifact(
        reranked_artifact_root_dir=reranked_artifact,
        k=3,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

