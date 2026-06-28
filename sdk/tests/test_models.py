from datetime import datetime, timezone

import pytest

from flight_recorder.models import Step, StepType, Trace


def test_step_creation():
    step = Step(
        index=0,
        step_type=StepType.LLM_CALL,
        name="generate_text",
        input_data={"prompt": "Hello"},
        output_data={"response": "Hi there"},
        tokens_in=10,
        tokens_out=5,
        cost=0.001,
        duration_ms=150.0,
    )
    assert step.index == 0
    assert step.step_type == StepType.LLM_CALL
    assert step.name == "generate_text"
    assert step.input_data == {"prompt": "Hello"}
    assert step.output_data == {"response": "Hi there"}
    assert step.tokens_in == 10
    assert step.tokens_out == 5
    assert step.cost == 0.001
    assert step.duration_ms == 150.0
    assert step.context_snapshot is None
    assert step.error is None


def test_trace_creation():
    step = Step(
        index=0,
        step_type=StepType.TOOL_CALL,
        name="search",
        input_data={"q": "test"},
        output_data={"results": []},
        cost=0.0,
        duration_ms=50.0,
    )
    trace = Trace(agent_name="my_agent", steps=[step])
    assert trace.id is not None
    assert len(trace.id) == 12
    assert trace.agent_name == "my_agent"
    assert len(trace.steps) == 1
    assert trace.steps[0].name == "search"
    assert isinstance(trace.created_at, datetime)
    assert trace.created_at.tzinfo is not None
    assert trace.metadata == {}


def test_trace_total_cost():
    steps = [
        Step(
            index=i,
            step_type=StepType.LLM_CALL,
            name=f"step_{i}",
            input_data={},
            output_data={},
            cost=c,
            duration_ms=d,
        )
        for i, (c, d) in enumerate([(0.005, 100.0), (0.003, 200.0), (0.002, 50.0)])
    ]
    trace = Trace(agent_name="cost_agent", steps=steps)
    assert trace.total_cost() == pytest.approx(0.01)
    assert trace.total_duration_ms() == pytest.approx(350.0)


def test_step_context_snapshot():
    snapshot = {"conversation": [{"role": "user", "content": "hi"}], "token_count": 42}
    step = Step(
        index=0,
        step_type=StepType.REASONING,
        name="think",
        input_data={},
        output_data={},
        context_snapshot=snapshot,
        cost=0.0,
        duration_ms=10.0,
    )
    assert step.context_snapshot == snapshot
    assert step.context_snapshot["token_count"] == 42
