import pytest

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.creator import build_step, create_adapter
from flight_recorder.models import Step, StepType, Trace


class TestBuildStep:
    def test_build_step_minimal(self):
        step = build_step(
            step_type=StepType.LLM_CALL,
            name="gpt-4",
            input_data={"prompt": "hello"},
            output_data={"response": "hi"},
        )
        assert isinstance(step, Step)
        assert step.step_type == StepType.LLM_CALL
        assert step.name == "gpt-4"
        assert step.input_data == {"prompt": "hello"}
        assert step.output_data == {"response": "hi"}
        assert step.index == 0
        assert step.cost == 0.0
        assert step.duration_ms == 0.0
        assert step.tokens_in is None
        assert step.tokens_out is None

    def test_build_step_with_optional_fields(self):
        step = build_step(
            step_type=StepType.TOOL_CALL,
            name="search",
            input_data={"query": "weather"},
            output_data={"result": "sunny"},
            index=3,
            tokens_in=10,
            tokens_out=20,
            cost=0.005,
            duration_ms=150.0,
            error="partial failure",
        )
        assert step.index == 3
        assert step.tokens_in == 10
        assert step.tokens_out == 20
        assert step.cost == 0.005
        assert step.duration_ms == 150.0
        assert step.error == "partial failure"

    def test_build_step_accepts_string_step_type(self):
        step = build_step(
            step_type="output",
            name="final",
            input_data={},
            output_data={"text": "done"},
        )
        assert step.step_type == StepType.OUTPUT


class TestCreateAdapter:
    def test_returns_base_adapter_instance(self):
        adapter = create_adapter("custom", {})
        assert isinstance(adapter, BaseAdapter)

    def test_adapter_name_in_trace(self):
        adapter = create_adapter("my_bot", {})
        trace = adapter.build_trace()
        assert isinstance(trace, Trace)
        assert trace.agent_name == "my_bot"

    def test_event_handler_produces_steps(self):
        def on_llm(prompt, response):
            return build_step(
                step_type=StepType.LLM_CALL,
                name="llm",
                input_data={"prompt": prompt},
                output_data={"response": response},
            )

        adapter = create_adapter("bot", {"on_llm": on_llm})
        adapter.handle_event("on_llm", prompt="What is 2+2?", response="4")

        trace = adapter.build_trace()
        assert len(trace.steps) == 1
        assert trace.steps[0].step_type == StepType.LLM_CALL
        assert trace.steps[0].input_data == {"prompt": "What is 2+2?"}
        assert trace.steps[0].output_data == {"response": "4"}

    def test_multiple_event_handlers(self):
        def on_llm(prompt, response):
            return build_step(
                step_type=StepType.LLM_CALL,
                name="llm",
                input_data={"prompt": prompt},
                output_data={"response": response},
            )

        def on_tool(tool_name, input_data, output_data):
            return build_step(
                step_type=StepType.TOOL_CALL,
                name=tool_name,
                input_data=input_data,
                output_data=output_data,
            )

        adapter = create_adapter("agent", {"on_llm": on_llm, "on_tool": on_tool})
        adapter.handle_event("on_llm", prompt="hi", response="hello")
        adapter.handle_event("on_tool", tool_name="search", input_data={"q": "test"}, output_data={"r": "ok"})

        trace = adapter.build_trace()
        assert len(trace.steps) == 2
        assert trace.steps[0].step_type == StepType.LLM_CALL
        assert trace.steps[1].step_type == StepType.TOOL_CALL
        assert trace.steps[1].name == "search"

    def test_unknown_event_raises(self):
        adapter = create_adapter("bot", {})
        with pytest.raises(ValueError, match="Unknown event"):
            adapter.handle_event("on_nonexistent")

    def test_handler_returning_none_skips_step(self):
        def on_event():
            return None

        adapter = create_adapter("bot", {"on_event": on_event})
        adapter.handle_event("on_event")

        trace = adapter.build_trace()
        assert len(trace.steps) == 0

    def test_step_indices_are_sequential(self):
        def make_step(name):
            return build_step(
                step_type=StepType.LLM_CALL,
                name=name,
                input_data={},
                output_data={},
            )

        adapter = create_adapter("bot", {
            "on_a": lambda: make_step("a"),
            "on_b": lambda: make_step("b"),
            "on_c": lambda: make_step("c"),
        })
        adapter.handle_event("on_a")
        adapter.handle_event("on_b")
        adapter.handle_event("on_c")

        trace = adapter.build_trace()
        assert [s.index for s in trace.steps] == [0, 1, 2]

    def test_multiple_adapters_are_independent(self):
        adapter_a = create_adapter("a", {})
        adapter_b = create_adapter("b", {})

        def on_event():
            return build_step(
                step_type=StepType.OUTPUT,
                name="out",
                input_data={},
                output_data={},
            )

        adapter_a._event_handlers["on_event"] = on_event
        adapter_a.handle_event("on_event")

        assert len(adapter_a.build_trace().steps) == 1
        assert len(adapter_b.build_trace().steps) == 0

    def test_build_trace_returns_fresh_copy(self):
        def on_event():
            return build_step(
                step_type=StepType.OUTPUT,
                name="out",
                input_data={},
                output_data={},
            )

        adapter = create_adapter("bot", {"on_event": on_event})
        adapter.handle_event("on_event")

        trace1 = adapter.build_trace()
        trace2 = adapter.build_trace()
        assert trace1.steps == trace2.steps
        assert trace1 is not trace2
