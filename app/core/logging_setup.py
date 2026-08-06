"""Rotating file logging plus an in-memory ring buffer feeding the Log Viewer widget."""
from __future__ import annotations

import logging
import logging.handlers
from collections import deque

from app.config.settings import LOG_DIR
from app.core.events import LogEvent, bus

LOG_RING_BUFFER: deque[LogEvent] = deque(maxlen=2000)


class _BusHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        event = LogEvent(level=record.levelname, message=self.format(record))
        LOG_RING_BUFFER.append(event)
        bus.log_emitted.emit(event)


_CONFIGURED = False


def configure_logging() -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger("harness")
    if _CONFIGURED:
        return logger
    _CONFIGURED = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)

    file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    bus_handler = _BusHandler()
    bus_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(bus_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(file_fmt)
    logger.addHandler(stream_handler)

    return logger


def get_logger(name: str = "harness") -> logging.Logger:
    """Returns a child of the configured "harness" logger so handlers propagate."""
    if name == "harness":
        return logging.getLogger("harness")
    return logging.getLogger(f"harness.{name}")
