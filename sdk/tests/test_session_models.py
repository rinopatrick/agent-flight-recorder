from flight_recorder.models import TraceSession


def test_session_creation():
    s = TraceSession(name="test-session", trace_ids=["abc", "def"])
    assert s.name == "test-session"
    assert len(s.trace_ids) == 2
    assert s.id is not None
    assert len(s.id) == 12


def test_session_empty_traces():
    s = TraceSession(name="empty")
    assert s.trace_ids == []
    assert s.metadata == {}
