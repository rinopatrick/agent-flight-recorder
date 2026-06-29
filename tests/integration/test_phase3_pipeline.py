"""Integration test: full Phase 3 pipeline — record, store, export/import, fork, generate test, API round-trip."""

import ast
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flight_recorder import (
    clear_last_trace,
    export_trace,
    get_last_trace,
    import_trace,
    record,
)
from flight_recorder.models import StepType
from flight_recorder_backend import create_app
from flight_recorder_backend.db import Database
from flight_recorder_backend.test_generator import TestGenerator


@record
def _pipeline_agent():
    record.llm_call(
        name="gpt-4",
        input_data={"prompt": "plan the task"},
        output_data={"plan": "do A then B"},
        tokens_in=120,
        tokens_out=60,
        cost=0.006,
        duration_ms=250.0,
    )
    record.tool_call(
        name="read_file",
        input_data={"path": "src/main.py"},
        output_data={"content": "print('hello')"},
        duration_ms=30.0,
    )
    record.llm_call(
        name="gpt-4",
        input_data={"prompt": "generate code"},
        output_data={"code": "print('world')"},
        tokens_in=200,
        tokens_out=100,
        cost=0.010,
        duration_ms=300.0,
    )
    return "pipeline complete"


@pytest.fixture()
def recorded_trace():
    clear_last_trace()
    _pipeline_agent()
    trace = get_last_trace()
    assert trace is not None
    assert len(trace.steps) == 4
    return trace


@pytest.fixture()
def db(tmp_path: Path):
    return Database(tmp_path / "phase3.db")


@pytest.fixture()
def saved_trace(recorded_trace, db):
    db.save_trace(recorded_trace)
    return recorded_trace


@pytest.fixture()
def client(db):
    return TestClient(create_app(db))


def test_record_trace(recorded_trace):
    assert recorded_trace.agent_name == "_pipeline_agent"
    assert recorded_trace.steps[0].step_type == StepType.LLM_CALL
    assert recorded_trace.steps[0].name == "gpt-4"
    assert recorded_trace.steps[0].tokens_in == 120
    assert recorded_trace.steps[1].step_type == StepType.TOOL_CALL
    assert recorded_trace.steps[1].name == "read_file"
    assert recorded_trace.steps[2].step_type == StepType.LLM_CALL
    assert recorded_trace.steps[3].step_type == StepType.OUTPUT


def test_save_and_load_from_db(recorded_trace, db):
    db.save_trace(recorded_trace)
    loaded = db.get_trace(recorded_trace.id)
    assert loaded is not None
    assert loaded.id == recorded_trace.id
    assert loaded.agent_name == "_pipeline_agent"
    assert len(loaded.steps) == 4
    assert loaded.steps[0].step_type == StepType.LLM_CALL
    assert loaded.steps[1].step_type == StepType.TOOL_CALL
    assert loaded.steps[0].tokens_in == 120


def test_export_import_roundtrip(recorded_trace):
    exported = export_trace(recorded_trace)
    assert isinstance(exported, dict)
    assert exported["id"] == recorded_trace.id
    assert exported["agent_name"] == "_pipeline_agent"
    assert len(exported["steps"]) == 4
    assert exported["steps"][0]["step_type"] == "llm_call"
    assert exported["steps"][1]["step_type"] == "tool_call"

    imported = import_trace(exported)
    assert imported.id == recorded_trace.id
    assert imported.agent_name == recorded_trace.agent_name
    assert len(imported.steps) == 4
    assert imported.steps[0].step_type == StepType.LLM_CALL
    assert imported.steps[0].name == "gpt-4"
    assert imported.steps[0].tokens_in == 120
    assert imported.steps[1].step_type == StepType.TOOL_CALL
    assert imported.steps[1].name == "read_file"
    assert imported.total_cost() == pytest.approx(recorded_trace.total_cost())
    assert imported.total_duration_ms() == pytest.approx(
        recorded_trace.total_duration_ms()
    )


def test_fork_imported_trace(recorded_trace):
    from flight_recorder_backend.replay import ReplayEngine

    exported = export_trace(recorded_trace)
    imported = import_trace(exported)

    engine = ReplayEngine()
    branch = engine.create_branch_from_trace(
        trace=imported,
        fork_step_index=2,
        name="phase3-fork",
        modifications={"model": "claude-3-opus"},
    )
    assert branch.parent_trace_id == imported.id
    assert branch.fork_step_index == 2
    assert branch.name == "phase3-fork"
    assert branch.modifications == {"model": "claude-3-opus"}
    assert len(branch.steps) == 2
    assert branch.steps[0].name == "claude-3-opus"


def test_generate_test_code(recorded_trace, db):
    db.save_trace(recorded_trace)
    generator = TestGenerator()
    test_code = generator.generate_test(recorded_trace)

    assert isinstance(test_code, str)
    assert len(test_code) > 0

    ast.parse(test_code)

    assert "def test_agent_" in test_code
    assert "run_agent(" in test_code
    assert 'assert_tool_called(result, "read_file"' in test_code
    assert 'assert_model_used(result, "gpt-4")' in test_code
    assert "assert_cost(result, max_cost=" in test_code
    assert "assert_latency(result, max_ms=" in test_code


def test_export_import_via_api(saved_trace, client):
    resp = client.get(f"/api/traces/{saved_trace.id}/export")
    assert resp.status_code == 200
    exported = resp.json()
    assert exported["id"] == saved_trace.id
    assert len(exported["steps"]) == 4

    reimport_data = {**exported, "id": uuid.uuid4().hex[:12]}

    resp = client.post("/api/traces/import", json={"data": reimport_data})
    assert resp.status_code == 200
    imported_data = resp.json()
    assert imported_data["id"] == reimport_data["id"]
    assert imported_data["agent_name"] == "_pipeline_agent"
    assert len(imported_data["steps"]) == 4

    resp = client.get("/api/traces")
    assert resp.status_code == 200
    traces = resp.json()
    ids = [t["id"] for t in traces]
    assert saved_trace.id in ids
    assert reimport_data["id"] in ids


def test_full_phase3_pipeline(tmp_path: Path):
    clear_last_trace()
    _pipeline_agent()
    trace = get_last_trace()
    assert trace is not None

    db = Database(tmp_path / "full.db")
    db.save_trace(trace)
    stored = db.get_trace(trace.id)
    assert stored is not None
    assert len(stored.steps) == 4

    exported = export_trace(stored)
    assert exported["id"] == trace.id
    assert len(exported["steps"]) == 4

    imported = import_trace(exported)
    assert imported.id == trace.id
    assert imported.total_cost() == pytest.approx(trace.total_cost())

    from flight_recorder_backend.replay import ReplayEngine

    engine = ReplayEngine()
    branch = engine.create_branch_from_trace(
        trace=imported,
        fork_step_index=2,
        name="full-fork",
        modifications={"model": "claude-3-opus"},
    )
    assert branch.parent_trace_id == imported.id
    assert len(branch.steps) == 2
    assert branch.steps[0].name == "claude-3-opus"

    generator = TestGenerator()
    test_code = generator.generate_test(trace)
    ast.parse(test_code)
    assert "assert_tool_called" in test_code
    assert "assert_model_used" in test_code
    assert "assert_cost" in test_code
    assert "assert_latency" in test_code

    app = create_app(db)
    client = TestClient(app)

    resp = client.get("/api/traces")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get(f"/api/traces/{trace.id}/export")
    assert resp.status_code == 200
    api_exported = resp.json()
    assert api_exported["id"] == trace.id

    reimport = {**api_exported, "id": uuid.uuid4().hex[:12]}
    resp = client.post("/api/traces/import", json={"data": reimport})
    assert resp.status_code == 200
    assert resp.json()["id"] == reimport["id"]

    resp = client.post(
        f"/api/traces/{trace.id}/generate-test",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "test_code" in body
    assert "assert_tool_called" in body["test_code"]

    resp = client.post(
        f"/api/traces/{trace.id}/fork",
        json={
            "name": "api-fork",
            "fork_step_index": 1,
            "modifications": {"model": "claude-3-sonnet"},
        },
    )
    assert resp.status_code == 200
    fork_data = resp.json()
    assert fork_data["name"] == "api-fork"
    assert fork_data["parent_trace_id"] == trace.id
