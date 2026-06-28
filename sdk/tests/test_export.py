import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from flight_recorder.export import (
    export_to_file,
    export_trace,
    import_from_file,
    import_trace,
)
from flight_recorder.models import Step, StepType, Trace


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
    return Trace(
        agent_name=agent_name,
        steps=steps,
        metadata={"env": "test"},
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestExportTrace:
    def test_returns_dict(self):
        trace = _make_trace()
        data = export_trace(trace)
        assert isinstance(data, dict)

    def test_serializes_basic_fields(self):
        trace = _make_trace("my_agent", n_steps=0)
        data = export_trace(trace)
        assert data["id"] == trace.id
        assert data["agent_name"] == "my_agent"
        assert data["steps"] == []
        assert data["metadata"] == {"env": "test"}

    def test_serializes_datetime_as_iso(self):
        trace = _make_trace()
        data = export_trace(trace)
        assert data["created_at"] == "2025-06-15T12:00:00+00:00"

    def test_serializes_step_type_enum(self):
        trace = _make_trace(n_steps=1)
        data = export_trace(trace)
        assert data["steps"][0]["step_type"] == "llm_call"

    def test_serializes_optional_fields(self):
        trace = _make_trace(n_steps=3)
        data = export_trace(trace)
        assert data["steps"][0]["context_snapshot"] == {"turn": 0}
        assert data["steps"][1]["context_snapshot"] is None
        assert data["steps"][2]["error"] == "oops"

    def test_output_is_json_compatible(self):
        trace = _make_trace(n_steps=2)
        data = export_trace(trace)
        serialized = json.dumps(data)
        assert isinstance(serialized, str)


class TestImportTrace:
    def test_round_trip(self):
        trace = _make_trace("rt_agent", n_steps=3)
        data = export_trace(trace)
        restored = import_trace(data)
        assert restored.id == trace.id
        assert restored.agent_name == trace.agent_name
        assert restored.created_at == trace.created_at
        assert restored.metadata == trace.metadata
        assert len(restored.steps) == len(trace.steps)

    def test_round_trip_steps(self):
        trace = _make_trace(n_steps=3)
        data = export_trace(trace)
        restored = import_trace(data)
        for orig, rest in zip(trace.steps, restored.steps):
            assert rest.index == orig.index
            assert rest.step_type == orig.step_type
            assert rest.name == orig.name
            assert rest.input_data == orig.input_data
            assert rest.output_data == orig.output_data
            assert rest.tokens_in == orig.tokens_in
            assert rest.tokens_out == orig.tokens_out
            assert rest.cost == pytest.approx(orig.cost)
            assert rest.duration_ms == pytest.approx(orig.duration_ms)
            assert rest.context_snapshot == orig.context_snapshot
            assert rest.error == orig.error

    def test_round_trip_all_step_types(self):
        steps = [
            Step(
                index=i,
                step_type=st,
                name=f"step_{st.value}",
                input_data={},
                output_data={},
            )
            for i, st in enumerate(StepType)
        ]
        trace = Trace(agent_name="enum_agent", steps=steps)
        data = export_trace(trace)
        restored = import_trace(data)
        for orig, rest in zip(steps, restored.steps):
            assert rest.step_type == orig.step_type


class TestFileIO:
    def test_export_and_import_file(self, tmp_path: Path):
        path = tmp_path / "trace.json"
        trace = _make_trace("file_agent", n_steps=2)
        export_to_file(trace, path)
        assert path.exists()

        restored = import_from_file(path)
        assert restored.id == trace.id
        assert restored.agent_name == "file_agent"
        assert len(restored.steps) == 2

    def test_file_contains_valid_json(self, tmp_path: Path):
        path = tmp_path / "trace.json"
        trace = _make_trace()
        export_to_file(trace, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["id"] == trace.id

    def test_round_trip_through_file(self, tmp_path: Path):
        path = tmp_path / "trace.json"
        trace = _make_trace(n_steps=3)
        export_to_file(trace, path)
        restored = import_from_file(path)
        assert restored == trace


class TestEdgeCases:
    def test_empty_steps(self):
        trace = Trace(agent_name="empty", steps=[])
        data = export_trace(trace)
        restored = import_trace(data)
        assert restored.steps == []
        assert restored.agent_name == "empty"

    def test_none_context_snapshot(self):
        step = Step(
            index=0,
            step_type=StepType.TOOL_CALL,
            name="tool",
            input_data={},
            output_data={},
            context_snapshot=None,
        )
        trace = Trace(agent_name="ctx_none", steps=[step])
        data = export_trace(trace)
        restored = import_trace(data)
        assert restored.steps[0].context_snapshot is None

    def test_none_token_fields(self):
        step = Step(
            index=0,
            step_type=StepType.OUTPUT,
            name="out",
            input_data={},
            output_data={},
            tokens_in=None,
            tokens_out=None,
        )
        trace = Trace(agent_name="no_tokens", steps=[step])
        data = export_trace(trace)
        restored = import_trace(data)
        assert restored.steps[0].tokens_in is None
        assert restored.steps[0].tokens_out is None

    def test_none_error(self):
        step = Step(
            index=0,
            step_type=StepType.LLM_CALL,
            name="ok",
            input_data={},
            output_data={},
            error=None,
        )
        trace = Trace(agent_name="no_error", steps=[step])
        data = export_trace(trace)
        restored = import_trace(data)
        assert restored.steps[0].error is None

    def test_empty_metadata(self):
        trace = Trace(agent_name="meta_empty", metadata={})
        data = export_trace(trace)
        restored = import_trace(data)
        assert restored.metadata == {}

    def test_import_from_nonexistent_file(self, tmp_path: Path):
        path = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError):
            import_from_file(path)
