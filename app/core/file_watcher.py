"""Recursive project file watcher with per-file debounce.

Only changed files are queued for pipeline processing (via FileChangeEvent on
the bus) — the watcher never re-scans a whole project on every save. Beyond
plain create/modify (which trigger analysis, same as rename), this also
surfaces delete, git-HEAD, and build-output activity for the Dashboard's
live feed — see ANALYSIS_CHANGE_TYPES for exactly which kinds
PipelineController acts on versus which are purely informational.
"""
from __future__ import annotations

import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config.constants import IGNORED_DIR_NAMES, SUPPORTED_EXTENSIONS
from app.core.events import FileChangeEvent, bus
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_BUILD_OUTPUT_DIR_NAMES = {"dist", "build", "__pycache__"}
_BUILD_OUTPUT_EXTENSIONS = {".whl", ".egg", ".exe", ".dll", ".so", ".pyd", ".pyc"}

# Change types that should trigger a Harness run (see PipelineController).
# "deleted"/"git_changed"/"build_output_changed" are informational-only —
# there's nothing meaningful to analyze in a file that no longer exists, and
# git/build activity isn't itself a source-code change.
ANALYSIS_CHANGE_TYPES = {"created", "modified", "renamed"}


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def _is_supported(path: Path) -> bool:
    return path.suffix in SUPPORTED_EXTENSIONS


def _is_git_head(path: Path) -> bool:
    return path.name == "HEAD" and path.parent.name == ".git"


def _is_build_output(path: Path) -> bool:
    if path.suffix in _BUILD_OUTPUT_EXTENSIONS:
        return True
    return any(part in _BUILD_OUTPUT_DIR_NAMES for part in path.parts)


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(self, project_path: str, debounce_seconds: float, on_change):
        super().__init__()
        self.project_path = project_path
        self.debounce_seconds = debounce_seconds
        self.on_change = on_change
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _classify(self, path: Path, default_type: str) -> str | None:
        """Returns the change_type to actually emit, or None to drop the event."""
        if _is_git_head(path):
            return "git_changed"
        if _is_build_output(path):
            return "build_output_changed"
        if _is_ignored(path) or not _is_supported(path):
            return None
        return default_type

    def _schedule(self, path_str: str, default_type: str) -> None:
        change_type = self._classify(Path(path_str), default_type)
        if change_type is None:
            return
        key = f"{path_str}:{change_type}"
        with self._lock:
            existing = self._timers.get(key)
            if existing:
                existing.cancel()
            timer = threading.Timer(self.debounce_seconds, self._fire, args=(path_str, change_type, key))
            timer.daemon = True
            self._timers[key] = timer
            timer.start()

    def _fire(self, path_str: str, change_type: str, key: str) -> None:
        with self._lock:
            self._timers.pop(key, None)
        event = FileChangeEvent(project_path=self.project_path, file_path=path_str, change_type=change_type)
        logger.info("File %s: %s", change_type, path_str)
        self.on_change(event)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            # The old path is effectively a delete; the new path is treated
            # like a fresh change so it gets analyzed (covers both true
            # renames and moves across folders within the watched tree).
            self._schedule(event.dest_path, "renamed")


class ProjectWatcher:
    """Watches one project folder recursively and emits debounced FileChangeEvents."""

    def __init__(self, project_path: str, debounce_seconds: float = 1.5):
        self.project_path = project_path
        self.debounce_seconds = debounce_seconds
        self._observer: Observer | None = None

    def start(self) -> None:
        if self._observer is not None:
            return
        if not Path(self.project_path).is_dir():
            # A monitored project can vanish (deleted, moved, a disconnected
            # network/USB drive) between app runs. Watchdog's native Windows
            # handle lookup raises straight out of observer.start() for a
            # missing path — uncaught, that takes the whole app down before
            # its window ever appears. Skip it instead; the project stays
            # configured and just isn't actively watched until it's back.
            logger.warning("Project path no longer exists, skipping watch: %s", self.project_path)
            return
        handler = _DebouncedHandler(self.project_path, self.debounce_seconds, self._emit)
        observer = Observer()
        observer.schedule(handler, self.project_path, recursive=True)
        try:
            observer.start()
        except OSError as exc:
            logger.warning("Could not start watching %s: %s", self.project_path, exc)
            return
        self._observer = observer
        logger.info("Started watching %s", self.project_path)

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("Stopped watching %s", self.project_path)

    @staticmethod
    def _emit(event: FileChangeEvent) -> None:
        bus.file_changed.emit(event)


class WatcherManager:
    """Owns one ProjectWatcher per monitored project; reconciles on settings changes."""

    def __init__(self):
        self._watchers: dict[str, ProjectWatcher] = {}

    def set_projects(self, paths: list[str], debounce_seconds: float = 1.5) -> None:
        current = set(self._watchers.keys())
        desired = set(paths)
        for stale in current - desired:
            self._watchers.pop(stale).stop()
        for new_path in desired - current:
            watcher = ProjectWatcher(new_path, debounce_seconds)
            watcher.start()
            self._watchers[new_path] = watcher

    def stop_all(self) -> None:
        for watcher in self._watchers.values():
            watcher.stop()
        self._watchers.clear()
