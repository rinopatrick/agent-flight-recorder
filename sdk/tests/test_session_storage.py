from pathlib import Path

from flight_recorder.models import TraceSession
from flight_recorder.session_storage import SessionStorage


def test_save_and_get_session(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    s = TraceSession(name="test", trace_ids=["abc", "def"])
    store.save_session(s)
    loaded = store.get_session(s.id)
    assert loaded is not None
    assert loaded.name == "test"
    assert loaded.trace_ids == ["abc", "def"]


def test_list_sessions(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    store.save_session(TraceSession(name="s1"))
    store.save_session(TraceSession(name="s2"))
    sessions = store.list_sessions()
    assert len(sessions) == 2


def test_add_trace_to_session(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    s = TraceSession(name="test", trace_ids=["abc"])
    store.save_session(s)
    store.add_trace_to_session(s.id, "def")
    loaded = store.get_session(s.id)
    assert "def" in loaded.trace_ids


def test_remove_trace_from_session(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    s = TraceSession(name="test", trace_ids=["abc", "def"])
    store.save_session(s)
    store.remove_trace_from_session(s.id, "abc")
    loaded = store.get_session(s.id)
    assert "abc" not in loaded.trace_ids
    assert "def" in loaded.trace_ids
