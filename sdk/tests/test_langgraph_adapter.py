from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.langgraph import LangGraphAdapter
from flight_recorder.models import StepType


def test_langgraph_adapter_is_base_adapter():
    adapter = LangGraphAdapter(agent_name="test-graph")
    assert isinstance(adapter, BaseAdapter)


def test_langgraph_record_node():
    adapter = LangGraphAdapter(agent_name="test-graph")
    adapter.record_node("agent_node", input_data={"query": "hello"}, output_data={"response": "hi"})
    trace = adapter.build_trace()
    assert len(trace.steps) == 1
    assert trace.steps[0].name == "agent_node"
    assert trace.steps[0].step_type == StepType.TOOL_CALL
    assert trace.steps[0].input_data == {"query": "hello"}


def test_langgraph_record_multiple_nodes():
    adapter = LangGraphAdapter(agent_name="test-graph")
    adapter.record_node("node_a", input_data={}, output_data={})
    adapter.record_node("node_b", input_data={}, output_data={})
    trace = adapter.build_trace()
    assert len(trace.steps) == 2


def test_langgraph_record_conditional_edge():
    adapter = LangGraphAdapter(agent_name="test-graph")
    adapter.record_conditional_edge("router", chosen_path="path_a", input_data={"state": "x"})
    trace = adapter.build_trace()
    assert len(trace.steps) == 1
    assert trace.steps[0].name == "router"
    assert trace.steps[0].output_data == {"chosen_path": "path_a"}
