import pytest
from flight_recorder.models import Step, StepType, Trace, TraceComparison


def test_comparison_creation():
    a = Trace(id="a", agent_name="x", steps=[
        Step(index=0, step_type=StepType.LLM_CALL, name="s1", input_data={}, output_data={}, cost=0.1, duration_ms=100),
    ])
    b = Trace(id="b", agent_name="x", steps=[
        Step(index=0, step_type=StepType.LLM_CALL, name="s1", input_data={}, output_data={}, cost=0.2, duration_ms=200),
        Step(index=1, step_type=StepType.TOOL_CALL, name="s2", input_data={}, output_data={}, cost=0.05, duration_ms=50),
    ])
    comp = TraceComparison(trace_a=a, trace_b=b)
    assert comp.cost_diff == pytest.approx(0.15)
    assert comp.duration_diff == pytest.approx(150.0)
    assert comp.step_count_diff == 1
