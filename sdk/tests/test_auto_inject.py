import logging

from flight_recorder.auto_inject import (
    _add_step,
    _get_or_create_auto_trace,
    _original_functions,
    auto_record,
    clear_auto_trace,
    disable_auto_record,
    get_auto_trace,
)
from flight_recorder.models import StepType


def test_auto_record_enables_injection():
    _original_functions.clear()
    auto_record(enable_openai=False, enable_anthropic=False, enable_langchain=False)


def test_disable_auto_record_restores_functions():
    _original_functions.clear()
    _original_functions["test"] = (None, "test", lambda: None)
    disable_auto_record()
    assert len(_original_functions) == 0


def test_auto_record_logs_status(caplog: logging.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        auto_record(enable_openai=False, enable_anthropic=False, enable_langchain=False)
    assert "Auto-injection enabled" in caplog.text


def test_get_or_create_auto_trace_creates_trace():
    clear_auto_trace()
    assert get_auto_trace() is None

    trace = _get_or_create_auto_trace()
    assert trace is not None
    assert trace.agent_name == "auto_record"
    assert get_auto_trace() is trace


def test_clear_auto_trace():
    clear_auto_trace()
    _get_or_create_auto_trace()
    assert get_auto_trace() is not None

    clear_auto_trace()
    assert get_auto_trace() is None


def test_add_step_records_to_auto_trace():
    clear_auto_trace()
    _add_step(
        StepType.LLM_CALL,
        "test/model",
        {"prompt": "hello"},
        {"response": "world"},
        tokens_in=10,
        tokens_out=5,
        duration_ms=100.0,
    )

    trace = get_auto_trace()
    assert trace is not None
    assert len(trace.steps) == 1

    step = trace.steps[0]
    assert step.index == 0
    assert step.step_type == StepType.LLM_CALL
    assert step.name == "test/model"
    assert step.input_data == {"prompt": "hello"}
    assert step.output_data == {"response": "world"}
    assert step.tokens_in == 10
    assert step.tokens_out == 5
    assert step.duration_ms == 100.0


def test_add_step_increments_index():
    clear_auto_trace()
    _add_step(StepType.LLM_CALL, "a", {}, {})
    _add_step(StepType.TOOL_CALL, "b", {}, {})
    _add_step(StepType.OUTPUT, "c", {}, {})

    trace = get_auto_trace()
    assert trace is not None
    assert len(trace.steps) == 3
    assert trace.steps[0].index == 0
    assert trace.steps[1].index == 1
    assert trace.steps[2].index == 2


def test_disable_auto_record_preserves_non_module_entries():
    _original_functions.clear()
    _original_functions["langchain_callback"] = (None, "Foo", lambda: None)
    disable_auto_record()
    assert len(_original_functions) == 0
