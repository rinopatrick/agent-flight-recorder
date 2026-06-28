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


# --- Branch API tests ---


def test_create_branch(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=3)
    db.save_trace(trace)

    resp = client.post(
        f"/api/traces/{trace.id}/branches",
        json={
            "name": "my-branch",
            "fork_step_index": 1,
            "modifications": {"temperature": 0.9},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "my-branch"
    assert data["parent_trace_id"] == trace.id
    assert data["fork_step_index"] == 1
    assert data["modifications"] == {"temperature": 0.9}
    assert "id" in data


def test_create_branch_trace_not_found(client: TestClient) -> None:
    resp = client.post(
        "/api/traces/nonexistent/branches",
        json={
            "name": "my-branch",
            "fork_step_index": 0,
            "modifications": {},
        },
    )
    assert resp.status_code == 404


def test_list_branches_for_trace(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=3)
    db.save_trace(trace)

    client.post(
        f"/api/traces/{trace.id}/branches",
        json={"name": "branch-1", "fork_step_index": 0, "modifications": {}},
    )
    client.post(
        f"/api/traces/{trace.id}/branches",
        json={"name": "branch-2", "fork_step_index": 1, "modifications": {}},
    )

    resp = client.get(f"/api/traces/{trace.id}/branches")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {b["name"] for b in data}
    assert names == {"branch-1", "branch-2"}


def test_list_branches_empty(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=1)
    db.save_trace(trace)

    resp = client.get(f"/api/traces/{trace.id}/branches")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_branch(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=3)
    db.save_trace(trace)

    create_resp = client.post(
        f"/api/traces/{trace.id}/branches",
        json={"name": "detail-branch", "fork_step_index": 2, "modifications": {"x": 1}},
    )
    branch_id = create_resp.json()["id"]

    resp = client.get(f"/api/branches/{branch_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == branch_id
    assert data["name"] == "detail-branch"
    assert data["parent_trace_id"] == trace.id
    assert data["fork_step_index"] == 2
    assert data["modifications"] == {"x": 1}


def test_get_branch_not_found(client: TestClient) -> None:
    resp = client.get("/api/branches/nonexistent")
    assert resp.status_code == 404


def test_delete_branch(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=2)
    db.save_trace(trace)

    create_resp = client.post(
        f"/api/traces/{trace.id}/branches",
        json={"name": "to-delete", "fork_step_index": 0, "modifications": {}},
    )
    branch_id = create_resp.json()["id"]

    resp = client.delete(f"/api/branches/{branch_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/branches/{branch_id}")
    assert resp.status_code == 404


def test_delete_branch_not_found(client: TestClient) -> None:
    resp = client.delete("/api/branches/nonexistent")
    assert resp.status_code == 404
