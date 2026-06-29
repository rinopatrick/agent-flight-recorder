from flight_recorder.models import Step, StepType, StreamEvent


def test_stream_event_trace_start():
    e = StreamEvent(event_type="trace_start", trace_id="abc123", data={"agent_name": "test"})
    assert e.event_type == "trace_start"
    assert e.trace_id == "abc123"
    assert e.timestamp is not None


def test_stream_event_step_complete():
    step = Step(index=0, step_type=StepType.LLM_CALL, name="call", input_data={}, output_data={})
    e = StreamEvent(event_type="step_complete", trace_id="abc123", data={"step": step.model_dump()})
    assert e.event_type == "step_complete"
    assert "step" in e.data


def test_stream_event_trace_end():
    e = StreamEvent(event_type="trace_end", trace_id="abc123", data={"total_steps": 5})
    assert e.event_type == "trace_end"
