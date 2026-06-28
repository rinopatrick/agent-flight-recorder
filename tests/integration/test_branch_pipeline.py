"""Integration test: branch pipeline from recording through fork to comparison."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flight_recorder import get_last_trace, record
from flight_recorder_backend import create_app
from flight_recorder_backend.db import Database
from flight_recorder_backend.replay import ReplayEngine


@record
def _traced_agent():
    record.llm_call(
        name="gpt-4",
        input_data={"prompt": "summarize this"},
        output_data={"summary": "a short summary"},
        tokens_in=100,
        tokens_out=50,
        cost=0.005,
        duration_ms=200.0,
    )
    record.tool_call(
        name="search",
        input_data={"query": "branching"},
        output_data={"results": ["x", "y", "z"]},
        duration_ms=80.0,
    )
    record.llm_call(
        name="gpt-4",
        input_data={"prompt": "refine"},
        output_data={"refined": "better summary"},
        tokens_in=80,
        tokens_out=40,
        cost=0.004,
        duration_ms=180.0,
    )
    return "complete"


def test_branch_pipeline(tmp_path: Path):
    _traced_agent()
    trace = get_last_trace()
    assert trace is not None
    assert len(trace.steps) == 4

    db = Database(tmp_path / "test.db")
    db.save_trace(trace)

    stored = db.get_trace(trace.id)
    assert stored is not None
    assert len(stored.steps) == 4

    engine = ReplayEngine()
    branch = engine.create_branch_from_trace(
        trace=stored,
        fork_step_index=2,
        name="model-swap",
        modifications={"model": "claude-3-opus"},
    )

    assert branch.parent_trace_id == stored.id
    assert branch.fork_step_index == 2
    assert branch.modifications == {"model": "claude-3-opus"}
    assert len(branch.steps) == 2
    assert branch.steps[0].name == "claude-3-opus"

    db.branches.save_branch(branch)
    stored_branch = db.branches.get_branch(branch.id)
    assert stored_branch is not None
    assert stored_branch.name == "model-swap"
    assert len(stored_branch.steps) == 2

    trace_cost = stored.total_cost()
    branch_cost = stored_branch.total_cost()
    trace_dur = stored.total_duration_ms()
    branch_dur = stored_branch.total_duration_ms()

    assert trace_cost == pytest.approx(0.009)
    assert branch_cost == pytest.approx(0.005)
    assert trace_cost > branch_cost
    assert trace_dur > branch_dur

    listed = db.branches.list_branches_for_trace(stored.id)
    assert len(listed) == 1
    assert listed[0].id == branch.id

    all_branches = db.branches.list_branches()
    assert len(all_branches) >= 1
    assert any(b.id == branch.id for b in all_branches)


def test_branch_pipeline_via_api(tmp_path: Path):
    _traced_agent()
    trace = get_last_trace()
    assert trace is not None

    db = Database(tmp_path / "test.db")
    db.save_trace(trace)
    app = create_app(db)
    client = TestClient(app)

    resp = client.get(f"/api/traces/{trace.id}")
    assert resp.status_code == 200

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
    assert len(fork_data["steps"]) == 1
    assert fork_data["steps"][0]["name"] == "claude-3-sonnet"

    branch_id = fork_data["id"]

    resp = client.get(f"/api/traces/{trace.id}/branches")
    assert resp.status_code == 200
    branches = resp.json()
    assert len(branches) == 1
    assert branches[0]["id"] == branch_id

    resp = client.get(f"/api/branches/{branch_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["name"] == "api-fork"
    assert detail["fork_step_index"] == 1

    resp = client.delete(f"/api/branches/{branch_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/branches/{branch_id}")
    assert resp.status_code == 404
