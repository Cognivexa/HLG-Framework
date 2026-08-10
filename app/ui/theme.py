"""Dark/light stylesheets for the enterprise dashboard look."""
from __future__ import annotations

DARK_QSS = """
QWidget { background-color: #1e1f22; color: #d4d4d8; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background-color: #1e1f22; }
QTabWidget::pane { border: 1px solid #33353a; }
QTabBar::tab { background: #26282c; padding: 6px 12px; color: #a9adb4; }
QTabBar::tab:selected { background: #2f81f7; color: white; }
QGroupBox { border: 1px solid #33353a; border-radius: 5px; margin-top: 8px; padding-top: 6px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton { background-color: #2f81f7; color: white; border: none; padding: 5px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #4b93f8; }
QPushButton:disabled { background-color: #3a3d42; color: #75787e; }
QListWidget, QTableWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #26282c; border: 1px solid #33353a; border-radius: 4px; color: #d4d4d8; padding: 2px 4px;
}
QLabel[role="banner-ok"] { color: #3fb950; font-weight: 600; padding: 3px; }
QLabel[role="banner-error"] { color: #f85149; font-weight: 600; padding: 3px; }
QProgressBar { background-color: #26282c; border: 1px solid #33353a; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background-color: #2f81f7; }
"""

LIGHT_QSS = """
QWidget { background-color: #f5f6f8; color: #1b1f24; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background-color: #f5f6f8; }
QTabWidget::pane { border: 1px solid #d0d7de; }
QTabBar::tab { background: #eaecef; padding: 6px 12px; color: #57606a; }
QTabBar::tab:selected { background: #0969da; color: white; }
QGroupBox { border: 1px solid #d0d7de; border-radius: 5px; margin-top: 8px; padding-top: 6px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton { background-color: #0969da; color: white; border: none; padding: 5px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #2186f5; }
QPushButton:disabled { background-color: #d0d7de; color: #8c959f; }
QListWidget, QTableWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 4px; color: #1b1f24; padding: 2px 4px;
}
QLabel[role="banner-ok"] { color: #1a7f37; font-weight: 600; padding: 3px; }
QLabel[role="banner-error"] { color: #cf222e; font-weight: 600; padding: 3px; }
QProgressBar { background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background-color: #0969da; }
"""


def stylesheet_for(theme: str) -> str:
    return DARK_QSS if theme == "dark" else LIGHT_QSS
