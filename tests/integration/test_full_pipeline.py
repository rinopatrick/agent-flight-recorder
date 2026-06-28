"""Integration test: full pipeline from SDK recording through storage to API."""

from pathlib import Path

from fastapi.testclient import TestClient

from flight_recorder import StepType, get_last_trace, record
from flight_recorder_backend import create_app
from flight_recorder_backend.db import Database


@record
def _sample_agent():
    record.llm_call(
        name="chat",
        input_data={"prompt": "hello"},
        output_data={"response": "hi there"},
        tokens_in=10,
        tokens_out=5,
        cost=0.002,
        duration_ms=150.0,
    )
    record.tool_call(
        name="search",
        input_data={"query": "test"},
        output_data={"results": ["a", "b"]},
        duration_ms=50.0,
    )
    return "done"


def test_full_pipeline(tmp_path: Path):
    _sample_agent()
    trace = get_last_trace()
    assert trace is not None

    db = Database(tmp_path / "test.db")
    db.save_trace(trace)

    app = create_app(db)
    client = TestClient(app)

    resp = client.get("/api/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == trace.id
    assert data[0]["agent_name"] == "_sample_agent"
    assert data[0]["step_count"] == 3

    resp = client.get(f"/api/traces/{trace.id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == trace.id
    assert len(detail["steps"]) == 3
    assert detail["steps"][0]["step_type"] == StepType.LLM_CALL.value
    assert detail["steps"][0]["tokens_in"] == 10
    assert detail["steps"][1]["step_type"] == StepType.TOOL_CALL.value
    assert detail["steps"][2]["step_type"] == StepType.OUTPUT.value

    assert data[0]["total_cost"] == 0.002
