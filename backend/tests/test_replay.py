import pytest

from flight_recorder import Step, StepType, Trace
from flight_recorder.models import Branch

from flight_recorder_backend.replay import ReplayEngine


def _make_trace() -> Trace:
    steps = [
        Step(
            index=0,
            step_type=StepType.LLM_CALL,
            name="gpt-4",
            input_data={"prompt": "What is 2+2?"},
            output_data={"response": "4"},
            tokens_in=10,
            tokens_out=5,
            cost=0.003,
            duration_ms=150.0,
            context_snapshot={"conversation": "math"},
        ),
        Step(
            index=1,
            step_type=StepType.TOOL_CALL,
            name="calculator",
            input_data={"input": "2+2"},
            output_data={"output": "4"},
            cost=0.001,
            duration_ms=50.0,
        ),
        Step(
            index=2,
            step_type=StepType.LLM_CALL,
            name="gpt-4",
            input_data={"prompt": "Summarize"},
            output_data={"response": "The answer is 4"},
            tokens_in=20,
            tokens_out=10,
            cost=0.005,
            duration_ms=200.0,
        ),
    ]
    return Trace(agent_name="math-agent", steps=steps)


# --- create_branch_from_trace ---


def test_create_branch_copies_steps_up_to_fork():
    engine = ReplayEngine()
    trace = _make_trace()
    branch = engine.create_branch_from_trace(
        trace=trace, fork_step_index=1, name="fork-at-1"
    )
    assert isinstance(branch, Branch)
    assert branch.name == "fork-at-1"
    assert branch.parent_trace_id == trace.id
    assert branch.fork_step_index == 1
    assert len(branch.steps) == 1
    assert branch.steps[0].name == "gpt-4"


def test_create_branch_with_modifications():
    engine = ReplayEngine()
    trace = _make_trace()
    branch = engine.create_branch_from_trace(
        trace=trace,
        fork_step_index=1,
        name="swap-model",
        modifications={"model": "gpt-4o"},
    )
    assert branch.steps[0].name == "gpt-4o"
    assert branch.modifications == {"model": "gpt-4o"}


def test_create_branch_fork_at_zero():
    engine = ReplayEngine()
    trace = _make_trace()
    branch = engine.create_branch_from_trace(
        trace=trace, fork_step_index=0, name="empty-branch"
    )
    assert len(branch.steps) == 0


def test_create_branch_fork_at_end():
    engine = ReplayEngine()
    trace = _make_trace()
    branch = engine.create_branch_from_trace(
        trace=trace, fork_step_index=3, name="full-copy"
    )
    assert len(branch.steps) == 3


# --- apply_modification ---


def test_apply_modification_model():
    engine = ReplayEngine()
    step = _make_trace().steps[0]
    modified = engine.apply_modification(step, {"model": "claude-3"})
    assert modified.name == "claude-3"
    assert modified.input_data == step.input_data


def test_apply_modification_prompt():
    engine = ReplayEngine()
    step = _make_trace().steps[0]
    modified = engine.apply_modification(step, {"prompt": "What is 3+3?"})
    assert modified.input_data["prompt"] == "What is 3+3?"
    assert modified.name == step.name


def test_apply_modification_context():
    engine = ReplayEngine()
    step = _make_trace().steps[0]
    modified = engine.apply_modification(step, {"context": {"conversation": "physics"}})
    assert modified.context_snapshot == {"conversation": "physics"}


def test_apply_modification_multiple():
    engine = ReplayEngine()
    step = _make_trace().steps[0]
    modified = engine.apply_modification(
        step, {"model": "gpt-4o", "prompt": "new prompt"}
    )
    assert modified.name == "gpt-4o"
    assert modified.input_data["prompt"] == "new prompt"


def test_apply_modification_noop():
    engine = ReplayEngine()
    step = _make_trace().steps[0]
    modified = engine.apply_modification(step, {})
    assert modified.name == step.name
    assert modified.input_data == step.input_data


# --- compare_branches ---


def test_compare_branches_basic():
    engine = ReplayEngine()
    trace = _make_trace()
    branch_a = engine.create_branch_from_trace(
        trace=trace, fork_step_index=2, name="branch-a"
    )
    branch_b = engine.create_branch_from_trace(
        trace=trace,
        fork_step_index=2,
        name="branch-b",
        modifications={"model": "gpt-4o"},
    )
    result = engine.compare_branches(branch_a, branch_b)
    assert "cost_diff" in result
    assert "duration_diff" in result
    assert "step_count_diff" in result
    assert "output_diffs" in result
    assert result["step_count_diff"] == 0
    assert result["cost_diff"] == pytest.approx(0.0)
    assert result["duration_diff"] == pytest.approx(0.0)


def test_compare_branches_different_lengths():
    engine = ReplayEngine()
    trace = _make_trace()
    branch_a = engine.create_branch_from_trace(
        trace=trace, fork_step_index=1, name="short"
    )
    branch_b = engine.create_branch_from_trace(
        trace=trace, fork_step_index=3, name="long"
    )
    result = engine.compare_branches(branch_a, branch_b)
    assert result["step_count_diff"] == -2
    assert result["cost_diff"] < 0  # branch_a has less cost
    assert result["duration_diff"] < 0


def test_compare_branches_output_diffs():
    engine = ReplayEngine()
    trace = _make_trace()
    branch_a = engine.create_branch_from_trace(
        trace=trace, fork_step_index=3, name="original"
    )
    # Manually create a branch with different output
    modified_step = trace.steps[0].model_copy(
        update={"output_data": {"response": "5"}}
    )
    branch_b = Branch(
        name="modified",
        parent_trace_id=trace.id,
        fork_step_index=0,
        steps=[modified_step, trace.steps[1], trace.steps[2]],
    )
    result = engine.compare_branches(branch_a, branch_b)
    assert len(result["output_diffs"]) == 3
    assert result["output_diffs"][0]["step_index"] == 0
    assert result["output_diffs"][0]["different"] is True
    assert result["output_diffs"][1]["different"] is False
