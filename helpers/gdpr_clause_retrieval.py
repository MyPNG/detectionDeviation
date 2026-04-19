from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import faiss
import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


def load_clauses(clauses_json: Path) -> list[dict[str, Any]]:
    data = json.loads(clauses_json.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in: {clauses_json}")
    return data


def load_query_files(queries_path: Path) -> list[Path]:
    if queries_path.is_file():
        return [queries_path]
    if queries_path.is_dir():
        return sorted(path for path in queries_path.rglob("*") if path.is_file())
    return []


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    output = vectors.astype(np.float32, copy=False)
    faiss.normalize_L2(output)
    return output


def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    index.add(vectors)
    return index


def build_sentence_embeddings(
    texts: list[str],
    model_name: str,
    batch_size: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)
    vectors = normalize_vectors(vectors)
    meta = {
        "model_name": model_name,
        "batch_size": batch_size,
    }
    return vectors, meta


def build_tfidf_embeddings(
    texts: list[str],
    svd_dim: int,
    max_word_features: int,
    max_char_features: int,
) -> tuple[np.ndarray, dict[str, Any], dict[str, Any]]:
    word_vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        analyzer="word",
        ngram_range=(1, 2),
        max_features=max_word_features,
        norm="l2",
        sublinear_tf=True,
    )
    char_vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=max_char_features,
        norm="l2",
        sublinear_tf=True,
    )

    word_matrix = word_vectorizer.fit_transform(texts)
    char_matrix = char_vectorizer.fit_transform(texts)
    combined_matrix = hstack([word_matrix, char_matrix], format="csr")

    max_components = min(combined_matrix.shape[0] - 1, combined_matrix.shape[1] - 1)
    if max_components <= 0:
        raise ValueError("Not enough data to build reduced TF-IDF embeddings.")

    effective_dim = min(svd_dim, max_components)
    svd = TruncatedSVD(n_components=effective_dim, random_state=42)
    vectors = svd.fit_transform(combined_matrix).astype(np.float32)
    vectors = normalize_vectors(vectors)

    artifacts = {
        "word_vectorizer": word_vectorizer,
        "char_vectorizer": char_vectorizer,
        "svd": svd,
    }
    meta = {
        "svd_dim": int(vectors.shape[1]),
        "max_word_features": max_word_features,
        "max_char_features": max_char_features,
    }
    return vectors, artifacts, meta


def save_index_artifacts(
    index_dir: Path,
    index: faiss.Index,
    clauses_json: Path,
    clauses: list[dict[str, Any]],
    backend: str,
    backend_meta: dict[str, Any],
    backend_artifacts: dict[str, Any] | None,
) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(index_dir / "gdpr_clause.index.faiss"))
    if backend_artifacts:
        for name, artifact in backend_artifacts.items():
            joblib.dump(artifact, index_dir / f"{name}.joblib")

    metadata = {
        "index_type": "faiss.IndexFlatIP",
        "backend": backend,
        "clauses_json": str(clauses_json.resolve()),
        "clause_count": len(clauses),
        "backend_meta": backend_meta,
    }
    (index_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")


def build_index(
    clauses_json: Path,
    index_dir: Path,
    backend: str,
    sentence_model: str,
    sentence_batch_size: int,
    svd_dim: int,
    max_word_features: int,
    max_char_features: int,
) -> tuple[int, int, str]:
    clauses = load_clauses(clauses_json)
    texts = [str(clause.get("text", "")) for clause in clauses]

    used_backend = backend
    vectors: np.ndarray
    artifacts: dict[str, Any] | None = None
    backend_meta: dict[str, Any]

    if backend in {"sentence", "auto"}:
        try:
            vectors, backend_meta = build_sentence_embeddings(
                texts=texts,
                model_name=sentence_model,
                batch_size=sentence_batch_size,
            )
            used_backend = "sentence"
        except Exception:
            if backend == "sentence":
                raise
            vectors, artifacts, backend_meta = build_tfidf_embeddings(
                texts=texts,
                svd_dim=svd_dim,
                max_word_features=max_word_features,
                max_char_features=max_char_features,
            )
            used_backend = "tfidf"
    else:
        vectors, artifacts, backend_meta = build_tfidf_embeddings(
            texts=texts,
            svd_dim=svd_dim,
            max_word_features=max_word_features,
            max_char_features=max_char_features,
        )
        used_backend = "tfidf"

    index = build_faiss_index(vectors)
    save_index_artifacts(
        index_dir=index_dir,
        index=index,
        clauses_json=clauses_json,
        clauses=clauses,
        backend=used_backend,
        backend_meta=backend_meta,
        backend_artifacts=artifacts,
    )

    return len(clauses), int(vectors.shape[1]), used_backend


def load_index(index_dir: Path) -> tuple[faiss.Index, dict[str, Any]]:
    index = faiss.read_index(str(index_dir / "gdpr_clause.index.faiss"))
    metadata = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
    return index, metadata


def encode_queries_with_backend(
    backend: str,
    backend_meta: dict[str, Any],
    index_dir: Path,
    query_texts: list[str],
) -> np.ndarray:
    if backend == "sentence":
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(backend_meta["model_name"])
        vectors = model.encode(
            query_texts,
            batch_size=int(backend_meta.get("batch_size", 32)),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)
        return normalize_vectors(vectors)

    word_vectorizer: TfidfVectorizer = joblib.load(index_dir / "word_vectorizer.joblib")
    char_vectorizer: TfidfVectorizer = joblib.load(index_dir / "char_vectorizer.joblib")
    svd: TruncatedSVD = joblib.load(index_dir / "svd.joblib")

    word_matrix = word_vectorizer.transform(query_texts)
    char_matrix = char_vectorizer.transform(query_texts)
    combined_matrix = hstack([word_matrix, char_matrix], format="csr")
    vectors = svd.transform(combined_matrix).astype(np.float32)
    return normalize_vectors(vectors)


def query_index(
    index_dir: Path,
    queries_path: Path,
    top_k: int,
    output_file: Path,
) -> tuple[int, int]:
    index, metadata = load_index(index_dir)
    backend = metadata["backend"]
    backend_meta = metadata["backend_meta"]
    clauses = load_clauses(Path(metadata["clauses_json"]))

    files = load_query_files(queries_path)
    results: list[dict[str, Any]] = []

    for file_path in files:
        query_text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not query_text:
            continue

        query_vector = encode_queries_with_backend(
            backend=backend,
            backend_meta=backend_meta,
            index_dir=index_dir,
            query_texts=[query_text],
        )
        distances, indices = index.search(query_vector, k=top_k)

        matches: list[dict[str, Any]] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            matches.append(
                {
                    "score": round(float(score), 6),
                    "clause": clauses[int(idx)],
                }
            )

        results.append(
            {
                "query_file": str(file_path.resolve()),
                "query_text": query_text,
                "top_matches": matches,
            }
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(files), len(results)


def build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Embed GDPR clauses and retrieve top-k clauses for policy text files using FAISS."
    )
    parser.add_argument(
        "--mode",
        choices=["run", "build", "query"],
        default="run",
        help="run=build+query, build=index only, query=query only",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "sentence", "tfidf"],
        default="auto",
        help="Embedding backend.",
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
        default=project_root / "gdpr_clause" / "index",
        help="Directory for FAISS and embedding artifacts.",
    )
    parser.add_argument(
        "--queries-path",
        type=Path,
        default=project_root / "datasets" / "rea" / "test_data",
        help="Path to policy text file or directory.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=project_root / "gdpr_clause" / "rea_top_matches.json",
        help="Path to save retrieval output JSON.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Top-k clauses to return for each query file.",
    )
    parser.add_argument(
        "--sentence-model",
        type=str,
        default=os.getenv("SENTENCE_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        help="Sentence-transformers model name/path.",
    )
    parser.add_argument(
        "--sentence-batch-size",
        type=int,
        default=32,
        help="Batch size for sentence embedding.",
    )
    parser.add_argument(
        "--svd-dim",
        type=int,
        default=256,
        help="Target embedding size for TF-IDF backend.",
    )
    parser.add_argument(
        "--max-word-features",
        type=int,
        default=50000,
        help="Max word n-gram features for TF-IDF backend.",
    )
    parser.add_argument(
        "--max-char-features",
        type=int,
        default=50000,
        help="Max char n-gram features for TF-IDF backend.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be greater than 0")
    if args.sentence_batch_size <= 0:
        raise ValueError("--sentence-batch-size must be greater than 0")
    if args.svd_dim <= 0:
        raise ValueError("--svd-dim must be greater than 0")
    if args.max_word_features <= 0:
        raise ValueError("--max-word-features must be greater than 0")
    if args.max_char_features <= 0:
        raise ValueError("--max-char-features must be greater than 0")

    clause_count = 0
    embedding_dim = 0
    used_backend = ""

    if args.mode in {"run", "build"}:
        clause_count, embedding_dim, used_backend = build_index(
            clauses_json=args.clauses_json,
            index_dir=args.index_dir,
            backend=args.backend,
            sentence_model=args.sentence_model,
            sentence_batch_size=args.sentence_batch_size,
            svd_dim=args.svd_dim,
            max_word_features=args.max_word_features,
            max_char_features=args.max_char_features,
        )
        print(f"Indexed clauses: {clause_count}")
        print(f"Embedding dimension: {embedding_dim}")
        print(f"Backend used: {used_backend}")
        print(f"Index dir: {args.index_dir}")

    if args.mode in {"run", "query"}:
        discovered_files, queried_files = query_index(
            index_dir=args.index_dir,
            queries_path=args.queries_path,
            top_k=args.top_k,
            output_file=args.output_file,
        )
        print(f"Discovered query files: {discovered_files}")
        print(f"Queried files with non-empty text: {queried_files}")
        print(f"Saved retrieval output: {args.output_file}")


if __name__ == "__main__":
    main()
