from datetime import datetime, timezone

from flight_recorder.models import StepType, TraceFilter


def test_trace_filter_creation():
    f = TraceFilter(
        agent_name="test-agent",
        created_after=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_before=datetime(2026, 12, 31, tzinfo=timezone.utc),
        min_cost=0.001,
        max_cost=1.0,
        step_type=StepType.LLM_CALL,
        has_error=True,
    )
    assert f.agent_name == "test-agent"
    assert f.min_cost == 0.001
    assert f.max_cost == 1.0
    assert f.step_type == StepType.LLM_CALL
    assert f.has_error is True


def test_trace_filter_defaults():
    f = TraceFilter()
    assert f.agent_name is None
    assert f.created_after is None
    assert f.min_cost is None
    assert f.max_cost is None
    assert f.step_type is None
    assert f.has_error is None
