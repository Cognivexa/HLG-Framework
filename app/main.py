"""Application entry point: bootstraps Qt, the tray icon, and the main window."""
from __future__ import annotations

import sys
import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from app.config.constants import APP_DISPLAY_NAME
from app.config.settings import AppSettings
from app.core.events import bus
from app.core.file_watcher import WatcherManager
from app.core.llm_client import LLMClient
from app.core.logging_setup import configure_logging, get_logger
from app.core.ollama_client import OllamaClient
from app.core.pipeline_controller import PipelineController
from app.core.pipeline_worker import run_in_background
from app.notifications.notifier import Notifier
from app.ui.icons import build_app_icon
from app.ui.main_window import MainWindow
from app.ui.tray import TrayIcon

logger = get_logger(__name__)


def main() -> int:
    configure_logging()
    logger.info("Starting %s", APP_DISPLAY_NAME)

    # Must be set before QApplication is constructed. Without this, a
    # fractional Windows display scale (125%/150% — the common case on
    # laptops) makes a Qt6 app render oversized/blurry; PassThrough uses the
    # exact scale factor instead of rounding to the nearest integer.
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_DISPLAY_NAME)

    icon = build_app_icon()
    app.setWindowIcon(icon)

    settings = AppSettings.load()
    ollama_client = OllamaClient(host=settings.ollama_host)  # local-only: drives the Dashboard's Ollama status banner
    llm_client = LLMClient(settings)  # multi-provider facade: used by every pipeline
    watcher_manager = WatcherManager()
    pipeline_controller = PipelineController(settings, llm_client)

    window = MainWindow(
        settings=settings, ollama_client=ollama_client, llm_client=llm_client,
        watcher_manager=watcher_manager, pipeline_controller=pipeline_controller,
    )
    window.setWindowIcon(icon)

    tray = TrayIcon(icon=icon, window=window)
    tray.show()
    notifier = Notifier(tray)  # noqa: F841 - keeps signal connections alive

    def on_pause_toggled(checked: bool) -> None:
        if checked:
            watcher_manager.stop_all()
            logger.info("Monitoring paused from tray")
        else:
            watcher_manager.set_projects(settings.projects, settings.debounce_seconds)
            logger.info("Monitoring resumed from tray")

    tray.pause_action.toggled.connect(on_pause_toggled)

    if settings.monitoring_enabled:
        watcher_manager.set_projects(settings.projects, settings.debounce_seconds)

    web_mirror = None
    if settings.web_dashboard_enabled:
        from app.web.server import WebMirrorServer

        web_mirror = WebMirrorServer(port=settings.web_dashboard_port)
        web_mirror.start()
        logger.info("Web mirror listening on %s", web_mirror.url)
        webbrowser.open(web_mirror.url)
    window.web_mirror = web_mirror  # keeps a reference; also lets the Dashboard tab's "Open in Browser" button find it

    # Both calls below are blocking HTTP requests (up to ~2s + ~15s of timeout
    # budget). Running them straight on this QTimer's callback — as a bare
    # synchronous call — would freeze the entire UI (including the model
    # dropdowns) every 15s whenever Ollama is slow, unreachable, or DNS stalls
    # past the requests timeout. run_in_background keeps this off the GUI
    # thread; `_poll_in_flight` skips overlapping polls if one is still out.
    _poll_in_flight = {"value": False}

    def poll_ollama() -> None:
        if _poll_in_flight["value"]:
            return
        _poll_in_flight["value"] = True

        def work():
            available = ollama_client.is_available()
            models = [m.name for m in ollama_client.list_models()] if available else []
            return available, models

        def done(result) -> None:
            _poll_in_flight["value"] = False
            available, models = result
            bus.ollama_status_changed.emit(available, models)

        def failed(message: str) -> None:
            _poll_in_flight["value"] = False
            logger.warning("Ollama status poll failed: %s", message)
            bus.ollama_status_changed.emit(False, [])

        run_in_background(work, on_finished=done, on_failed=failed)

    ollama_timer = QTimer()
    ollama_timer.timeout.connect(poll_ollama)
    ollama_timer.start(15_000)
    poll_ollama()

    window.show()
    exit_code = app.exec()
    watcher_manager.stop_all()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
