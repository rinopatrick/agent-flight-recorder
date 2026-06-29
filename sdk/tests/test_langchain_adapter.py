import time
import uuid

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.langchain import LangChainAdapter
from flight_recorder.models import StepType, Trace


def test_adapter_is_subclass():
    adapter = LangChainAdapter(agent_name="test_agent")
    assert isinstance(adapter, BaseAdapter)


def test_adapter_creates_trace_from_events():
    adapter = LangChainAdapter(agent_name="my_agent")

    run_id_1 = uuid.uuid4().hex
    adapter.on_llm_start(
        serialized={"name": "OpenAI"},
        prompts=["What is 2+2?"],
        run_id=run_id_1,
    )
    adapter.on_llm_end(
        output={"generations": [[{"text": "4"}]], "llm_output": {"token_usage": {"prompt_tokens": 5, "completion_tokens": 1}}},
        run_id=run_id_1,
    )

    run_id_2 = uuid.uuid4().hex
    adapter.on_tool_start(
        serialized={"name": "calculator"},
        input_str="2+2",
        run_id=run_id_2,
    )
    adapter.on_tool_end(output="4", run_id=run_id_2)

    trace = adapter.build_trace()

    assert isinstance(trace, Trace)
    assert trace.agent_name == "my_agent"
    assert len(trace.steps) == 2

    llm_step = trace.steps[0]
    assert llm_step.step_type == StepType.LLM_CALL
    assert llm_step.name == "OpenAI"
    assert llm_step.input_data["prompts"] == ["What is 2+2?"]
    assert llm_step.tokens_in == 5
    assert llm_step.tokens_out == 1

    tool_step = trace.steps[1]
    assert tool_step.step_type == StepType.TOOL_CALL
    assert tool_step.name == "calculator"
    assert tool_step.input_data["input"] == "2+2"
    assert tool_step.output_data["output"] == "4"


def test_adapter_tracks_timing():
    adapter = LangChainAdapter(agent_name="timing_agent")

    run_id = uuid.uuid4().hex
    adapter.on_llm_start(serialized={"name": "SlowLLM"}, prompts=["hello"], run_id=run_id)
    time.sleep(0.05)
    adapter.on_llm_end(
        output={"generations": [[{"text": "hi"}]], "llm_output": None},
        run_id=run_id,
    )

    trace = adapter.build_trace()
    assert len(trace.steps) == 1
    assert trace.steps[0].duration_ms > 0
