import json
from datetime import timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base

from flight_recorder.models import Annotation

Base = declarative_base()


class AnnotationRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "annotations"

    id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    tags_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False)


class AnnotationStorage:
    def __init__(self, db_path: Path) -> None:
        self._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self._engine)

    def save_annotation(self, annotation: Annotation) -> None:
        with Session(self._engine) as db:
            row = AnnotationRow(
                id=annotation.id,
                trace_id=annotation.trace_id,
                content=annotation.content,
                tags_json=json.dumps(annotation.tags),
                created_at=annotation.created_at,
            )
            db.merge(row)
            db.commit()

    def get_annotations_for_trace(self, trace_id: str) -> list[Annotation]:
        with Session(self._engine) as db:
            rows = (
                db.query(AnnotationRow)
                .filter(AnnotationRow.trace_id == trace_id)
                .order_by(AnnotationRow.created_at.desc())
                .all()
            )
            return [self._row_to_annotation(r) for r in rows]

    def delete_annotation(self, annotation_id: str) -> None:
        with Session(self._engine) as db:
            row = db.get(AnnotationRow, annotation_id)
            if row is not None:
                db.delete(row)
                db.commit()

    def add_tag(self, annotation_id: str, tag: str) -> None:
        with Session(self._engine) as db:
            row = db.get(AnnotationRow, annotation_id)
            if row is None:
                return
            tags: list[str] = json.loads(row.tags_json)  # type: ignore[arg-type]
            if tag not in tags:
                tags.append(tag)
                row.tags_json = json.dumps(tags)  # type: ignore[assignment]
                db.commit()

    def remove_tag(self, annotation_id: str, tag: str) -> None:
        with Session(self._engine) as db:
            row = db.get(AnnotationRow, annotation_id)
            if row is None:
                return
            tags: list[str] = json.loads(row.tags_json)  # type: ignore[arg-type]
            if tag in tags:
                tags.remove(tag)
                row.tags_json = json.dumps(tags)  # type: ignore[assignment]
                db.commit()

    @staticmethod
    def _row_to_annotation(row: AnnotationRow) -> Annotation:
        return Annotation(
            id=row.id,  # type: ignore[arg-type]
            trace_id=row.trace_id,  # type: ignore[arg-type]
            content=row.content,  # type: ignore[arg-type]
            tags=json.loads(row.tags_json),  # type: ignore[arg-type]
            created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at,  # type: ignore[arg-type]
        )
