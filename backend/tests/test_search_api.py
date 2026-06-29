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


def test_search_by_agent_name(client: TestClient, db: Database) -> None:
    db.save_trace(
        Trace(
            agent_name="agent-a",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})],
        )
    )
    db.save_trace(
        Trace(
            agent_name="agent-b",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="y", input_data={}, output_data={})],
        )
    )

    resp = client.get("/api/traces/search", params={"agent_name": "agent-a"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "agent-a"


def test_search_by_cost_range(client: TestClient, db: Database) -> None:
    db.save_trace(
        Trace(
            agent_name="cheap",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={}, cost=0.001)],
        )
    )
    db.save_trace(
        Trace(
            agent_name="expensive",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="y", input_data={}, output_data={}, cost=5.0)],
        )
    )

    resp = client.get("/api/traces/search", params={"min_cost": "1.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "expensive"


def test_search_with_pagination(client: TestClient, db: Database) -> None:
    for i in range(5):
        db.save_trace(Trace(agent_name=f"agent-{i}", steps=[]))

    resp = client.get("/api/traces/search", params={"limit": "2", "offset": "0"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_search_no_results(client: TestClient, db: Database) -> None:
    db.save_trace(Trace(agent_name="agent-a", steps=[]))

    resp = client.get("/api/traces/search", params={"agent_name": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_response_shape(client: TestClient, db: Database) -> None:
    db.save_trace(
        Trace(
            agent_name="my-agent",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={}, cost=0.5)],
        )
    )

    resp = client.get("/api/traces/search")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert "id" in item
    assert "agent_name" in item
    assert "step_count" in item
    assert "created_at" in item
    assert "total_cost" in item


def test_search_by_step_type(client: TestClient, db: Database) -> None:
    db.save_trace(
        Trace(
            agent_name="a",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})],
        )
    )
    db.save_trace(
        Trace(
            agent_name="b",
            steps=[Step(index=0, step_type=StepType.TOOL_CALL, name="y", input_data={}, output_data={})],
        )
    )

    resp = client.get("/api/traces/search", params={"step_type": "tool_call"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "b"


def test_search_by_has_error(client: TestClient, db: Database) -> None:
    db.save_trace(
        Trace(
            agent_name="ok",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})],
        )
    )
    db.save_trace(
        Trace(
            agent_name="broken",
            steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={}, error="oops")],
        )
    )

    resp = client.get("/api/traces/search", params={"has_error": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "broken"
