"""How It Works: a plain-language orientation tab explaining Harness, Loop,
and Graph Engineering — both as general concepts and as this app actually
implements them — plus a live strip showing what each pipeline is doing
right now. Every other tab assumes you already know what these three words
mean; this one is where a new/non-technical user starts instead.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.core.events import PipelineEvent, bus

_PIPELINE_LABELS = {
    "harness": "Harness Engineering",
    "loop": "Loop Engineering",
    "graph": "Graph Engineering",
    "code_review": "Code Review",
}

_STATUS_ICON = {"started": "▶", "completed": "✅", "failed": "❌", "blocked": "⛔"}


def _definition_box(title: str, concept_lines: list[str], in_this_app: str) -> QGroupBox:
    box = QGroupBox(title)
    layout = QVBoxLayout()
    for line in concept_lines:
        label = QLabel(f"• {line}")
        label.setWordWrap(True)
        layout.addWidget(label)
    app_label = QLabel(f"<b>In this app:</b> {in_this_app}")
    app_label.setWordWrap(True)
    layout.addWidget(app_label)
    box.setLayout(layout)
    return box


def _chain_box(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        "border: 1px solid #888; border-radius: 6px; padding: 8px; font-weight: bold;"
    )
    return label


class HowItWorksWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._latest_status: dict[str, str] = {}

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)

        intro = QLabel(
            "<b>Three engineering layers, one pipeline.</b> Harness Engineering is the "
            "environment an agent runs in (its tools, memory, context, and safety rules). "
            "Loop Engineering is repeating work — act, check, fix, re-check — until it's "
            "actually verified right, not just attempted once. Graph Engineering is deciding "
            "who runs when, in what order, and what happens when a step fails. "
            "This app chains all three together automatically every time you save a file: "
            "<b>Harness → Graph → Code Review → Clean Copy</b>, with Loop stepping in to fix "
            "things whenever Harness or Graph finds something fixable."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(_definition_box(
            "Harness Engineering — the environment",
            [
                "Orchestration & Routing: decides which agent/step runs next and how sub-steps are spawned.",
                "Typed Communication: strict, structured handoffs between steps instead of loose free text.",
                "Context Isolation: each check gets only the files/context it needs, not everything at once.",
                "Persistent State & Artifacts: logs, backups, and reports that survive past a single run.",
                "Validation Gates & Evals: automated tests/lint/security checks act as an objective pass/fail signal.",
            ],
            "the 21-step sequential pipeline on the Harness Engineering tab — secret/PII scanning, "
            "dependency/static/security analysis, build, tests, an AI code review, RAG retrieval, "
            "and architecture checks, run against whatever you just changed.",
        ))

        layout.addWidget(_definition_box(
            "Loop Engineering — repeat until it's right",
            [
                "Actor-Critic Pattern: one agent produces a fix, a separate check grades it — never the same model marking its own work.",
                "Self-Prompting & Iteration: a failure's details are fed back in as the next prompt, automatically.",
                "State & Memory: a scratchpad of what's been tried, so parallel attempts don't overwrite each other.",
                "Termination Logic: hard limits stop it from spinning forever on a fix that isn't working.",
            ],
            "the Loop Engineering tab's backup → apply fix → re-check → keep-or-rollback cycle. It keeps "
            "retrying for as long as each attempt fixes more than the last one — it only gives up once "
            "several attempts in a row make zero improvement (a genuine stall), not after a fixed number "
            "of tries. With Auto Run on, this includes secret/PII findings — fixed by moving the value to "
            "an environment variable, never by masking it. With Auto Run off, the same finding blocks for "
            "a human to review first.",
        ))

        layout.addWidget(_definition_box(
            "Graph Engineering — who runs when",
            [
                "Nodes: agents, deterministic checks, or human-review checkpoints — not just LLM calls.",
                "Edges: fixed or conditional transitions that say what feeds into what.",
                "State Management: explicit tracking of what each node can see or change.",
                "Cyclic Capabilities: feedback loops and retries, not just a strict one-way flow.",
            ],
            "the Graph Engineering tab's live agent DAG — the same checks Harness runs, but organized as "
            "16 nodes with real dependencies so independent ones run concurrently, ending in a Final "
            "Verification Agent that approves or rejects the whole run.",
        ))

        chain_box = QGroupBox("The actual chain in this app")
        chain_layout = QVBoxLayout()
        row = QHBoxLayout()
        for i, step in enumerate(["File saved", "Harness", "Graph", "Code Review", "Clean Copy exported"]):
            row.addWidget(_chain_box(step))
            if i < 4:
                row.addWidget(QLabel("→"))
        chain_layout.addLayout(row)
        chain_layout.addWidget(QLabel(
            "🔁 If Harness or Graph finds something fixable (build/test/lint/quality/architecture/docs), "
            "Loop fixes it and Harness re-checks — this repeats until it passes or genuinely stalls."
        ))
        chain_layout.addWidget(QLabel(
            "🔁 If Code Review finds a real regression, the whole chain restarts from Harness."
        ))
        chain_layout.addWidget(QLabel(
            "⛔ A secret/PII/password finding blocks immediately for manual review when Auto Run is off. "
            "With Auto Run on, Loop fixes it the same way as everything else — moved to an environment "
            "variable, verified by re-scanning, never masked."
        ))
        chain_box.setLayout(chain_layout)
        layout.addWidget(chain_box)

        live_box = QGroupBox("Live status right now")
        live_layout = QHBoxLayout()
        self._chips: dict[str, QLabel] = {}
        for pipeline_id, label_text in _PIPELINE_LABELS.items():
            chip = QLabel(f"{label_text}: idle")
            chip.setWordWrap(True)
            chip.setStyleSheet("border: 1px solid #666; border-radius: 6px; padding: 6px;")
            self._chips[pipeline_id] = chip
            live_layout.addWidget(chip)
        live_box.setLayout(live_layout)
        layout.addWidget(live_box)

        closing = QLabel(
            "When every stage is green, Code Review exports a clean copy of your project — that's the "
            "100% passed signal (see the release banner on the Dashboard and Eval tabs)."
        )
        closing.setWordWrap(True)
        layout.addWidget(closing)
        layout.addStretch(1)

        bus.pipeline_updated.connect(self._on_pipeline_updated)

    def _on_pipeline_updated(self, event: PipelineEvent) -> None:
        chip = self._chips.get(event.pipeline)
        if chip is None:
            return
        icon = _STATUS_ICON.get(event.status, "•")
        label = _PIPELINE_LABELS.get(event.pipeline, event.pipeline)
        detail = f" — {event.project_path}" if event.project_path else ""
        chip.setText(f"{icon} {label}{detail}")
