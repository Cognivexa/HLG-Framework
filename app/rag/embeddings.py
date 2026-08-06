"""Text chunking + embedding helpers for RAG ingestion."""
from __future__ import annotations

from app.core.llm_client import LLMClient

_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 150


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - overlap
    return chunks


def embed_chunks(llm_client: LLMClient, provider_id: str, model: str, chunks: list[str]) -> list[list[float]]:
    return [llm_client.embed(provider_id, model, chunk) for chunk in chunks]
