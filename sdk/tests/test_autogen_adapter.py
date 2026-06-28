import time
import uuid

import pytest

from flight_recorder.adapters.autogen import AutoGenAdapter
from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import StepType, Trace


def test_adapter_is_subclass():
    adapter = AutoGenAdapter(agent_name="test_agent")
    assert isinstance(adapter, BaseAdapter)


def test_on_message_creates_output_step():
    adapter = AutoGenAdapter(agent_name="group_chat")

    adapter.on_message(
        sender="assistant",
        receiver="user",
        content="Hello, how can I help?",
        is_tool_call=False,
    )

    trace = adapter.build_trace()
    assert isinstance(trace, Trace)
    assert trace.agent_name == "group_chat"
    assert len(trace.steps) == 1

    step = trace.steps[0]
    assert step.step_type == StepType.OUTPUT
    assert step.name == "assistant -> user"
    assert step.input_data == {"sender": "assistant", "receiver": "user"}
    assert step.output_data == {"content": "Hello, how can I help?"}


def test_on_message_tool_call_creates_tool_step():
    adapter = AutoGenAdapter(agent_name="agent")

    adapter.on_message(
        sender="executor",
        receiver="planner",
        content="search_results: [1, 2, 3]",
        is_tool_call=True,
    )

    trace = adapter.build_trace()
    assert len(trace.steps) == 1

    step = trace.steps[0]
    assert step.step_type == StepType.TOOL_CALL
    assert step.name == "executor -> planner"
    assert step.input_data == {"sender": "executor", "receiver": "planner"}
    assert step.output_data == {"content": "search_results: [1, 2, 3]"}


def test_on_llm_call_creates_llm_step():
    adapter = AutoGenAdapter(agent_name="agent")

    adapter.on_llm_call(
        agent_name="planner",
        prompt="What should I do next?",
        response="Search for flight data.",
        tokens={"prompt_tokens": 10, "completion_tokens": 8},
    )

    trace = adapter.build_trace()
    assert len(trace.steps) == 1

    step = trace.steps[0]
    assert step.step_type == StepType.LLM_CALL
    assert step.name == "planner"
    assert step.input_data == {"prompt": "What should I do next?"}
    assert step.output_data == {"response": "Search for flight data."}
    assert step.tokens_in == 10
    assert step.tokens_out == 8


def test_on_llm_call_no_tokens():
    adapter = AutoGenAdapter(agent_name="agent")

    adapter.on_llm_call(
        agent_name="planner",
        prompt="Hello",
        response="Hi there",
        tokens=None,
    )

    trace = adapter.build_trace()
    step = trace.steps[0]
    assert step.tokens_in is None
    assert step.tokens_out is None


def test_multiple_events_in_order():
    adapter = AutoGenAdapter(agent_name="multi_agent")

    adapter.on_message(sender="user", receiver="assistant", content="Plan my trip", is_tool_call=False)
    adapter.on_llm_call(agent_name="assistant", prompt="Plan my trip", response="I'll search for flights.", tokens=None)
    adapter.on_message(sender="assistant", receiver="executor", content="Search flights", is_tool_call=False)
    adapter.on_message(sender="executor", receiver="assistant", content="Found 3 flights", is_tool_call=True)

    trace = adapter.build_trace()
    assert len(trace.steps) == 4
    assert trace.steps[0].step_type == StepType.OUTPUT
    assert trace.steps[1].step_type == StepType.LLM_CALL
    assert trace.steps[2].step_type == StepType.OUTPUT
    assert trace.steps[3].step_type == StepType.TOOL_CALL
    # Indices are sequential
    for i, step in enumerate(trace.steps):
        assert step.index == i


def test_build_trace_returns_copy():
    adapter = AutoGenAdapter(agent_name="agent")
    adapter.on_message(sender="a", receiver="b", content="msg", is_tool_call=False)

    trace1 = adapter.build_trace()
    trace2 = adapter.build_trace()

    assert trace1.id != trace2.id
    assert len(trace1.steps) == len(trace2.steps) == 1


def test_empty_trace():
    adapter = AutoGenAdapter(agent_name="empty")
    trace = adapter.build_trace()
    assert trace.agent_name == "empty"
    assert len(trace.steps) == 0


def test_metadata_preserved():
    adapter = AutoGenAdapter(agent_name="agent", metadata={"session_id": "abc123"})
    adapter.on_message(sender="a", receiver="b", content="msg", is_tool_call=False)

    trace = adapter.build_trace()
    assert trace.metadata == {"session_id": "abc123"}
