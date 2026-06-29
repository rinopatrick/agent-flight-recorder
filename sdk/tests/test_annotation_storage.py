from pathlib import Path

from flight_recorder.annotation_storage import AnnotationStorage
from flight_recorder.models import Annotation


def test_save_and_get_annotations(tmp_path: Path):
    store = AnnotationStorage(tmp_path / "test.db")
    a = Annotation(trace_id="abc", content="slow trace", tags=["perf"])
    store.save_annotation(a)
    results = store.get_annotations_for_trace("abc")
    assert len(results) == 1
    assert results[0].content == "slow trace"


def test_delete_annotation(tmp_path: Path):
    store = AnnotationStorage(tmp_path / "test.db")
    a = Annotation(trace_id="abc", content="note")
    store.save_annotation(a)
    store.delete_annotation(a.id)
    assert store.get_annotations_for_trace("abc") == []


def test_add_and_remove_tag(tmp_path: Path):
    store = AnnotationStorage(tmp_path / "test.db")
    a = Annotation(trace_id="abc", content="note", tags=["initial"])
    store.save_annotation(a)
    store.add_tag(a.id, "new-tag")
    results = store.get_annotations_for_trace("abc")
    assert "new-tag" in results[0].tags
    store.remove_tag(a.id, "initial")
    results = store.get_annotations_for_trace("abc")
    assert "initial" not in results[0].tags
