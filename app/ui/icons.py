"""Programmatic app icon so the app doesn't depend on a bundled image asset."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap


def build_app_icon(size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2f81f7"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, size * 0.2, size * 0.2)

    painter.setPen(QColor("white"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(int(size * 0.5))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "H")
    painter.end()

    return QIcon(pixmap)
