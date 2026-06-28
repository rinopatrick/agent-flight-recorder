from flight_recorder.models import StepType
from flight_recorder.recorder import clear_last_trace, get_last_trace, record


def test_record_no_trace_by_default():
    clear_last_trace()
    assert get_last_trace() is None


def test_record_captures_function_call():
    @record
    def my_agent(x: int) -> int:
        return x + 1

    result = my_agent(41)
    assert result == 42

    trace = get_last_trace()
    assert trace is not None
    assert trace.agent_name == "my_agent"
    assert len(trace.steps) == 1
    assert trace.steps[0].step_type == StepType.OUTPUT
    assert trace.steps[0].output_data == {"result": 42}


def test_record_captures_llm_simulation():
    @record
    def my_agent(prompt: str) -> str:
        record.llm_call(
            name="chat",
            input_data={"prompt": prompt},
            output_data={"response": "hello"},
            tokens_in=10,
            tokens_out=5,
            cost=0.001,
        )
        return "hello"

    result = my_agent("hi")
    assert result == "hello"

    trace = get_last_trace()
    assert trace is not None
    assert len(trace.steps) == 2
    llm_step = trace.steps[0]
    assert llm_step.step_type == StepType.LLM_CALL
    assert llm_step.name == "chat"
    assert llm_step.input_data == {"prompt": "hi"}
    assert llm_step.output_data == {"response": "hello"}
    assert llm_step.tokens_in == 10
    assert llm_step.tokens_out == 5
    assert llm_step.cost == 0.001


def test_record_captures_tool_call():
    @record
    def my_agent() -> str:
        record.tool_call(
            name="search",
            input_data={"query": "test"},
            output_data={"results": ["a", "b"]},
        )
        return "done"

    result = my_agent()
    assert result == "done"

    trace = get_last_trace()
    assert trace is not None
    assert len(trace.steps) == 2
    tool_step = trace.steps[0]
    assert tool_step.step_type == StepType.TOOL_CALL
    assert tool_step.name == "search"
    assert tool_step.input_data == {"query": "test"}
    assert tool_step.output_data == {"results": ["a", "b"]}


def test_record_stores_context():
    @record
    def my_agent() -> str:
        record.set_context({"user": "alice", "session": "abc"})
        return "ok"

    result = my_agent()
    assert result == "ok"

    trace = get_last_trace()
    assert trace is not None
    assert len(trace.steps) == 1
    assert trace.steps[0].context_snapshot == {"user": "alice", "session": "abc"}


def test_record_captures_error():
    @record
    def bad_agent():
        raise ValueError("boom")

    try:
        bad_agent()
    except ValueError:
        pass

    trace = get_last_trace()
    assert trace is not None
    assert len(trace.steps) == 1
    assert trace.steps[0].step_type == StepType.ERROR
    assert "boom" in trace.steps[0].error
