"""Generic background worker for running pipeline functions off the UI thread."""
from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from app.core.logging_setup import get_logger

logger = get_logger(__name__)

# A single, permanently-alive QObject that every background task's
# completion is routed through, instead of each task getting its own
# short-lived QObject to emit from. A per-task QObject with no parent has no
# guaranteed lifetime once the QRunnable that created it finishes and is
# eligible for cleanup — even holding a Python-side reference to the
# runnable, PySide6/Shiboken can tear down the underlying C++ object before
# the finished/failed signal, queued for cross-thread delivery, actually
# reaches the GUI thread's event loop. That race manifested as "Signal
# source has been deleted" and a completion callback that silently never
# fires. Routing through one dispatcher that lives for the process's
# lifetime removes the race entirely: there's nothing to race against.
class _Dispatcher(QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)


_dispatcher = _Dispatcher()
_callbacks: dict[int, tuple[Callable[[object], None] | None, Callable[[str], None] | None]] = {}
_next_id_lock = threading.Lock()
_next_id = 0


def _next_call_id() -> int:
    global _next_id
    with _next_id_lock:
        _next_id += 1
        return _next_id


def _on_finished(call_id: int, result: object) -> None:
    on_finished, _on_failed_cb = _callbacks.pop(call_id, (None, None))
    if on_finished:
        on_finished(result)


def _on_failed(call_id: int, message: str) -> None:
    _on_finished_cb, on_failed = _callbacks.pop(call_id, (None, None))
    if on_failed:
        on_failed(message)


_dispatcher.finished.connect(_on_finished)
_dispatcher.failed.connect(_on_failed)


class _CallableRunnable(QRunnable):
    def __init__(self, fn: Callable[[], object], call_id: int):
        super().__init__()
        self.fn = fn
        self.call_id = call_id

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - background tasks must never crash the app
            logger.exception("Background task failed")
            _dispatcher.failed.emit(self.call_id, str(exc))
            return
        _dispatcher.finished.emit(self.call_id, result)


_POOL = QThreadPool.globalInstance()


def run_in_background(
    fn: Callable[[], object],
    on_finished: Callable[[object], None] | None = None,
    on_failed: Callable[[str], None] | None = None,
) -> None:
    call_id = _next_call_id()
    _callbacks[call_id] = (on_finished, on_failed)
    runnable = _CallableRunnable(fn, call_id)
    _POOL.start(runnable)
