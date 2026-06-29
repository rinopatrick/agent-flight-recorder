from pathlib import Path

import pytest

from flight_recorder.models import Step, StepType, Trace
from flight_recorder.storage import TraceStorage


def _make_trace(agent_name: str = "test_agent", n_steps: int = 1) -> Trace:
    steps = [
        Step(
            index=i,
            step_type=StepType.LLM_CALL,
            name=f"step_{i}",
            input_data={"prompt": f"hello {i}"},
            output_data={"response": f"world {i}"},
            tokens_in=10 + i,
            tokens_out=5 + i,
            cost=0.001 * (i + 1),
            duration_ms=100.0 * (i + 1),
            context_snapshot={"turn": i} if i == 0 else None,
            error="oops" if i == 2 else None,
        )
        for i in range(n_steps)
    ]
    return Trace(agent_name=agent_name, steps=steps)


def test_save_and_get_trace(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = TraceStorage(db)
    trace = _make_trace("agent_a", n_steps=2)
    storage.save_trace(trace)

    loaded = storage.get_trace(trace.id)
    assert loaded is not None
    assert loaded.id == trace.id
    assert loaded.agent_name == "agent_a"
    assert len(loaded.steps) == 2
    assert loaded.steps[0].name == "step_0"
    assert loaded.steps[0].step_type == StepType.LLM_CALL
    assert loaded.steps[0].input_data == {"prompt": "hello 0"}
    assert loaded.steps[0].tokens_in == 10
    assert loaded.steps[0].cost == pytest.approx(0.001)
    assert loaded.steps[1].index == 1
    assert loaded.created_at is not None
    assert loaded.metadata == trace.metadata


def test_list_traces(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = TraceStorage(db)
    storage.save_trace(_make_trace("a"))
    storage.save_trace(_make_trace("b"))

    traces = storage.list_traces()
    assert len(traces) == 2
    assert {t.agent_name for t in traces} == {"a", "b"}


def test_list_traces_with_limit(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = TraceStorage(db)
    for i in range(5):
        storage.save_trace(_make_trace(f"agent_{i}"))

    traces = storage.list_traces(limit=2)
    assert len(traces) == 2


def test_delete_trace(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = TraceStorage(db)
    trace = _make_trace()
    storage.save_trace(trace)

    storage.delete_trace(trace.id)
    assert storage.get_trace(trace.id) is None


def test_get_nonexistent_trace(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = TraceStorage(db)
    assert storage.get_trace("nonexistent") is None
