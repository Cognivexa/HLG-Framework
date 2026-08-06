"""Knowledge-source ingestion: turns files, folders, websites, or git repos
into embedded chunks in the local RAG store."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from app.config.settings import RAG_DIR
from app.core.llm_client import LLMClient
from app.core.logging_setup import get_logger
from app.rag.embeddings import chunk_text, embed_chunks
from app.rag.vector_store import RagStore

logger = get_logger(__name__)

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".py", ".json", ".yaml", ".yml"}
_IGNORED_FOLDER_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


@dataclass
class IngestResult:
    source: str
    chunks_added: int
    error: str = ""


def _read_txt_like(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _read_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def _read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    return _read_txt_like(path)


def _read_website(url: str) -> str:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "HLGFramework/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _clone_git_repo(url: str) -> Path | None:
    if shutil.which("git") is None:
        return None
    dest = RAG_DIR / "git_sources" / uuid.uuid4().hex[:10]
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True, text=True, timeout=120, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.warning("git clone failed for %s: %s", url, exc)
        return None
    return dest


def _iter_folder_documents(folder: Path):
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _IGNORED_FOLDER_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.suffix.lower() in (".pdf", ".docx"):
            yield path


def ingest_file(store: RagStore, llm_client: LLMClient, provider_id: str, embedding_model: str, path: Path) -> IngestResult:
    try:
        text = _read_file(path)
    except Exception as exc:  # noqa: BLE001 - a bad file must not abort the whole ingestion run
        return IngestResult(source=str(path), chunks_added=0, error=str(exc))
    chunks = chunk_text(text)
    if not chunks:
        return IngestResult(source=str(path), chunks_added=0, error="No extractable text.")
    embeddings = embed_chunks(llm_client, provider_id, embedding_model, chunks)
    store.add_chunks(str(path), chunks, embeddings)
    return IngestResult(source=str(path), chunks_added=len(chunks))


def ingest_folder(store: RagStore, llm_client: LLMClient, provider_id: str, embedding_model: str, folder: Path) -> list[IngestResult]:
    return [
        ingest_file(store, llm_client, provider_id, embedding_model, path)
        for path in _iter_folder_documents(folder)
    ]


def ingest_website(store: RagStore, llm_client: LLMClient, provider_id: str, embedding_model: str, url: str) -> IngestResult:
    try:
        text = _read_website(url)
    except Exception as exc:  # noqa: BLE001
        return IngestResult(source=url, chunks_added=0, error=str(exc))
    chunks = chunk_text(text)
    if not chunks:
        return IngestResult(source=url, chunks_added=0, error="No extractable text.")
    embeddings = embed_chunks(llm_client, provider_id, embedding_model, chunks)
    store.add_chunks(url, chunks, embeddings)
    return IngestResult(source=url, chunks_added=len(chunks))


def ingest_git_repo(store: RagStore, llm_client: LLMClient, provider_id: str, embedding_model: str, url: str) -> list[IngestResult]:
    dest = _clone_git_repo(url)
    if dest is None:
        return [IngestResult(source=url, chunks_added=0, error="git not available on PATH, or clone failed")]
    return ingest_folder(store, llm_client, provider_id, embedding_model, dest)
