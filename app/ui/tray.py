"""System tray icon and its context menu — the app lives here when minimized."""
from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from app.config.constants import APP_DISPLAY_NAME


class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon: QIcon, window: QWidget):
        super().__init__(icon)
        self._window = window
        self.setToolTip(APP_DISPLAY_NAME)

        menu = QMenu()
        show_action = QAction("Show Dashboard", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        self._pause_action = QAction("Pause Monitoring", menu)
        self._pause_action.setCheckable(True)
        menu.addAction(self._pause_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    @property
    def pause_action(self) -> QAction:
        return self._pause_action

    def _show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _quit(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def notify(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        self.showMessage(title, message, icon, 5000)
