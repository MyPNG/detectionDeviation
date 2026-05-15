from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from .Reranker import Reranker
from .ranking import sort_top_matches


@dataclass
class RegObject:
    reg_id: str
    article: str
    paragraph: str
    text: str
    actor: str
    modal: str
    action: str
    action_list: list[str]
    object_text: str
    temporal: str
    manner: str
    condition: str
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
            reg_id=self._normalize_spaces(str(item.get("ID", item.get("id", "")))),
            article=self._normalize_article(item.get("Article", item.get("article", ""))),
            paragraph=self._normalize_spaces(str(item.get("Paragraph", item.get("paragraph", "")))),
            text=self._normalize_spaces(str(item.get("Text", item.get("text", "")))),
            actor=self._normalize_spaces(str(item.get("actor", ""))),
            modal=self._normalize_spaces(str(item.get("Modal", item.get("modal", "")))),
            action=self._normalize_spaces(str(item.get("action", ""))),
            action_list=[
                self._normalize_spaces(str(value))
                for value in item.get("action_list", [])
                if self._normalize_spaces(str(value))
            ]
            if isinstance(item.get("action_list", []), list)
            else ([self._normalize_spaces(str(item.get("action_list", "")))] if self._normalize_spaces(str(item.get("action_list", ""))) else []),
            object_text=self._normalize_spaces(str(item.get("object", ""))),
            temporal=self._normalize_spaces(str(item.get("temporal", ""))),
            manner=self._normalize_spaces(str(item.get("manner", ""))),
            condition=self._normalize_spaces(str(item.get("condition", ""))),
            references=[self._normalize_spaces(str(ref)) for ref in references if str(ref).strip()],
        )

    def load_reg_objects(self, input_json_path: str | Path) -> list[RegObject]:
        input_path = Path(input_json_path).expanduser().resolve()
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("results", [])
        if not isinstance(payload, list):
            raise ValueError("Input JSON must be a list of requirement objects or an object with a 'results' list.")

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
    def _clean_placeholder(value: str) -> str:
        normalized = str(value)
        normalized = re.sub(r"\[\s*missing_subject\s*\]", " ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bmissing_subject\b", " ", normalized, flags=re.IGNORECASE)
        normalized = " ".join(normalized.split()).strip()
        lowered = normalized.lower()
        if lowered in {"", "[missing_subject]", "missing_subject"}:
            return ""
        return normalized

    @classmethod
    def _build_structured_text(
        cls,
        *,
        actor: str,
        modal: str,
        action: str,
        action_list: list[str],
        object_text: str,
        temporal: str,
        manner: str,
        condition: str,
        text: str,
    ) -> str:
        actions_text = " | ".join(cls._clean_placeholder(value) for value in action_list if cls._clean_placeholder(value))
        parts = [
            f"actions: {actions_text}" if actions_text else "",
            f"action: {cls._clean_placeholder(action)}" if cls._clean_placeholder(action) else "",
            f"object: {cls._clean_placeholder(object_text)}" if cls._clean_placeholder(object_text) else "",
            f"actor: {cls._clean_placeholder(actor)}" if cls._clean_placeholder(actor) else "",
            f"modal: {cls._clean_placeholder(modal)}" if cls._clean_placeholder(modal) else "",
            f"temporal: {cls._clean_placeholder(temporal)}" if cls._clean_placeholder(temporal) else "",
            f"condition: {cls._clean_placeholder(condition)}" if cls._clean_placeholder(condition) else "",
            f"manner: {cls._clean_placeholder(manner)}" if cls._clean_placeholder(manner) else "",
            f"text: {cls._clean_placeholder(text)}" if cls._clean_placeholder(text) else "",
        ]
        return "\n".join(part for part in parts if part)

    @classmethod
    def _build_embedding_text(cls, reg_obj: RegObject) -> str:
        return cls._build_structured_text(
            actor=reg_obj.actor,
            modal=reg_obj.modal,
            action=reg_obj.action,
            action_list=reg_obj.action_list,
            object_text=reg_obj.object_text,
            temporal=reg_obj.temporal,
            manner=reg_obj.manner,
            condition=reg_obj.condition,
            text=reg_obj.text,
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
                "text": obj.text,
                "embedding_text": embedding_texts[idx],
                "actor": obj.actor,
                "modal": obj.modal,
                "action": obj.action,
                "action_list": " | ".join(obj.action_list),
                "object": obj.object_text,
                "temporal": obj.temporal,
                "manner": obj.manner,
                "condition": obj.condition,
                "references": ", ".join(obj.references),
            }
            for idx, obj in enumerate(reg_objects)
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
        if isinstance(payload, dict):
            payload = payload.get("stage4_output", [])
        if not isinstance(payload, list):
            raise ValueError("REA input JSON must be a list.")

        items: list[dict[str, str]] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            rea_id = self._normalize_spaces(
                str(row.get("sub_id", row.get("rea_id", row.get("id", ""))))
            )
            raw_text = self._normalize_spaces(str(row.get("text", "")))
            text = self._clean_placeholder(raw_text)
            query_text = self._build_structured_text(
                actor=self._normalize_spaces(str(row.get("actor", ""))),
                modal=self._normalize_spaces(str(row.get("modal", row.get("Modal", "")))),
                action=self._normalize_spaces(str(row.get("action", ""))),
                action_list=[
                    self._normalize_spaces(str(value))
                    for value in row.get("action_list", [])
                    if self._normalize_spaces(str(value))
                ]
                if isinstance(row.get("action_list", []), list)
                else ([self._normalize_spaces(str(row.get("action_list", "")))] if self._normalize_spaces(str(row.get("action_list", ""))) else []),
                object_text=self._normalize_spaces(str(row.get("object", ""))),
                temporal=self._normalize_spaces(str(row.get("temporal", ""))),
                manner=self._normalize_spaces(str(row.get("manner", ""))),
                condition=self._normalize_spaces(str(row.get("condition", ""))),
                text=text,
            )
            if not rea_id or not query_text:
                continue
            items.append({"rea_id": rea_id, "text": text, "query_text": query_text})
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
                    "text": self._normalize_spaces(str(metadata.get("text", "")))
                    or self._normalize_spaces(str(doc_text)),
                    "embedding text": self._normalize_spaces(str(metadata.get("embedding_text", ""))),
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
            query_text = item["query_text"]
            top_matches = self._search_single_query(
                query_text=query_text,
                collection=collection,
                top_k=top_k,
            )
            payload = {
                "id": rea_id,
                "search query": item["text"],
                "embedding query": query_text,
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
        If input is a folder, collect `*_deontic_stages.json` files recursively,
        else `*_requirements.json`.
        """
        root = Path(rea_json_root_path).expanduser().resolve()
        if root.is_file():
            return [root]
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"REA input path not found: {root}")

        stage_files = sorted(root.rglob("*_deontic_stages.json"))
        if stage_files:
            return stage_files

        files = sorted(root.rglob("*_requirements.json"))
        if files:
            return files
        raise FileNotFoundError(
            f"No *_deontic_stages.json or *_requirements.json files found under: {root}"
        )

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
                query_text = item["query_text"]
                top_matches = self._search_single_query(
                    query_text=query_text,
                    collection=collection,
                    top_k=top_k,
                )
                payload = {
                    "id": rea_id,
                    "search query": item["text"],
                    "embedding query": query_text,
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

    def search_and_rerank_for_rea_folder(
        self,
        *,
        rea_json_root_path: str | Path,
        chroma_persist_dir: str | Path,
        artifact_root_dir: str | Path,
        reranked_output_root_dir: str | Path,
        top_k: int = 100,
        rerank_top_n: int = 100,
        reranker_model_name: str = "kanon-2-reranker",
        reranker_api_key_env: str = "ISAACUS_API_KEY",
    ) -> dict[str, Any]:
        """
        Combined retrieval convenience:
        1) dense vector search
        2) reranking
        3) deterministic top-match sort for downstream prompt preparation
        """
        search_result = self.vector_search_for_rea_folder(
            rea_json_root_path=rea_json_root_path,
            chroma_persist_dir=chroma_persist_dir,
            artifact_root_dir=artifact_root_dir,
            top_k=top_k,
        )

        reranker = Reranker(
            model_name=reranker_model_name,
            api_key_env=reranker_api_key_env,
        )
        rerank_result = reranker.rerank_artifact_root(
            input_artifact_01_dir=artifact_root_dir,
            output_artifact_dir=reranked_output_root_dir,
            top_n=rerank_top_n,
        )

        reranked_root = Path(reranked_output_root_dir).expanduser().resolve()
        for payload_file in sorted(reranked_root.rglob("rea-*.json")):
            try:
                payload = json.loads(payload_file.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and isinstance(payload.get("top matches"), list):
                    payload["top matches"] = sort_top_matches(payload.get("top matches", []))
                    payload_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                continue

        return {
            "vector_search": search_result,
            "reranker": rerank_result,
            "reranked_output_root_dir": str(reranked_root),
        }


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    reg_input_name = "reg_for_injectiontest"
    rea_input_name = "rea_with_injections"
    input_json = (
        project_root
        / "intermediate_results"
        / "01_preprocessing"
        / "reg_prep"
        / "01_extracting"
        / "mainrequirementsslotfilter"
        / reg_input_name
        / f"{reg_input_name}_requirements_slots_main.json"
    )
    rea_json = (
        project_root
        / "intermediate_results"
        / "01_preprocessing"
        / "reaPrep"
        / "01_extracting"
        / "readeonticstagepipeline"
        / rea_input_name
    )
    persist_dir = (
        project_root
        / "intermediate_results"
        / "01_preprocessing"
        / "reg_prep"
        / "02_vector_embedding"
        / "embeddingindexbuilder"
        / reg_input_name
        / "chromadb_store"
    )
    artifact_root = (
        project_root
        / "intermediate_results"
        / "02_processing"
        / "01_retrieval"
        / "vectorsearch"
        / f"artifact_01_{rea_input_name}__{reg_input_name}"
    )
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
        top_k=100,
    )
    # print("Stored vectors in ChromaDB:")
    # print(json.dumps(embed_result, indent=2, ensure_ascii=False))
    print("REA -> REG vector search results:")
    print(json.dumps(search_result, indent=2, ensure_ascii=False))


# Backward-compatible alias.
VectorEmbedding = VectorSearch


if __name__ == "__main__":
    main()
