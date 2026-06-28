from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace, TraceStorage

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture()
def client(db: Database) -> TestClient:
    app = create_app(db)
    return TestClient(app)


def _make_trace(name: str = "test-agent", n_steps: int = 1) -> Trace:
    steps = [
        Step(
            index=i,
            step_type=StepType.LLM_CALL,
            name=f"step-{i}",
            input_data={"prompt": "hello"},
            output_data={"response": "world"},
            tokens_in=10,
            tokens_out=5,
            cost=0.001,
            duration_ms=100.0,
        )
        for i in range(n_steps)
    ]
    return Trace(agent_name=name, steps=steps)


def test_list_traces_empty(client: TestClient) -> None:
    resp = client.get("/api/traces")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_traces_with_data(client: TestClient, db: Database) -> None:
    db.save_trace(_make_trace("agent-a", n_steps=2))
    db.save_trace(_make_trace("agent-b", n_steps=1))

    resp = client.get("/api/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for item in data:
        assert "id" in item
        assert "agent_name" in item
        assert "step_count" in item
        assert "created_at" in item
        assert "total_cost" in item


def test_get_trace(client: TestClient, db: Database) -> None:
    trace = _make_trace("my-agent", n_steps=3)
    db.save_trace(trace)

    resp = client.get(f"/api/traces/{trace.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == trace.id
    assert data["agent_name"] == "my-agent"
    assert len(data["steps"]) == 3
    assert data["steps"][0]["name"] == "step-0"
    assert data["steps"][0]["step_type"] == "llm_call"


def test_get_trace_not_found(client: TestClient) -> None:
    resp = client.get("/api/traces/nonexistent")
    assert resp.status_code == 404


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
