import pytest

from flight_recorder.models import Branch, Step, StepType


def test_branch_creation():
    branch = Branch(
        name="alt-search",
        parent_trace_id="abc123def456",
        fork_step_index=3,
        modifications={"temperature": 0.9, "model": "gpt-4"},
    )
    assert branch.id is not None
    assert len(branch.id) == 12
    assert branch.name == "alt-search"
    assert branch.parent_trace_id == "abc123def456"
    assert branch.fork_step_index == 3
    assert branch.modifications == {"temperature": 0.9, "model": "gpt-4"}
    assert branch.steps == []
    assert branch.created_at is not None


def test_branch_with_steps():
    steps = [
        Step(
            index=0,
            step_type=StepType.LLM_CALL,
            name="generate",
            input_data={"prompt": "hello"},
            output_data={"text": "hi"},
            cost=0.005,
            duration_ms=120.0,
        ),
        Step(
            index=1,
            step_type=StepType.TOOL_CALL,
            name="search",
            input_data={"q": "test"},
            output_data={"results": []},
            cost=0.002,
            duration_ms=80.0,
        ),
    ]
    branch = Branch(
        name="alt-path",
        parent_trace_id="trace123",
        fork_step_index=0,
        modifications={},
        steps=steps,
    )
    assert len(branch.steps) == 2
    assert branch.steps[0].name == "generate"
    assert branch.steps[1].name == "search"


def test_branch_total_cost():
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
        for i, (c, d) in enumerate([(0.01, 200.0), (0.02, 300.0), (0.005, 50.0)])
    ]
    branch = Branch(
        name="costly-branch",
        parent_trace_id="xyz",
        fork_step_index=5,
        modifications={"max_tokens": 1000},
        steps=steps,
    )
    assert branch.total_cost() == pytest.approx(0.035)
    assert branch.total_duration_ms() == pytest.approx(550.0)
