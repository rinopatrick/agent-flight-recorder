from pathlib import Path

from fastapi.testclient import TestClient

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_websocket_connect(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/api/ws/traces") as ws:
        assert ws is not None


def test_websocket_receives_trace_event(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/api/ws/traces") as ws:
        client.post(
            "/api/traces/import",
            json={
                "data": {
                    "id": "ws-test",
                    "agent_name": "ws-agent",
                    "steps": [],
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
        )
        data = ws.receive_json()
        assert data["event_type"] == "trace_saved"
        assert data["trace_id"] == "ws-test"
