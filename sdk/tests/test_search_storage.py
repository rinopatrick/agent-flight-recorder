from datetime import datetime, timezone
from pathlib import Path

from flight_recorder.models import Step, StepType, Trace, TraceFilter
from flight_recorder.storage import TraceStorage


def _make_trace(agent: str, cost: float = 0.0, error: bool = False) -> Trace:
    step = Step(index=0, step_type=StepType.LLM_CALL, name="test", input_data={}, output_data={}, cost=cost, error="fail" if error else None)
    return Trace(agent_name=agent, steps=[step], created_at=datetime(2026, 6, 15, tzinfo=timezone.utc))


def test_search_by_agent_name(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("agent-a"))
    store.save_trace(_make_trace("agent-b"))
    store.save_trace(_make_trace("agent-a"))
    result = store.search_traces(TraceFilter(agent_name="agent-a"))
    assert len(result) == 2
    assert all(t.agent_name == "agent-a" for t in result)


def test_search_by_cost_range(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("a", cost=0.001))
    store.save_trace(_make_trace("b", cost=0.5))
    store.save_trace(_make_trace("c", cost=5.0))
    result = store.search_traces(TraceFilter(min_cost=0.01, max_cost=1.0))
    assert len(result) == 1
    assert result[0].agent_name == "b"


def test_search_by_has_error(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("a", error=False))
    store.save_trace(_make_trace("b", error=True))
    result = store.search_traces(TraceFilter(has_error=True))
    assert len(result) == 1
    assert result[0].agent_name == "b"


def test_search_by_step_type(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    t1 = Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})])
    t2 = Trace(agent_name="b", steps=[Step(index=0, step_type=StepType.TOOL_CALL, name="y", input_data={}, output_data={})])
    store.save_trace(t1)
    store.save_trace(t2)
    result = store.search_traces(TraceFilter(step_type=StepType.TOOL_CALL))
    assert len(result) == 1
    assert result[0].agent_name == "b"


def test_search_no_filter_returns_all(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("a"))
    store.save_trace(_make_trace("b"))
    result = store.search_traces(TraceFilter())
    assert len(result) == 2
