from flight_recorder.models import Annotation


def test_annotation_creation():
    a = Annotation(trace_id="abc123", content="This trace is slow", tags=["performance", "investigate"])
    assert a.trace_id == "abc123"
    assert a.content == "This trace is slow"
    assert "performance" in a.tags
    assert a.id is not None


def test_annotation_defaults():
    a = Annotation(trace_id="abc123", content="note")
    assert a.tags == []
