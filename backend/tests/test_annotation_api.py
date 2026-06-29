from pathlib import Path

from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace
from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_create_and_get_annotations(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id
    client = TestClient(app)
    resp = client.post(f"/api/traces/{trace_id}/annotations", json={"content": "slow trace", "tags": ["perf"]})
    assert resp.status_code == 200
    ann_id = resp.json()["id"]
    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["content"] == "slow trace"


def test_delete_annotation(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id
    client = TestClient(app)
    resp = client.post(f"/api/traces/{trace_id}/annotations", json={"content": "note"})
    ann_id = resp.json()["id"]
    resp = client.delete(f"/api/annotations/{ann_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert len(resp.json()) == 0


def test_add_and_remove_tag(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id
    client = TestClient(app)
    resp = client.post(f"/api/traces/{trace_id}/annotations", json={"content": "note", "tags": ["initial"]})
    ann_id = resp.json()["id"]
    resp = client.post(f"/api/annotations/{ann_id}/tags/new-tag")
    assert resp.status_code == 200
    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert "new-tag" in resp.json()[0]["tags"]
    resp = client.delete(f"/api/annotations/{ann_id}/tags/initial")
    assert resp.status_code == 200
    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert "initial" not in resp.json()[0]["tags"]
