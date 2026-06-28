import time
import uuid

import pytest

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.crewai import CrewAIAdapter
from flight_recorder.models import StepType, Trace


def test_adapter_is_subclass():
    adapter = CrewAIAdapter(agent_name="test_agent")
    assert isinstance(adapter, BaseAdapter)


def test_adapter_creates_trace_from_events():
    adapter = CrewAIAdapter(agent_name="my_crew")

    run_id_1 = uuid.uuid4().hex
    adapter.on_llm_call_start(agent_name="researcher", prompt="What is AI?", run_id=run_id_1)
    adapter.on_llm_call_end(
        agent_name="researcher",
        response="AI is artificial intelligence.",
        tokens_used={"prompt_tokens": 5, "completion_tokens": 6},
        run_id=run_id_1,
    )

    run_id_2 = uuid.uuid4().hex
    adapter.on_tool_usage(
        agent_name="researcher",
        tool_name="web_search",
        input_data={"query": "AI news"},
        output_data={"results": ["article1"]},
        run_id=run_id_2,
    )

    run_id_3 = uuid.uuid4().hex
    adapter.on_agent_start(agent_name="researcher", task_description="Research AI", run_id=run_id_3)
    adapter.on_agent_end(agent_name="researcher", result="Done", run_id=run_id_3)

    trace = adapter.build_trace()

    assert isinstance(trace, Trace)
    assert trace.agent_name == "my_crew"
    assert len(trace.steps) == 3

    llm_step = trace.steps[0]
    assert llm_step.step_type == StepType.LLM_CALL
    assert llm_step.name == "llm_call"
    assert llm_step.input_data["prompt"] == "What is AI?"
    assert llm_step.output_data["response"] == "AI is artificial intelligence."
    assert llm_step.tokens_in == 5
    assert llm_step.tokens_out == 6

    tool_step = trace.steps[1]
    assert tool_step.step_type == StepType.TOOL_CALL
    assert tool_step.name == "web_search"
    assert tool_step.input_data["query"] == "AI news"
    assert tool_step.output_data["results"] == ["article1"]


def test_adapter_tracks_timing():
    adapter = CrewAIAdapter(agent_name="timing_agent")

    run_id = uuid.uuid4().hex
    adapter.on_llm_call_start(agent_name="agent", prompt="hello", run_id=run_id)
    time.sleep(0.05)
    adapter.on_llm_call_end(
        agent_name="agent",
        response="hi",
        tokens_used=None,
        run_id=run_id,
    )

    trace = adapter.build_trace()
    assert len(trace.steps) == 1
    assert trace.steps[0].duration_ms > 0


def test_adapter_no_tokens_when_none():
    adapter = CrewAIAdapter(agent_name="agent")

    run_id = uuid.uuid4().hex
    adapter.on_llm_call_start(agent_name="agent", prompt="q", run_id=run_id)
    adapter.on_llm_call_end(agent_name="agent", response="a", tokens_used=None, run_id=run_id)

    trace = adapter.build_trace()
    assert trace.steps[0].tokens_in is None
    assert trace.steps[0].tokens_out is None
