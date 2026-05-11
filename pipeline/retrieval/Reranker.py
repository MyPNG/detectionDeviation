from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


class Reranker:
    """
    Isaacus Kanon 2 Reranker wrapper for retrieval post-processing.
    Input candidates are expected in the current project format:
    {
      "id": "REA-XX",
      "search query": "...",
      "top matches": [
        {"ID": "REG-001", "embedding text": "...", ...},
        ...
      ]
    }
    """

    def __init__(
        self,
        model_name: str = "kanon-2-reranker",
        api_key_env: str = "ISAACUS_API_KEY",
    ):
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.api_key = self._load_api_key()
        self.client = self._create_client()

    def _load_api_key(self) -> str:
        api_key = (os.getenv(self.api_key_env) or "").strip()
        if not api_key:
            raise ValueError(f"{self.api_key_env} is not set in environment.")
        return api_key

    def _create_client(self):
        try:
            from isaacus import Isaacus
        except ImportError as exc:
            raise ImportError(
                "isaacus SDK is not installed. Install with: "
                ".venv/bin/python -m pip install isaacus"
            ) from exc
        return Isaacus(api_key=self.api_key)

    @staticmethod
    def _safe_text(value: Any) -> str:
        text = str(value)
        text = re.sub(r"\[\s*missing_subject\s*\]", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmissing_subject\b", " ", text, flags=re.IGNORECASE)
        return " ".join(text.split()).strip()

    @classmethod
    def _sanitize_match_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(row)
        for key in ("text", "Text", "embedding text", "embedding test", "actor", "object", "condition", "manner"):
            if key in cleaned and cleaned[key] is not None:
                cleaned[key] = cls._safe_text(cleaned[key])
        return cleaned

    @staticmethod
    def _candidate_text(candidate: dict[str, Any]) -> str:
        # Prefer original regulation text for reranking; fallback to embedding string if needed.
        return Reranker._safe_text(
            candidate.get("text", "")
            or candidate.get("Text", "")
            or candidate.get("embedding text", "")
            or candidate.get("embedding test", "")
        )

    @staticmethod
    def _query_text(payload: dict[str, Any]) -> str:
        # Use the natural REA clause first; structured query is only a fallback.
        return Reranker._safe_text(
            payload.get("search query", "")
            or payload.get("embedding query", "")
            or payload.get("query", "")
        )

    @staticmethod
    def _read_result_index_score(result_item: Any) -> tuple[int | None, float | None]:
        """
        Supports both dict-style and object-style SDK result items.
        """
        if isinstance(result_item, dict):
            idx = result_item.get("index")
            score = result_item.get("score")
            if score is None:
                score = result_item.get("relevance_score")
            return (idx if isinstance(idx, int) else None, float(score) if score is not None else None)

        idx = getattr(result_item, "index", None)
        score = getattr(result_item, "score", None)
        if score is None:
            score = getattr(result_item, "relevance_score", None)
        return (idx if isinstance(idx, int) else None, float(score) if score is not None else None)

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_n: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Rerank a list of candidate REG rows using Isaacus Kanon 2 Reranker.
        Returns candidates sorted by rerank relevance score, with:
          - rerank score
          - rerank rank
        """
        if top_n <= 0:
            raise ValueError("top_n must be > 0")
        if not candidates:
            return []

        query_text = self._safe_text(query)
        texts = [self._candidate_text(row) for row in candidates]
        safe_top_n = min(top_n, len(texts))

        reranking = self.client.rerankings.create(
            model=self.model_name,
            query=query_text,
            texts=texts,
            top_n=safe_top_n,
        )
        results = getattr(reranking, "results", None)
        if results is None and isinstance(reranking, dict):
            results = reranking.get("results", [])
        if not isinstance(results, list):
            return []

        reranked: list[dict[str, Any]] = []
        for rank_idx, item in enumerate(results, start=1):
            index, score = self._read_result_index_score(item)
            if index is None:
                continue
            if index < 0 or index >= len(candidates):
                continue

            row = dict(candidates[index])
            row = self._sanitize_match_row(row)
            row["rerank score"] = score
            row["rerank rank"] = rank_idx
            reranked.append(row)

        return reranked

    def rerank_rea_file(
        self,
        input_json: str | Path,
        output_json: str | Path,
        top_n: int = 20,
        llm_max_items: int | None = None,
    ) -> Path:
        """
        Rerank one REA retrieval JSON file.
        """
        input_path = Path(input_json).expanduser().resolve()
        output_path = Path(output_json).expanduser().resolve()
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in {input_path}")

        query = self._query_text(payload)
        matches = payload.get("top matches", [])
        if not isinstance(matches, list):
            matches = []

        reranked_matches = self.rerank(query=query, candidates=matches, top_n=top_n)
        out_payload = dict(payload)
        if "search query" in out_payload:
            out_payload["search query"] = self._safe_text(out_payload.get("search query", ""))
        if "embedding query" in out_payload:
            out_payload["embedding query"] = self._safe_text(out_payload.get("embedding query", ""))
        out_payload["top matches"] = reranked_matches
        out_payload["rerank query"] = query
        out_payload["reranker"] = {
            "provider": "isaacus",
            "model": self.model_name,
            "top_n": min(top_n, len(matches)),
            "llm_max_items": llm_max_items,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def rerank_chunk_folder(
        self,
        input_chunk_dir: str | Path,
        output_chunk_dir: str | Path,
        top_n: int = 20,
        llm_max_items: int | None = None,
    ) -> dict[str, Any]:
        """
        Rerank all REA JSON files for one chunk folder.
        """
        in_dir = Path(input_chunk_dir).expanduser().resolve()
        out_dir = Path(output_chunk_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        written: list[str] = []
        for file_path in sorted(in_dir.glob("*.json")):
            out_path = out_dir / file_path.name
            saved = self.rerank_rea_file(
                file_path,
                out_path,
                top_n=top_n,
                llm_max_items=llm_max_items,
            )
            written.append(str(saved))

        return {
            "input_chunk_dir": str(in_dir),
            "output_chunk_dir": str(out_dir),
            "file_count": len(written),
            "files_written": written,
        }

    def rerank_artifact_root(
        self,
        input_artifact_01_dir: str | Path,
        output_artifact_dir: str | Path,
        top_n: int = 20,
        llm_max_items: int | None = None,
    ) -> dict[str, Any]:
        """
        Rerank all chunk folders under artifact_01-like structure.
        """
        input_root = Path(input_artifact_01_dir).expanduser().resolve()
        output_root = Path(output_artifact_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)

        chunk_summaries: list[dict[str, Any]] = []
        for chunk_dir in sorted(path for path in input_root.iterdir() if path.is_dir()):
            summary = self.rerank_chunk_folder(
                input_chunk_dir=chunk_dir,
                output_chunk_dir=output_root / chunk_dir.name,
                top_n=top_n,
                llm_max_items=llm_max_items,
            )
            summary["chunk"] = chunk_dir.name
            chunk_summaries.append(summary)

        return {
            "input_root": str(input_root),
            "output_root": str(output_root),
            "chunk_count": len(chunk_summaries),
            "top_n": top_n,
            "llm_max_items": llm_max_items,
            "chunks": chunk_summaries,
        }


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    input_artifact = project_root / "intermediate_outputs" / "artifact_01_case3_v3"
    output_artifact = project_root / "intermediate_outputs" / "artifact_01_case3_v3_reranked"

    reranker = Reranker(
        model_name="kanon-2-reranker",
        api_key_env="ISAACUS_API_KEY",
    )
    result = reranker.rerank_artifact_root(
        input_artifact_01_dir=input_artifact,
        output_artifact_dir=output_artifact,
        top_n=100,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
