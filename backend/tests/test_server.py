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


# --- Fork endpoint tests ---


def test_fork_trace(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=3)
    db.save_trace(trace)

    resp = client.post(
        f"/api/traces/{trace.id}/fork",
        json={
            "name": "my-fork",
            "fork_step_index": 2,
            "modifications": {"model": "claude-3"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "my-fork"
    assert data["parent_trace_id"] == trace.id
    assert data["fork_step_index"] == 2
    assert data["modifications"] == {"model": "claude-3"}
    assert "id" in data
    assert len(data["steps"]) == 2


def test_fork_trace_not_found(client: TestClient) -> None:
    resp = client.post(
        "/api/traces/nonexistent/fork",
        json={"name": "fork", "fork_step_index": 0, "modifications": {}},
    )
    assert resp.status_code == 404


def test_fork_invalid_step_index(client: TestClient, db: Database) -> None:
    trace = _make_trace("agent-a", n_steps=3)
    db.save_trace(trace)

    resp = client.post(
        f"/api/traces/{trace.id}/fork",
        json={"name": "bad-fork", "fork_step_index": 5, "modifications": {}},
    )
    assert resp.status_code == 400
    assert "fork_step_index" in resp.json()["detail"]


# --- Export/Import endpoint tests ---


def test_export_trace(client: TestClient, db: Database) -> None:
    trace = _make_trace("my-agent", n_steps=2)
    db.save_trace(trace)

    resp = client.get(f"/api/traces/{trace.id}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == trace.id
    assert data["agent_name"] == "my-agent"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["step_type"] == "llm_call"
    assert "created_at" in data
    assert "metadata" in data


def test_export_trace_not_found(client: TestClient) -> None:
    resp = client.get("/api/traces/nonexistent/export")
    assert resp.status_code == 404


def test_import_trace(client: TestClient, db: Database) -> None:
    trace = _make_trace("imported-agent", n_steps=3)
    export_data = {
        "id": trace.id,
        "agent_name": trace.agent_name,
        "steps": [
            {
                "index": s.index,
                "step_type": s.step_type.value,
                "name": s.name,
                "input_data": s.input_data,
                "output_data": s.output_data,
                "tokens_in": s.tokens_in,
                "tokens_out": s.tokens_out,
                "cost": s.cost,
                "duration_ms": s.duration_ms,
                "context_snapshot": s.context_snapshot,
                "error": s.error,
            }
            for s in trace.steps
        ],
        "created_at": trace.created_at.isoformat(),
        "metadata": trace.metadata,
    }

    resp = client.post("/api/traces/import", json={"data": export_data})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == trace.id
    assert data["agent_name"] == "imported-agent"
    assert len(data["steps"]) == 3

    stored = db.get_trace(trace.id)
    assert stored is not None
    assert stored.agent_name == "imported-agent"
    assert len(stored.steps) == 3


def test_import_trace_invalid_data(client: TestClient) -> None:
    resp = client.post("/api/traces/import", json={"data": {"bad": "data"}})
    assert resp.status_code == 400


def test_export_import_roundtrip(client: TestClient, db: Database, tmp_path: Path) -> None:
    original = _make_trace("roundtrip-agent", n_steps=2)
    db.save_trace(original)

    export_resp = client.get(f"/api/traces/{original.id}/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()

    db2 = Database(tmp_path / "test2.db")
    app2 = create_app(db2)
    client2 = TestClient(app2)

    import_resp = client2.post("/api/traces/import", json={"data": export_data})
    assert import_resp.status_code == 200
    data = import_resp.json()
    assert data["id"] == original.id
    assert data["agent_name"] == "roundtrip-agent"
    assert len(data["steps"]) == 2

    stored = db2.get_trace(original.id)
    assert stored is not None
    assert stored.agent_name == "roundtrip-agent"


# --- Generate test endpoint ---


def test_generate_test(client: TestClient, db: Database) -> None:
    trace = _make_trace("my-agent", n_steps=2)
    db.save_trace(trace)

    resp = client.post(f"/api/traces/{trace.id}/generate-test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == trace.id
    assert "test_code" in data
    assert isinstance(data["test_code"], str)
    assert "def test_agent_" in data["test_code"]


def test_generate_test_not_found(client: TestClient) -> None:
    resp = client.post("/api/traces/nonexistent/generate-test")
    assert resp.status_code == 404


def test_generate_test_contains_assertions(client: TestClient, db: Database) -> None:
    trace = _make_trace("chatbot", n_steps=3)
    db.save_trace(trace)

    resp = client.post(f"/api/traces/{trace.id}/generate-test")
    code = resp.json()["test_code"]
    assert "run_agent" in code
    assert "assert_model_used" in code
