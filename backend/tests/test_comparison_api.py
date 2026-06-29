from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_compare_traces(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(id="aaa", agent_name="x", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="s", input_data={}, output_data={}, cost=0.1, duration_ms=100)]))
    db.save_trace(Trace(id="bbb", agent_name="x", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="s", input_data={}, output_data={}, cost=0.2, duration_ms=200)]))
    client = TestClient(app)
    resp = client.get("/api/traces/compare", params={"a": "aaa", "b": "bbb"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cost_diff"] == pytest.approx(0.1)
    assert data["duration_diff"] == pytest.approx(100.0)
    assert data["step_count_diff"] == 0


def test_compare_traces_not_found(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/traces/compare", params={"a": "nonexistent", "b": "also-not"})
    assert resp.status_code == 404
