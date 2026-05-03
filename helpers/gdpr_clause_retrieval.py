from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gdpr_compliance.loader import GDPRLoader
from gdpr_compliance.vector_index import ClauseVectorIndex


def load_query_files(queries_path: Path) -> list[Path]:
    if queries_path.is_file():
        return [queries_path]
    if queries_path.is_dir():
        return sorted(path for path in queries_path.rglob("*") if path.is_file())
    return []


def _safe_stem(path: Path) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("_")
    return cleaned or "query"


def build_index(
    clauses_json: Path,
    index_dir: Path,
    backend: str,
    sentence_model: str,
    sentence_batch_size: int,
    openai_model: str,
    sentence_timeout_seconds: float,
    openai_timeout_seconds: float,
    reuse_existing_index: bool,
    boilerplate_phrases_file: Path | None,
    vector_top_k: int,
    bm25_top_k: int,
    vector_weight: float,
    bm25_weight: float,
    concept_overlap_weight: float,
) -> tuple[int, str]:
    clauses = GDPRLoader(clauses_json).load()
    index = ClauseVectorIndex(
        index_dir=index_dir,
        backend=backend,
        sentence_model=sentence_model,
        sentence_batch_size=sentence_batch_size,
        openai_model=openai_model,
        sentence_timeout_seconds=sentence_timeout_seconds,
        openai_timeout_seconds=openai_timeout_seconds,
        reuse_existing_index=reuse_existing_index,
        boilerplate_phrases_path=boilerplate_phrases_file,
        default_vector_top_k=vector_top_k,
        default_bm25_top_k=bm25_top_k,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        concept_overlap_weight=concept_overlap_weight,
    )
    index.build(clauses)
    return len(clauses), index.effective_backend


def query_index(
    clauses_json: Path,
    index_dir: Path,
    queries_path: Path,
    top_k: int,
    output_file: Path,
    backend: str,
    sentence_model: str,
    sentence_batch_size: int,
    openai_model: str,
    sentence_timeout_seconds: float,
    openai_timeout_seconds: float,
    boilerplate_phrases_file: Path | None,
    vector_top_k: int,
    bm25_top_k: int,
    vector_weight: float,
    bm25_weight: float,
    concept_overlap_weight: float,
    score_debug_dir: Path | None,
) -> tuple[int, int]:
    clauses = GDPRLoader(clauses_json).load()
    index = ClauseVectorIndex(
        index_dir=index_dir,
        backend=backend,
        sentence_model=sentence_model,
        sentence_batch_size=sentence_batch_size,
        openai_model=openai_model,
        sentence_timeout_seconds=sentence_timeout_seconds,
        openai_timeout_seconds=openai_timeout_seconds,
        reuse_existing_index=True,
        boilerplate_phrases_path=boilerplate_phrases_file,
        default_vector_top_k=vector_top_k,
        default_bm25_top_k=bm25_top_k,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        concept_overlap_weight=concept_overlap_weight,
    )
    index.build(clauses)

    files = load_query_files(queries_path)
    results: list[dict[str, Any]] = []
    debug_written = 0

    for query_idx, file_path in enumerate(files):
        query_text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not query_text:
            continue

        matches = index.search(
            query=query_text,
            top_k=top_k,
            vector_top_k=vector_top_k,
            bm25_top_k=bm25_top_k,
        )
        results.append(
            {
                "query_file": str(file_path.resolve()),
                "query_text": query_text,
                "top_matches": [
                    {
                        "id": match.clause.id,
                        "score": round(float(match.score), 6),
                        "text": match.clause.text,
                        "concept_overlap": round(float(match.concept_overlap), 6),
                        "vector_similarity": round(float(match.vector_similarity), 6),
                        "bm25_score": round(float(match.bm25_score), 6),
                        "source": match.source,
                        "clause": match.clause.to_dict(),
                    }
                    for match in matches
                ],
            }
        )

        if score_debug_dir is not None:
            score_debug_dir.mkdir(parents=True, exist_ok=True)
            debug_payload = index.get_last_search_debug()
            debug_payload["query_file"] = str(file_path.resolve())
            debug_payload["output_top_k"] = top_k
            debug_filename = f"{query_idx:03d}_{_safe_stem(file_path)}_score_debug.json"
            (score_debug_dir / debug_filename).write_text(
                json.dumps(debug_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            debug_written += 1

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    if score_debug_dir is not None:
        print(f"Saved score-debug files: {debug_written} in {score_debug_dir}")
    return len(files), len(results)


def build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Hybrid GDPR clause retrieval (vector + BM25 + score fusion)."
    )
    parser.add_argument(
        "--mode",
        choices=["run", "build", "query"],
        default="run",
        help="run=build+query, build=index only, query=query only",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "sentence", "openai", "tfidf"],
        default="auto",
        help="Vector embedding backend.",
    )
    parser.add_argument(
        "--clauses-json",
        type=Path,
        default=project_root / "gdpr_clause" / "gdpr_clauses.json",
        help="Path to GDPR clauses JSON.",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=project_root / "gdpr_clause" / "kg_vector_index",
        help="Directory for hybrid retrieval artifacts.",
    )
    parser.add_argument(
        "--queries-path",
        type=Path,
        default=project_root / "datasets" / "rea" / "test_data.txt",
        help="Path to policy text file or directory.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=project_root / "gdpr_clause" / "rea_top_matches.json",
        help="Path to save retrieval output JSON.",
    )
    parser.add_argument(
        "--score-debug-dir",
        type=Path,
        default=None,
        help="Optional directory to write per-query score breakdown JSON files.",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Final top-k clauses to return per query.")
    parser.add_argument("--vector-top-k", type=int, default=50, help="Candidate count from vector retrieval.")
    parser.add_argument("--bm25-top-k", type=int, default=50, help="Candidate count from BM25 retrieval.")
    parser.add_argument("--vector-weight", type=float, default=0.6, help="Fusion weight for vector similarity.")
    parser.add_argument("--bm25-weight", type=float, default=0.3, help="Fusion weight for BM25 score.")
    parser.add_argument(
        "--concept-overlap-weight",
        type=float,
        default=0.1,
        help="Fusion weight for concept overlap score.",
    )
    parser.add_argument(
        "--boilerplate-phrases-file",
        type=Path,
        default=project_root / "datasets" / "reg" / "boilerplate_phrases" / "legal_filler_phrases.txt",
        help="TXT file with one filler phrase per line for normalization.",
    )
    parser.add_argument(
        "--sentence-model",
        type=str,
        default=os.getenv("SENTENCE_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        help="Sentence-transformers model name/path.",
    )
    parser.add_argument("--sentence-batch-size", type=int, default=32, help="Batch size for sentence embedding.")
    parser.add_argument("--openai-model", type=str, default="text-embedding-3-small")
    parser.add_argument("--sentence-timeout-seconds", type=float, default=5.0)
    parser.add_argument("--openai-timeout-seconds", type=float, default=10.0)
    parser.add_argument(
        "--no-reuse-existing-index",
        action="store_true",
        help="Force rebuilding vector artifacts even if cache matches.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be greater than 0")
    if args.vector_top_k <= 0:
        raise ValueError("--vector-top-k must be greater than 0")
    if args.bm25_top_k <= 0:
        raise ValueError("--bm25-top-k must be greater than 0")
    if args.sentence_batch_size <= 0:
        raise ValueError("--sentence-batch-size must be greater than 0")

    if args.mode in {"run", "build"}:
        clause_count, backend_used = build_index(
            clauses_json=args.clauses_json,
            index_dir=args.index_dir,
            backend=args.backend,
            sentence_model=args.sentence_model,
            sentence_batch_size=args.sentence_batch_size,
            openai_model=args.openai_model,
            sentence_timeout_seconds=args.sentence_timeout_seconds,
            openai_timeout_seconds=args.openai_timeout_seconds,
            reuse_existing_index=not args.no_reuse_existing_index,
            boilerplate_phrases_file=args.boilerplate_phrases_file,
            vector_top_k=args.vector_top_k,
            bm25_top_k=args.bm25_top_k,
            vector_weight=args.vector_weight,
            bm25_weight=args.bm25_weight,
            concept_overlap_weight=args.concept_overlap_weight,
        )
        print(f"Indexed clauses: {clause_count}")
        print(f"Backend used: {backend_used}")
        print(f"Index dir: {args.index_dir}")

    if args.mode in {"run", "query"}:
        discovered_files, queried_files = query_index(
            clauses_json=args.clauses_json,
            index_dir=args.index_dir,
            queries_path=args.queries_path,
            top_k=args.top_k,
            output_file=args.output_file,
            backend=args.backend,
            sentence_model=args.sentence_model,
            sentence_batch_size=args.sentence_batch_size,
            openai_model=args.openai_model,
            sentence_timeout_seconds=args.sentence_timeout_seconds,
            openai_timeout_seconds=args.openai_timeout_seconds,
            boilerplate_phrases_file=args.boilerplate_phrases_file,
            vector_top_k=args.vector_top_k,
            bm25_top_k=args.bm25_top_k,
            vector_weight=args.vector_weight,
            bm25_weight=args.bm25_weight,
            concept_overlap_weight=args.concept_overlap_weight,
            score_debug_dir=args.score_debug_dir,
        )
        print(f"Discovered query files: {discovered_files}")
        print(f"Queried files with non-empty text: {queried_files}")
        print(f"Saved retrieval output: {args.output_file}")


if __name__ == "__main__":
    main()
