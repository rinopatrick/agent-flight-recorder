from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture()
def client(db: Database) -> TestClient:
    app = create_app(db)
    return TestClient(app)


def test_create_and_get_session(client: TestClient) -> None:
    resp = client.post("/api/sessions", json={"name": "test-session"})
    assert resp.status_code == 200
    session_id = resp.json()["id"]
    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-session"


def test_list_sessions(client: TestClient) -> None:
    client.post("/api/sessions", json={"name": "s1"})
    client.post("/api/sessions", json={"name": "s2"})
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_add_and_remove_trace_from_session(client: TestClient, db: Database) -> None:
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id
    resp = client.post("/api/sessions", json={"name": "test"})
    session_id = resp.json()["id"]
    resp = client.post(f"/api/sessions/{session_id}/traces/{trace_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/sessions/{session_id}")
    assert trace_id in resp.json()["trace_ids"]
    resp = client.delete(f"/api/sessions/{session_id}/traces/{trace_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/sessions/{session_id}")
    assert trace_id not in resp.json()["trace_ids"]
