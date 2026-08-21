"""Embedded local web server that mirrors the desktop app's live event
stream in a browser tab.

This is a read-only mirror, not a second app: it subscribes to the same
`app.core.events.bus` the desktop UI does, and pushes every event over a
WebSocket to whatever browser tab(s) are open. Nothing runs only in the
browser, and nothing the browser sends back changes any state — the
desktop app is the sole source of truth.

Threading: FastAPI/uvicorn need their own asyncio event loop, so the server
runs on a background thread with its own loop. Qt emits `bus` signals on
whatever thread it happens to be running on (pipeline worker threads or the
main thread); `_broadcast` is a plain signal-slot callback, so it always
runs on the connecting thread's context — we hop onto the server's asyncio
loop via `asyncio.run_coroutine_threadsafe` to actually send anything.
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.config.constants import APP_DISPLAY_NAME
from app.core.events import bus
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_PAGE_PATH = Path(__file__).parent / "static" / "index.html"
_ENGINEERING_FLOW_PATH = Path(__file__).parent / "static" / "engineering-flow.html"
_ALL_AI_ENGINEERING_PATH = Path(__file__).parent / "static" / "all-ai-engineering.html"
_MAX_HISTORY = 400


def _to_jsonable(payload: Any) -> Any:
    return asdict(payload) if is_dataclass(payload) else payload


class WebMirrorServer:
    """Owns the FastAPI app, the background uvicorn thread, and the set of
    connected WebSocket clients. One instance per process, started once
    from main.py."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._app = FastAPI(title=f"{APP_DISPLAY_NAME} — Live Mirror")
        self._clients: set[WebSocket] = set()
        self._history: list[dict] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._setup_routes()
        self._connect_bus()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _setup_routes(self) -> None:
        app = self._app

        @app.get("/", response_class=HTMLResponse)
        async def index() -> str:
            return _PAGE_PATH.read_text(encoding="utf-8")

        @app.get("/engineering-flow", response_class=HTMLResponse)
        async def engineering_flow() -> str:
            # A static, standalone explainer page — no bus/WebSocket wiring,
            # unlike everything else this server serves.
            return _ENGINEERING_FLOW_PATH.read_text(encoding="utf-8")

        @app.get("/all-ai-engineering", response_class=HTMLResponse)
        async def all_ai_engineering() -> str:
            # Same deal: a static reference page, no bus/WebSocket wiring.
            return _ALL_AI_ENGINEERING_PATH.read_text(encoding="utf-8")

        @app.get("/api/history")
        async def history() -> list[dict]:
            return self._history

        @app.websocket("/ws")
        async def ws(websocket: WebSocket) -> None:
            await websocket.accept()
            self._clients.add(websocket)
            try:
                for item in self._history:
                    await websocket.send_json(item)
                while True:
                    # Clients never need to send anything; this just blocks
                    # until the socket closes, which is how we detect that.
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                self._clients.discard(websocket)

    def _connect_bus(self) -> None:
        bus.step_updated.connect(lambda e: self._broadcast("step", e))
        bus.pipeline_updated.connect(lambda e: self._broadcast("pipeline", e))
        bus.graph_node_updated.connect(lambda e: self._broadcast("graph_node", e))
        bus.log_emitted.connect(lambda e: self._broadcast("log", e))
        bus.file_changed.connect(lambda e: self._broadcast("file_changed", e))
        bus.ollama_status_changed.connect(
            lambda available, models: self._broadcast("ollama_status", {"available": available, "models": models})
        )
        bus.clean_copy_ready.connect(
            lambda src, dst, n: self._broadcast(
                "clean_copy_ready", {"source_path": src, "destination_path": dst, "file_count": n}
            )
        )
        bus.memory_gate_decided.connect(
            lambda run_id, remembered, lesson: self._broadcast(
                "memory_gate", {"run_id": run_id, "remembered": remembered, "lesson": lesson}
            )
        )
        bus.prompt_activity.connect(lambda e: self._broadcast("prompt", e))

    def _broadcast(self, kind: str, payload: Any) -> None:
        message = {"type": kind, "payload": _to_jsonable(payload)}
        self._history.append(message)
        del self._history[:-_MAX_HISTORY]
        loop = self._loop
        if loop is None:
            return  # server thread hasn't finished starting yet; message is still in history for late joiners
        asyncio.run_coroutine_threadsafe(self._dispatch(message), loop)

    async def _dispatch(self, message: dict) -> None:
        dead = []
        for client in list(self._clients):
            try:
                await client.send_json(message)
            except Exception:  # noqa: BLE001 - a broken client must not affect the others
                dead.append(client)
        for client in dead:
            self._clients.discard(client)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_server, name="web-mirror-server", daemon=True)
        self._thread.start()
        self._started.wait(timeout=5)

    def _run_server(self) -> None:
        import uvicorn

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        config = uvicorn.Config(self._app, host=self.host, port=self.port, log_level="warning", loop="asyncio")
        server = uvicorn.Server(config)

        async def _serve() -> None:
            self._started.set()
            await server.serve()

        try:
            self._loop.run_until_complete(_serve())
        except Exception:  # noqa: BLE001 - the desktop app must keep running even if the mirror can't bind its port
            logger.exception("Web mirror server failed to start on %s:%s", self.host, self.port)
            self._started.set()
