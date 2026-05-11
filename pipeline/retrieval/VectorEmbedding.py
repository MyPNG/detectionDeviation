from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer


@dataclass
class RegObject:
    reg_id: str
    article: str
    paragraph: str
    text: str
    references: list[str]

    @property
    def location(self) -> str:
        paragraph = self.paragraph.strip()
        return f"Art{self.article}({paragraph})" if paragraph else f"Art{self.article}"


class VectorSearch:
    """
    Build embeddings for GDPR REG objects and store them in a persistent ChromaDB collection.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        collection_name: str = "gdpr_requirements",
    ):
        self.model_name = model_name
        self.collection_name = collection_name
        self.model = self._load_model_with_retry()

    def _load_model_with_retry(self) -> SentenceTransformer:
        """
        Load SentenceTransformer model with explicit HF token and a single retry for transient hub client failures.
        """
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                if token:
                    return SentenceTransformer(self.model_name, token=token)
                return SentenceTransformer(self.model_name)
            except Exception as exc:
                last_error = exc
                # Known transient error after temporary network hiccups in hub client stack.
                if "client has been closed" not in str(exc).lower() and "nodename nor servname" not in str(exc).lower():
                    raise
                time.sleep(1.5)
        assert last_error is not None
        raise last_error

    @staticmethod
    def _normalize_spaces(value: str) -> str:
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _normalize_article(value: Any) -> str:
        article = str(value).strip()
        return article.replace("Art", "").strip() if article.lower().startswith("art") else article

    def _to_reg_object(self, item: dict[str, Any]) -> RegObject:
        references = item.get("references", [])
        if not isinstance(references, list):
            references = []
        return RegObject(
            reg_id=self._normalize_spaces(str(item.get("ID", ""))),
            article=self._normalize_article(item.get("Article", "")),
            paragraph=self._normalize_spaces(str(item.get("Paragraph", ""))),
            text=self._normalize_spaces(str(item.get("Text", ""))),
            references=[self._normalize_spaces(str(ref)) for ref in references if str(ref).strip()],
        )

    def load_reg_objects(self, input_json_path: str | Path) -> list[RegObject]:
        input_path = Path(input_json_path).expanduser().resolve()
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Input JSON must be a list of requirement objects.")

        reg_objects: list[RegObject] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            reg_obj = self._to_reg_object(item)
            if not reg_obj.reg_id or not reg_obj.text:
                continue
            reg_objects.append(reg_obj)
        return reg_objects

    @staticmethod
    def _build_embedding_text(reg_obj: RegObject) -> str:
        references = ", ".join(reg_obj.references) if reg_obj.references else ""
        return (
            f"REG-ID: {reg_obj.reg_id}\n"
            f"ARTICLE: {reg_obj.article}\n"
            f"PARAGRAPH: {reg_obj.paragraph}\n"
            f"LOCATION: {reg_obj.location}\n"
            f"REFERENCES: {references}\n"
            f"TEXT: {reg_obj.text}"
        )

    def _build_embedding_texts(self, reg_objects: list[RegObject]) -> list[str]:
        return [self._build_embedding_text(obj) for obj in reg_objects]

    def _get_chroma_collection(self, persist_dir: Path):
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "chromadb is not installed in this environment. Install it with: "
                ".venv/bin/python -m pip install chromadb"
            ) from exc

        client = chromadb.PersistentClient(path=str(persist_dir))
        collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return collection

    def embed_and_store(
        self,
        input_json_path: str | Path,
        chroma_persist_dir: str | Path,
        batch_size: int = 32,
    ) -> dict[str, Any]:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        reg_objects = self.load_reg_objects(input_json_path)
        if not reg_objects:
            raise ValueError("No valid REG objects found in input JSON.")

        embedding_texts = self._build_embedding_texts(reg_objects)
        vectors = self.model.encode(
            embedding_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        persist_dir = Path(chroma_persist_dir).expanduser().resolve()
        persist_dir.mkdir(parents=True, exist_ok=True)
        collection = self._get_chroma_collection(persist_dir)

        ids = [obj.reg_id for obj in reg_objects]
        metadatas = [
            {
                "reg_id": obj.reg_id,
                "article": obj.article,
                "paragraph": obj.paragraph,
                "location": obj.location,
                "references": ", ".join(obj.references),
            }
            for obj in reg_objects
        ]
        documents = [obj.text for obj in reg_objects]
        embeddings = [vector.astype(float).tolist() for vector in vectors]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

        return {
            "input_count": len(reg_objects),
            "collection_name": self.collection_name,
            "persist_dir": str(persist_dir),
            "model_name": self.model_name,
        }

    @staticmethod
    def _to_similarity_score(distance: float) -> float:
        # For cosine distance in Chroma, similarity is approximately 1 - distance.
        return float(1.0 - float(distance))

    def _load_rea_items(self, rea_json_path: str | Path) -> list[dict[str, str]]:
        input_path = Path(rea_json_path).expanduser().resolve()
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("REA input JSON must be a list.")

        items: list[dict[str, str]] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            rea_id = self._normalize_spaces(str(row.get("rea_id", "")))
            text = self._normalize_spaces(str(row.get("text", "")))
            if not rea_id or not text:
                continue
            items.append({"rea_id": rea_id, "text": text})
        return items

    def _search_single_query(
        self,
        query_text: str,
        collection,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        query_vector = self.model.encode(
            [query_text],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        result = collection.query(
            query_embeddings=[query_vector.astype(float).tolist()],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]

        matches: list[dict[str, Any]] = []
        for reg_id, doc_text, distance, metadata in zip(ids, documents, distances, metadatas):
            metadata = metadata if isinstance(metadata, dict) else {}
            location = self._normalize_spaces(str(metadata.get("location", "")))
            article_num = self._normalize_spaces(str(metadata.get("article", "")))
            paragraph_num = self._normalize_spaces(str(metadata.get("paragraph", "")))
            article_field = location
            if not article_field and article_num:
                article_field = f"Art{article_num}({paragraph_num})" if paragraph_num else f"Art{article_num}"
            matches.append(
                {
                    "ID": str(reg_id),
                    "article": article_field,
                    "embedding test": self._normalize_spaces(str(doc_text)),
                    "similarity score": round(self._to_similarity_score(float(distance)), 6),
                }
            )
        return matches

    def vector_search_for_rea_statements(
        self,
        rea_json_path: str | Path,
        chroma_persist_dir: str | Path,
        artifact_root_dir: str | Path,
        chunk_name: str = "chunk_1",
        top_k: int = 20,
    ) -> dict[str, Any]:
        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        persist_dir = Path(chroma_persist_dir).expanduser().resolve()
        collection = self._get_chroma_collection(persist_dir)
        rea_items = self._load_rea_items(rea_json_path)

        output_dir = Path(artifact_root_dir).expanduser().resolve() / chunk_name
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files: list[str] = []
        for item in rea_items:
            rea_id = item["rea_id"]
            query_text = item["text"]
            top_matches = self._search_single_query(
                query_text=query_text,
                collection=collection,
                top_k=top_k,
            )
            payload = {
                "id": rea_id,
                "search query": query_text,
                "top matches": top_matches,
            }
            output_path = output_dir / f"{rea_id.lower()}_top_{top_k}.json"
            output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            written_files.append(str(output_path))

        return {
            "rea_count": len(rea_items),
            "top_k": top_k,
            "output_dir": str(output_dir),
            "files_written": written_files,
        }

    @staticmethod
    def _chunk_name_from_requirements_file(file_path: Path) -> str:
        """
        Convert a file like `chunk1_requirements.json` -> `chunk1`.
        """
        stem = file_path.stem
        return re.sub(r"_requirements$", "", stem, flags=re.IGNORECASE)

    @staticmethod
    def _collect_rea_requirement_files(rea_json_root_path: str | Path) -> list[Path]:
        """
        If input is a file, return [file].
        If input is a folder, collect `*_requirements.json` files recursively.
        """
        root = Path(rea_json_root_path).expanduser().resolve()
        if root.is_file():
            return [root]
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"REA input path not found: {root}")

        files = sorted(root.rglob("*_requirements.json"))
        if files:
            return files
        return sorted(root.rglob("*.json"))

    def vector_search_for_rea_folder(
        self,
        rea_json_root_path: str | Path,
        chroma_persist_dir: str | Path,
        artifact_root_dir: str | Path,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """
        Folder mode:
        - input: folder containing chunk requirement files
        - output: artifact_root/<chunk_name>/<rea-id>.json
        """
        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        persist_dir = Path(chroma_persist_dir).expanduser().resolve()
        collection = self._get_chroma_collection(persist_dir)
        artifact_root = Path(artifact_root_dir).expanduser().resolve()
        artifact_root.mkdir(parents=True, exist_ok=True)

        rea_files = self._collect_rea_requirement_files(rea_json_root_path)
        written_files: list[str] = []
        chunk_summaries: list[dict[str, Any]] = []

        for rea_file in rea_files:
            chunk_name = self._chunk_name_from_requirements_file(rea_file)
            rea_items = self._load_rea_items(rea_file)
            output_dir = artifact_root / chunk_name
            output_dir.mkdir(parents=True, exist_ok=True)

            for item in rea_items:
                rea_id = item["rea_id"]
                query_text = item["text"]
                top_matches = self._search_single_query(
                    query_text=query_text,
                    collection=collection,
                    top_k=top_k,
                )
                payload = {
                    "id": rea_id,
                    "search query": query_text,
                    "top matches": top_matches,
                }
                output_path = output_dir / f"{rea_id.lower()}.json"
                output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                written_files.append(str(output_path))

            chunk_summaries.append(
                {
                    "input_file": str(rea_file),
                    "chunk_name": chunk_name,
                    "rea_count": len(rea_items),
                    "output_dir": str(output_dir),
                }
            )

        return {
            "chunk_count": len(chunk_summaries),
            "top_k": top_k,
            "artifact_root_dir": str(artifact_root),
            "chunks": chunk_summaries,
            "files_written": written_files,
        }


def main() -> None:
    input_json = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/reg_eu_ai_act/eu_ai_requirements.json"
    rea_json = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/rea_case3_injections"
    persist_dir = "/Users/my/Documents/projects/detectionDeviation/pipeline/retrieval/chromadb_store"
    artifact_root = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_case3_v3"
    collection_name = "gdpr_requirements"

    search = VectorSearch(
        model_name="BAAI/bge-large-en-v1.5",
        collection_name=collection_name,
    )
    # Index/build step
    embed_result = search.embed_and_store(
         input_json_path=input_json,
         chroma_persist_dir=persist_dir,
         batch_size=32,
     )
    search_result = search.vector_search_for_rea_folder(
        rea_json_root_path=rea_json,
        chroma_persist_dir=persist_dir,
        artifact_root_dir=artifact_root,
        top_k=40,
    )
    # print("Stored vectors in ChromaDB:")
    # print(json.dumps(embed_result, indent=2, ensure_ascii=False))
    print("REA -> REG vector search results:")
    print(json.dumps(search_result, indent=2, ensure_ascii=False))


# Backward-compatible alias.
VectorEmbedding = VectorSearch


if __name__ == "__main__":
    main()
