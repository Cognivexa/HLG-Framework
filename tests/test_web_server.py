"""Tests for the embedded browser-mirror server (app.web.server). The
background uvicorn thread itself isn't started here (that's covered by a
live smoke test) — these exercise the FastAPI app in-process: the routes,
the bus-to-history bridge, and history replay on a fresh WebSocket
connection, which together are what a browser tab actually depends on."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.events import GraphNodeEvent, StepEvent, bus
from app.web.server import WebMirrorServer, _to_jsonable


def _server() -> WebMirrorServer:
    # Never call .start() here — that spawns a real uvicorn thread bound to
    # a real port, which is unnecessary for testing the ASGI app in-process
    # and would leak a listening socket per test.
    return WebMirrorServer(host="127.0.0.1", port=0)


def test_to_jsonable_converts_dataclass():
    event = StepEvent(pipeline="harness", run_id="r1", step_id="s1", step_name="Step", status="success")
    data = _to_jsonable(event)
    assert data["pipeline"] == "harness"
    assert data["step_id"] == "s1"


def test_to_jsonable_passes_through_plain_dict():
    assert _to_jsonable({"a": 1}) == {"a": 1}


def test_index_route_serves_html():
    server = _server()
    client = TestClient(server._app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "HLG Framework" in resp.text


def test_engineering_flow_route_serves_html():
    server = _server()
    client = TestClient(server._app)
    resp = client.get("/engineering-flow")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Era of AI Engineering" in resp.text


def test_history_route_starts_empty():
    server = _server()
    client = TestClient(server._app)
    assert client.get("/api/history").json() == []


def test_bus_step_updated_is_appended_to_history():
    server = _server()
    bus.step_updated.emit(
        StepEvent(pipeline="harness", run_id="r2", step_id="build_verification", step_name="Build", status="failed", detail="boom")
    )
    assert len(server._history) == 1
    message = server._history[0]
    assert message["type"] == "step"
    assert message["payload"]["step_id"] == "build_verification"
    assert message["payload"]["status"] == "failed"


def test_bus_graph_node_updated_is_appended_to_history():
    server = _server()
    bus.graph_node_updated.emit(
        GraphNodeEvent(run_id="r3", node_id="n1", node_label="Security", status="running", depends_on=("n0",))
    )
    message = server._history[-1]
    assert message["type"] == "graph_node"
    assert message["payload"]["node_id"] == "n1"
    # asdict() preserves the tuple as-is; it's only JSON-serialized (to a list) when actually sent over the wire.
    assert message["payload"]["depends_on"] == ("n0",)


def test_history_caps_at_max_entries():
    server = _server()
    for i in range(450):
        bus.log_emitted.emit({"level": "info", "message": f"line {i}"})
    assert len(server._history) <= 400


def test_websocket_replays_history_on_connect():
    server = _server()
    bus.step_updated.emit(
        StepEvent(pipeline="loop", run_id="r4", step_id="memory_gate", step_name="Memory gate", status="success", detail="Remembered.")
    )
    client = TestClient(server._app)
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
    assert first["type"] == "step"
    assert first["payload"]["run_id"] == "r4"
