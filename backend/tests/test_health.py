from pathlib import Path

from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_health_detailed(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "database" in data
    assert "timestamp" in data


def test_metrics_empty(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 0
    assert data["total_steps"] == 0
    assert data["total_cost"] == 0
    assert data["avg_steps_per_trace"] == 0


def test_metrics(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(
        Trace(
            agent_name="test",
            steps=[
                Step(
                    index=0,
                    step_type=StepType.LLM_CALL,
                    name="x",
                    input_data={},
                    output_data={},
                    cost=0.1,
                )
            ],
        )
    )
    client = TestClient(app)
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 1
    assert data["total_steps"] == 1
    assert data["total_cost"] == 0.1
