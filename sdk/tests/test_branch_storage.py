from datetime import datetime, timezone
from pathlib import Path

import pytest

from flight_recorder.models import Branch, Step, StepType
from flight_recorder.branch_storage import BranchStorage


def _make_branch(
    name: str = "test_branch",
    parent_trace_id: str = "trace_abc",
    fork_step_index: int = 3,
    n_steps: int = 1,
) -> Branch:
    steps = [
        Step(
            index=i,
            step_type=StepType.TOOL_CALL,
            name=f"branch_step_{i}",
            input_data={"q": f"input {i}"},
            output_data={"r": f"output {i}"},
            tokens_in=20 + i,
            tokens_out=10 + i,
            cost=0.002 * (i + 1),
            duration_ms=80.0 * (i + 1),
        )
        for i in range(n_steps)
    ]
    return Branch(
        name=name,
        parent_trace_id=parent_trace_id,
        fork_step_index=fork_step_index,
        modifications={"changed_prompt": True},
        steps=steps,
    )


def test_save_and_get_branch(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = BranchStorage(db)
    branch = _make_branch("br1", "trace_1", 2, n_steps=2)
    storage.save_branch(branch)

    loaded = storage.get_branch(branch.id)
    assert loaded is not None
    assert loaded.id == branch.id
    assert loaded.name == "br1"
    assert loaded.parent_trace_id == "trace_1"
    assert loaded.fork_step_index == 2
    assert loaded.modifications == {"changed_prompt": True}
    assert len(loaded.steps) == 2
    assert loaded.steps[0].name == "branch_step_0"
    assert loaded.steps[0].step_type == StepType.TOOL_CALL
    assert loaded.steps[1].index == 1
    assert loaded.created_at is not None


def test_list_branches(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = BranchStorage(db)
    storage.save_branch(_make_branch("a"))
    storage.save_branch(_make_branch("b"))

    branches = storage.list_branches()
    assert len(branches) == 2
    assert {b.name for b in branches} == {"a", "b"}


def test_list_branches_with_limit(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = BranchStorage(db)
    for i in range(5):
        storage.save_branch(_make_branch(f"br_{i}"))

    branches = storage.list_branches(limit=2)
    assert len(branches) == 2


def test_list_branches_for_trace(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = BranchStorage(db)
    storage.save_branch(_make_branch("br_a", parent_trace_id="trace_1"))
    storage.save_branch(_make_branch("br_b", parent_trace_id="trace_1"))
    storage.save_branch(_make_branch("br_c", parent_trace_id="trace_2"))

    branches = storage.list_branches_for_trace("trace_1")
    assert len(branches) == 2
    assert all(b.parent_trace_id == "trace_1" for b in branches)


def test_list_branches_for_trace_empty(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = BranchStorage(db)
    assert storage.list_branches_for_trace("nonexistent") == []


def test_get_nonexistent_branch(tmp_path: Path):
    db = tmp_path / "test.db"
    storage = BranchStorage(db)
    assert storage.get_branch("nonexistent") is None
