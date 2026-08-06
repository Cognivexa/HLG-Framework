"""RAG tab: add knowledge sources (file/folder/website/git repo), see what's
ingested, and test retrieval directly."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.llm.base import ProviderError
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background
from app.rag.ingestion import ingest_file, ingest_folder, ingest_git_repo, ingest_website
from app.rag.vector_store import RagStore
from app.ui.widgets.provider_model_selector import ProviderModelSelectorWidget

logger = get_logger(__name__)


class RagWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client
        self._store = RagStore()

        self._description_label = QLabel(
            "A local knowledge base Harness/Loop/Graph consult during their AI review steps — add your "
            "company's coding standards, architecture docs, or any reference material here (files, "
            "folders, websites, or git repos). Everything is embedded and stored on this machine only."
        )
        self._description_label.setWordWrap(True)

        self._model_selector = ProviderModelSelectorWidget(
            "Embedding model", settings, llm_client, "rag_embedding_provider", "rag_embedding_model",
            embeddings_only=True,
        )

        add_file_btn = QPushButton("Add File…")
        add_file_btn.clicked.connect(self._add_file)
        add_folder_btn = QPushButton("Add Folder…")
        add_folder_btn.clicked.connect(self._add_folder)
        add_website_btn = QPushButton("Add Website URL…")
        add_website_btn.clicked.connect(self._add_website)
        add_git_btn = QPushButton("Add Git Repo URL…")
        add_git_btn.clicked.connect(self._add_git_repo)
        remove_btn = QPushButton("Remove Selected Source")
        remove_btn.clicked.connect(self._remove_selected)

        add_row = QHBoxLayout()
        for btn in (add_file_btn, add_folder_btn, add_website_btn, add_git_btn, remove_btn):
            add_row.addWidget(btn)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)

        self._sources_list = QListWidget()

        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText("Test query against the knowledge base…")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search)
        query_row = QHBoxLayout()
        query_row.addWidget(self._query_edit, 1)
        query_row.addWidget(search_btn)

        self._results_view = QTextEdit()
        self._results_view.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._description_label)
        layout.addWidget(self._model_selector)
        layout.addLayout(add_row)
        layout.addWidget(self._status_label)
        layout.addWidget(QLabel("Ingested sources:"))
        layout.addWidget(self._sources_list)
        layout.addLayout(query_row)
        layout.addWidget(self._results_view)

        self._refresh_sources()

    def _embedding_model(self) -> str | None:
        model = self._settings.models.rag_embedding_model
        if not model:
            self._status_label.setText("Select a RAG embedding model in Settings first.")
            return None
        return model

    def _provider_id(self) -> str:
        return self._settings.models.rag_embedding_provider

    def _refresh_sources(self) -> None:
        self._sources_list.clear()
        for source, count in self._store.list_sources():
            self._sources_list.addItem(f"{source}  ({count} chunk(s))")

    def _run_ingest(self, work) -> None:
        self._status_label.setText("Ingesting… this may take a while (each chunk is embedded via Ollama).")

        def done(results) -> None:
            results = results if isinstance(results, list) else [results]
            total_chunks = sum(r.chunks_added for r in results)
            errors = [r.error for r in results if r.error]
            detail = f"Added {total_chunks} chunk(s) from {len(results)} document(s)."
            if errors:
                detail += f" {len(errors)} error(s), e.g. {errors[0][:150]}"
            self._status_label.setText(detail)
            self._refresh_sources()

        def failed(message: str) -> None:
            logger.error("RAG ingestion failed: %s", message)
            self._status_label.setText(f"Ingestion failed: {message}")

        run_in_background(work, on_finished=done, on_failed=failed)

    def _add_file(self) -> None:
        model = self._embedding_model()
        if not model:
            return
        path_str, _ = QFileDialog.getOpenFileName(self, "Select a document", "", "Documents (*.txt *.md *.pdf *.docx *.rst)")
        if not path_str:
            return
        self._run_ingest(lambda: ingest_file(self._store, self._llm_client, self._provider_id(), model, Path(path_str)))

    def _add_folder(self) -> None:
        model = self._embedding_model()
        if not model:
            return
        path_str = QFileDialog.getExistingDirectory(self, "Select a folder")
        if not path_str:
            return
        self._run_ingest(lambda: ingest_folder(self._store, self._llm_client, self._provider_id(), model, Path(path_str)))

    def _add_website(self) -> None:
        model = self._embedding_model()
        if not model:
            return
        url, ok = QInputDialog.getText(self, "Add Website", "URL:")
        if not ok or not url.strip():
            return
        self._run_ingest(lambda: ingest_website(self._store, self._llm_client, self._provider_id(), model, url.strip()))

    def _add_git_repo(self) -> None:
        model = self._embedding_model()
        if not model:
            return
        url, ok = QInputDialog.getText(self, "Add Git Repository", "Clone URL:")
        if not ok or not url.strip():
            return
        self._run_ingest(lambda: ingest_git_repo(self._store, self._llm_client, self._provider_id(), model, url.strip()))

    def _remove_selected(self) -> None:
        item = self._sources_list.currentItem()
        if not item:
            return
        source = item.text().rsplit("  (", 1)[0]
        self._store.remove_source(source)
        self._refresh_sources()

    def _search(self) -> None:
        model = self._embedding_model()
        if not model:
            return
        query = self._query_edit.text().strip()
        if not query:
            return
        try:
            snippets = self._store.query(self._llm_client, self._provider_id(), model, query, top_k=5)
        except ProviderError as exc:
            self._results_view.setPlainText(f"Search failed: {exc}")
            return
        if not snippets:
            self._results_view.setPlainText("No results (knowledge base may be empty).")
            return
        self._results_view.setPlainText(
            "\n\n".join(f"[{s.source}] (distance {s.distance:.3f})\n{s.text[:600]}" for s in snippets)
        )
