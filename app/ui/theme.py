"""Dark/light/aurora stylesheets for the enterprise dashboard look."""
from __future__ import annotations

# Shared, theme-agnostic polish appended to every palette below: rounded
# scrollbars (Qt's default OS scrollbar looks dated and isn't styled at all
# otherwise), a visible focus ring for keyboard nav, and consistent checkbox/
# radio sizing. QSS has no `transition` property, so "smoother" here means
# real hover/pressed states everywhere a control is interactive (so nothing
# looks static/dead under the cursor) plus generally larger corner radii —
# not literal animation.
_COMMON_QSS_TEMPLATE = """
QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll_handle; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: $scroll_handle_hover; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: $scroll_handle; border-radius: 5px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: $scroll_handle_hover; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QCheckBox, QRadioButton { spacing: 6px; }
QToolTip { background-color: $tooltip_bg; color: $tooltip_fg; border: 1px solid $border; padding: 4px 6px; border-radius: 4px; }
"""


def _common_qss(scroll_handle: str, scroll_handle_hover: str, tooltip_bg: str, tooltip_fg: str, border: str) -> str:
    # Plain string substitution, not str.format() — the template above is
    # full of literal QSS `{ ... }` blocks that .format() would try (and
    # fail) to parse as replacement fields.
    return (
        _COMMON_QSS_TEMPLATE
        .replace("$scroll_handle_hover", scroll_handle_hover)
        .replace("$scroll_handle", scroll_handle)
        .replace("$tooltip_bg", tooltip_bg)
        .replace("$tooltip_fg", tooltip_fg)
        .replace("$border", border)
    )

DARK_QSS = """
QWidget { background-color: #1e1f22; color: #d4d4d8; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background-color: #1e1f22; }
QTabWidget::pane { border: 1px solid #33353a; }
QTabBar::tab { background: #26282c; padding: 6px 12px; color: #a9adb4; }
QTabBar::tab:selected { background: #2f81f7; color: white; }
QTabBar::tab:hover:!selected { background: #303236; }
QGroupBox { border: 1px solid #33353a; border-radius: 5px; margin-top: 8px; padding-top: 6px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton { background-color: #2f81f7; color: white; border: none; padding: 5px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #4b93f8; }
QPushButton:pressed { background-color: #2569c9; }
QPushButton:disabled { background-color: #3a3d42; color: #75787e; }
QListWidget, QTableWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #26282c; border: 1px solid #33353a; border-radius: 4px; color: #d4d4d8; padding: 2px 4px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #2f81f7;
}
QLabel[role="banner-ok"] { color: #3fb950; font-weight: 600; padding: 3px; }
QLabel[role="banner-error"] { color: #f85149; font-weight: 600; padding: 3px; }
QProgressBar { background-color: #26282c; border: 1px solid #33353a; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background-color: #2f81f7; }
""" + _common_qss(
    scroll_handle="#3a3d42", scroll_handle_hover="#4b4e54", tooltip_bg="#26282c", tooltip_fg="#d4d4d8", border="#33353a",
)

LIGHT_QSS = """
QWidget { background-color: #f5f6f8; color: #1b1f24; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background-color: #f5f6f8; }
QTabWidget::pane { border: 1px solid #d0d7de; }
QTabBar::tab { background: #eaecef; padding: 6px 12px; color: #57606a; }
QTabBar::tab:selected { background: #0969da; color: white; }
QTabBar::tab:hover:!selected { background: #dde2e7; }
QGroupBox { border: 1px solid #d0d7de; border-radius: 5px; margin-top: 8px; padding-top: 6px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton { background-color: #0969da; color: white; border: none; padding: 5px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #2186f5; }
QPushButton:pressed { background-color: #0757ba; }
QPushButton:disabled { background-color: #d0d7de; color: #8c959f; }
QListWidget, QTableWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 4px; color: #1b1f24; padding: 2px 4px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #0969da;
}
QLabel[role="banner-ok"] { color: #1a7f37; font-weight: 600; padding: 3px; }
QLabel[role="banner-error"] { color: #cf222e; font-weight: 600; padding: 3px; }
QProgressBar { background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background-color: #0969da; }
""" + _common_qss(
    scroll_handle="#c7ced4", scroll_handle_hover="#aeb6bd", tooltip_bg="#1b1f24", tooltip_fg="#f5f6f8", border="#d0d7de",
)

# "Aurora" — the deep-navy, multi-accent look (blue / purple / orange / teal)
# from the "Prompt vs Context vs Harness vs Loop" infographic. Same widget
# set as the other two palettes, just a different, more vivid identity:
# gradient panels instead of flat fills, a violet-to-blue accent for
# selection/focus, and rounder, larger-radius controls throughout.
AURORA_QSS = """
QWidget { background-color: #0b0f1e; color: #cbd5f5; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background-color: #0b0f1e; }
QTabWidget::pane { border: 1px solid #232a45; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #10162a; padding: 7px 14px; margin-right: 2px; color: #8b93b8;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f6df5, stop:1 #8b5cf6); color: white;
}
QTabBar::tab:hover:!selected { background: #171f38; color: #cbd5f5; }
QGroupBox {
    background-color: #0f1526; border: 1px solid #232a45; border-radius: 10px;
    margin-top: 10px; padding-top: 8px; font-weight: 600; color: #e8ecff;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #93a4ff; }
QLabel { color: #cbd5f5; }
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f6df5, stop:1 #7c5cf0);
    color: white; border: none; padding: 6px 14px; border-radius: 8px; font-weight: 600;
}
QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6b85ff, stop:1 #9575f5); }
QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d54c9, stop:1 #6444c2); }
QPushButton:disabled { background: #1c2340; color: #5b6389; }
QListWidget, QTableWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #10162a; border: 1px solid #232a45; border-radius: 6px; color: #d7defc; padding: 3px 6px;
    selection-background-color: #4f6df5; selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #7c5cf0;
}
QComboBox::drop-down { border: none; width: 20px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px; height: 15px; border: 1px solid #3a4270; border-radius: 4px; background: #10162a;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f6df5, stop:1 #34d399); border: 1px solid #4f6df5;
}
QLabel[role="banner-ok"] { color: #34d399; font-weight: 600; padding: 4px; }
QLabel[role="banner-error"] { color: #fb7185; font-weight: 600; padding: 4px; }
QProgressBar {
    background-color: #10162a; border: 1px solid #232a45; border-radius: 6px; text-align: center; color: #cbd5f5;
}
QProgressBar::chunk {
    border-radius: 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f6df5, stop:0.6 #8b5cf6, stop:1 #fb923c);
}
QMenu { background-color: #10162a; border: 1px solid #232a45; border-radius: 8px; padding: 4px; }
QMenu::item { padding: 5px 20px; border-radius: 4px; }
QMenu::item:selected { background-color: #232a45; }
""" + _common_qss(
    scroll_handle="#2a3358", scroll_handle_hover="#3d4a80", tooltip_bg="#171f38", tooltip_fg="#e8ecff", border="#232a45",
)


def stylesheet_for(theme: str) -> str:
    if theme == "light":
        return LIGHT_QSS
    if theme == "aurora":
        return AURORA_QSS
    return DARK_QSS
