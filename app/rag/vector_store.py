"""Local Chroma-backed vector store for the RAG knowledge base.

Embeddings are always supplied explicitly (via whichever provider the user
configured for RAG embeddings), bypassing Chroma's own default embedding
function entirely — this app never downloads or runs a bundled embedding
model of its own.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import chromadb

from app.config.settings import RAG_DIR
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_COLLECTION_NAME = "knowledge"


@dataclass
class RetrievedSnippet:
    text: str
    source: str
    distance: float


class RagStore:
    def __init__(self):
        RAG_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(RAG_DIR))
        # Cosine distance, not Chroma's default squared-L2: text embeddings are
        # not guaranteed to be unit-normalized, and cosine is the standard
        # choice for semantic similarity ranking.
        self._collection = self._client.get_or_create_collection(
            _COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def is_empty(self) -> bool:
        return self._collection.count() == 0

    def count(self) -> int:
        return self._collection.count()

    def add_chunks(self, source: str, chunks: list[str], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        batch = uuid.uuid4().hex[:8]
        ids = [f"{source}::{batch}::{i}" for i in range(len(chunks))]
        metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]
        self._collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

    def query(self, llm_client, provider_id: str, embedding_model: str, query_text: str, top_k: int = 3) -> list[RetrievedSnippet]:
        if self.is_empty():
            return []
        query_embedding = llm_client.embed(provider_id, embedding_model, query_text)
        result = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            RetrievedSnippet(text=doc, source=(meta or {}).get("source", "unknown"), distance=dist)
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

    def list_sources(self) -> list[tuple[str, int]]:
        if self.is_empty():
            return []
        data = self._collection.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in data.get("metadatas") or []:
            source = (meta or {}).get("source", "unknown")
            counts[source] = counts.get(source, 0) + 1
        return sorted(counts.items())

    def remove_source(self, source: str) -> None:
        self._collection.delete(where={"source": source})
