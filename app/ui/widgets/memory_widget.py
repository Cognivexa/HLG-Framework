"""Memory tab: the three kinds of memory behind a reliable agent, all
backed by real, already-existing storage in this app rather than a new
parallel subsystem —

- **Semantic** — the RAG knowledge base (app/rag): manually ingested docs
  plus, now, short generalized lessons the memory gate decided were worth
  keeping after a Loop Engineering fix (tagged "learned-fix::<run_id>").
- **Episodic** — the run history (app/reports/history.py): what actually
  happened, when, pass or fail.
- **Procedural** — installed plugin steps (app/plugins): "how to act" that
  every Harness run picks up automatically.

Below all three: the memory gate's own decision log (app/core/memory_log.py)
— not every successful fix is remembered, so this tab shows what was kept,
what wasn't, and why.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QLabel, QListWidget, QVBoxLayout, QWidget

from app.core import memory_log
from app.plugins.loader import get_registry
from app.rag.vector_store import RagStore
from app.reports.history import list_runs

_REFRESH_MS = 3000
_MAX_EPISODIC_ROWS = 25
_MAX_GATE_ROWS = 25


class MemoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        description = QLabel(
            "The memory behind this app's agents: semantic (the RAG knowledge base — reference docs "
            "plus lessons learned from past fixes), episodic (what actually ran and when), and "
            "procedural (installed plugin steps). The memory gate at the bottom decides which fixes "
            "were generalizable enough to keep."
        )
        description.setWordWrap(True)

        semantic_box = QGroupBox("Semantic memory — RAG knowledge base")
        self._semantic_list = QListWidget()
        semantic_layout = QVBoxLayout()
        semantic_layout.addWidget(self._semantic_list)
        semantic_box.setLayout(semantic_layout)

        episodic_box = QGroupBox("Episodic memory — recent runs")
        self._episodic_list = QListWidget()
        episodic_layout = QVBoxLayout()
        episodic_layout.addWidget(self._episodic_list)
        episodic_box.setLayout(episodic_layout)

        procedural_box = QGroupBox("Procedural memory — installed plugin steps")
        self._procedural_list = QListWidget()
        procedural_layout = QVBoxLayout()
        procedural_layout.addWidget(self._procedural_list)
        procedural_box.setLayout(procedural_layout)

        gate_box = QGroupBox("Memory gate decisions")
        self._gate_list = QListWidget()
        gate_layout = QVBoxLayout()
        gate_layout.addWidget(self._gate_list)
        gate_box.setLayout(gate_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addWidget(semantic_box)
        layout.addWidget(episodic_box)
        layout.addWidget(procedural_box)
        layout.addWidget(gate_box)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(_REFRESH_MS)
        self._refresh()

    def _refresh(self) -> None:
        self._refresh_semantic()
        self._refresh_episodic()
        self._refresh_procedural()
        self._refresh_gate()

    def _refresh_semantic(self) -> None:
        self._semantic_list.clear()
        try:
            sources = RagStore().list_sources()
        except Exception as exc:  # noqa: BLE001 - the RAG store may not have been initialized yet
            self._semantic_list.addItem(f"(unavailable: {exc})")
            return
        if not sources:
            self._semantic_list.addItem("(empty — add sources on the RAG tab)")
            return
        for source, count in sources:
            label = "🧠 learned fix" if source.startswith("learned-fix::") else "📄"
            self._semantic_list.addItem(f"{label} {source}  ({count} chunk(s))")

    def _refresh_episodic(self) -> None:
        self._episodic_list.clear()
        runs = list_runs()[:_MAX_EPISODIC_ROWS]
        if not runs:
            self._episodic_list.addItem("(no runs yet)")
            return
        for run in runs:
            icon = "✅" if run.get("overall_status") == "PASSED" else "❌"
            self._episodic_list.addItem(
                f"{icon} [{run.get('pipeline')}] {run.get('generated_at')} — "
                f"{run.get('passed', 0)} passed / {run.get('failed', 0)} failed"
            )

    def _refresh_procedural(self) -> None:
        self._procedural_list.clear()
        steps = get_registry().steps
        if not steps:
            self._procedural_list.addItem("(no plugins installed — see docs/ARCHITECTURE.md)")
            return
        for step in steps.values():
            self._procedural_list.addItem(f"🔌 {step.name} ({step.id})")

    def _refresh_gate(self) -> None:
        self._gate_list.clear()
        decisions = memory_log.list_decisions()[:_MAX_GATE_ROWS]
        if not decisions:
            self._gate_list.addItem("(no Loop fixes have gone through the memory gate yet)")
            return
        for decision in decisions:
            if decision.get("remember"):
                self._gate_list.addItem(f"🧠 Remembered: {decision.get('lesson')}")
            else:
                reason = decision.get("reason") or "Not generalizable enough to remember."
                self._gate_list.addItem(f"— Not remembered ({decision.get('run_id')}): {reason}")
