import ast
import pytest
from flight_recorder.models import Step, StepType, Trace
from flight_recorder_backend.test_generator import TestGenerator


@pytest.fixture
def generator():
    return TestGenerator()


@pytest.fixture
def simple_trace():
    return Trace(
        id="abc123def456",
        agent_name="my_agent",
        steps=[
            Step(
                index=0,
                step_type=StepType.TOOL_CALL,
                name="search",
                input_data={"query": "test"},
                output_data={"results": []},
                cost=0.01,
                duration_ms=200,
            ),
            Step(
                index=1,
                step_type=StepType.LLM_CALL,
                name="gpt-4",
                input_data={"prompt": "hello"},
                output_data={"response": "hi"},
                cost=0.02,
                duration_ms=300,
            ),
            Step(
                index=2,
                step_type=StepType.TOOL_CALL,
                name="write_file",
                input_data={"path": "/tmp/out.txt", "content": "data"},
                output_data={"status": "ok"},
                cost=0.005,
                duration_ms=100,
            ),
        ],
    )


@pytest.fixture
def llm_only_trace():
    return Trace(
        id="llm001abc",
        agent_name="chatbot",
        steps=[
            Step(
                index=0,
                step_type=StepType.LLM_CALL,
                name="claude-3-opus",
                input_data={"prompt": "summarize"},
                output_data={"response": "summary"},
                cost=0.05,
                duration_ms=1000,
            ),
        ],
    )


@pytest.fixture
def empty_trace():
    return Trace(
        id="empty001xxx",
        agent_name="noop_agent",
        steps=[],
    )


def test_generated_code_is_valid_python(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    ast.parse(code)


def test_function_name_format(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    assert "def test_agent_my_agent_abc123(" in code


def test_function_name_with_llm_trace(generator, llm_only_trace):
    code = generator.generate_test(llm_only_trace)
    assert "def test_agent_chatbot_llm001(" in code


def test_contains_run_agent_call(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    assert 'run_agent("original input")' in code


def test_tool_call_assertions(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    assert 'assert_tool_called(result, "search"' in code
    assert 'assert_tool_called(result, "write_file"' in code


def test_tool_call_arguments(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    assert "'query': 'test'" in code
    assert "'path': '/tmp/out.txt'" in code


def test_llm_call_assertion(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    assert 'assert_model_used(result, "gpt-4")' in code


def test_llm_only_trace_has_model_assertion(generator, llm_only_trace):
    code = generator.generate_test(llm_only_trace)
    assert 'assert_model_used(result, "claude-3-opus")' in code


def test_cost_assertion_with_margin(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    total = 0.01 + 0.02 + 0.005
    expected_max = round(total * 1.1, 4)
    assert f"assert_cost(result, max_cost={expected_max})" in code


def test_duration_assertion_with_margin(generator, simple_trace):
    code = generator.generate_test(simple_trace)
    total_ms = 200 + 300 + 100
    expected_max = round(total_ms * 1.1, 1)
    assert f"assert_latency(result, max_ms={expected_max})" in code


def test_empty_trace_generates_valid_python(generator, empty_trace):
    code = generator.generate_test(empty_trace)
    ast.parse(code)


def test_empty_trace_has_no_assertions(generator, empty_trace):
    code = generator.generate_test(empty_trace)
    assert "assert_tool_called" not in code
    assert "assert_model_used" not in code


def test_empty_trace_still_has_cost_and_duration(generator, empty_trace):
    code = generator.generate_test(empty_trace)
    assert "assert_cost(result, max_cost=0.0)" in code
    assert "assert_latency(result, max_ms=0.0)" in code


def test_llm_trace_valid_python(generator, llm_only_trace):
    code = generator.generate_test(llm_only_trace)
    ast.parse(code)


def test_llm_trace_cost_assertion(generator, llm_only_trace):
    code = generator.generate_test(llm_only_trace)
    assert "assert_cost(result, max_cost=0.055)" in code


def test_llm_trace_duration_assertion(generator, llm_only_trace):
    code = generator.generate_test(llm_only_trace)
    assert "assert_latency(result, max_ms=1100.0)" in code
