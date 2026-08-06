"""Live DAG view: nodes positioned by topological depth, colored by live
status as GraphNodeEvents arrive from the bus."""
from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

from app.core.events import GraphNodeEvent

_STATUS_COLORS = {
    "pending": QColor("#3a3d42"),
    "running": QColor("#2f81f7"),
    "success": QColor("#3fb950"),
    "failed": QColor("#f85149"),
    "skipped": QColor("#8b8f98"),
}

_NODE_W, _NODE_H = 180, 44
_X_GAP, _Y_GAP = 220, 62


def _compute_levels(depends_on_by_id: dict[str, tuple[str, ...]]) -> dict[str, int]:
    levels: dict[str, int] = {}

    def level_of(node_id: str) -> int:
        if node_id in levels:
            return levels[node_id]
        deps = depends_on_by_id.get(node_id, ())
        relevant = [d for d in deps if d in depends_on_by_id]
        levels[node_id] = 0 if not relevant else 1 + max(level_of(d) for d in relevant)
        return levels[node_id]

    for node_id in depends_on_by_id:
        level_of(node_id)
    return levels


class GraphViewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._current_run_id: str | None = None
        self._rects: dict[str, QGraphicsRectItem] = {}

    def build_layout(self, run_id: str, nodes: dict) -> None:
        """`nodes`: dict[node_id, GraphNode-like with .label and .depends_on]."""
        self._current_run_id = run_id
        self._scene.clear()
        self._rects.clear()

        depends_on_by_id = {node_id: node.depends_on for node_id, node in nodes.items()}
        levels = _compute_levels(depends_on_by_id)

        columns: dict[int, list[str]] = {}
        for node_id, level in levels.items():
            columns.setdefault(level, []).append(node_id)

        positions: dict[str, tuple[float, float]] = {}
        for level, node_ids in sorted(columns.items()):
            for row, node_id in enumerate(node_ids):
                positions[node_id] = (level * _X_GAP, row * _Y_GAP)

        for node_id, node in nodes.items():
            x2, y2 = positions[node_id]
            for dep in node.depends_on:
                if dep not in positions:
                    continue
                x1, y1 = positions[dep]
                line = QGraphicsLineItem(x1 + _NODE_W, y1 + _NODE_H / 2, x2, y2 + _NODE_H / 2)
                line.setPen(QPen(QColor("#555a63"), 1.5))
                self._scene.addItem(line)

        for node_id, node in nodes.items():
            x, y = positions[node_id]
            rect = QGraphicsRectItem(QRectF(x, y, _NODE_W, _NODE_H))
            rect.setBrush(QBrush(_STATUS_COLORS["pending"]))
            rect.setPen(QPen(QColor("#1e1f22"), 1))
            self._scene.addItem(rect)
            self._rects[node_id] = rect

            label = QGraphicsTextItem(node.label)
            label.setDefaultTextColor(QColor("white"))
            label.setPos(x + 8, y + 10)
            label.setTextWidth(_NODE_W - 16)
            self._scene.addItem(label)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-20, -20, 20, 20))

    def on_node_event(self, event: GraphNodeEvent) -> None:
        if event.run_id != self._current_run_id:
            return
        rect = self._rects.get(event.node_id)
        if rect is None:
            return
        rect.setBrush(QBrush(_STATUS_COLORS.get(event.status, QColor("gray"))))
