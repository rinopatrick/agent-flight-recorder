import json
from datetime import timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base

from flight_recorder.models import TraceSession

Base = declarative_base()


class SessionRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    trace_ids_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")


class SessionStorage:
    def __init__(self, db_path: Path | None = None, db_url: str | None = None) -> None:
        if db_url:
            self._engine = create_engine(db_url)
        elif db_path:
            self._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        else:
            raise ValueError("Either db_path or db_url must be provided")
        Base.metadata.create_all(self._engine)

    def save_session(self, session: TraceSession) -> None:
        with Session(self._engine) as db:
            row = SessionRow(
                id=session.id,
                name=session.name,
                trace_ids_json=json.dumps(session.trace_ids),
                created_at=session.created_at,
                metadata_json=json.dumps(session.metadata),
            )
            db.merge(row)
            db.commit()

    def get_session(self, session_id: str) -> TraceSession | None:
        with Session(self._engine) as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                return None
            return self._row_to_session(row)

    def list_sessions(self) -> list[TraceSession]:
        with Session(self._engine) as db:
            rows = db.query(SessionRow).order_by(SessionRow.created_at.desc()).all()
            return [self._row_to_session(r) for r in rows]

    def add_trace_to_session(self, session_id: str, trace_id: str) -> None:
        with Session(self._engine) as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                return
            ids: list[str] = json.loads(row.trace_ids_json)  # type: ignore[arg-type]
            if trace_id not in ids:
                ids.append(trace_id)
                row.trace_ids_json = json.dumps(ids)  # type: ignore[assignment]
                db.commit()

    def remove_trace_from_session(self, session_id: str, trace_id: str) -> None:
        with Session(self._engine) as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                return
            ids: list[str] = json.loads(row.trace_ids_json)  # type: ignore[arg-type]
            if trace_id in ids:
                ids.remove(trace_id)
                row.trace_ids_json = json.dumps(ids)  # type: ignore[assignment]
                db.commit()

    @staticmethod
    def _row_to_session(row: SessionRow) -> TraceSession:
        return TraceSession(
            id=row.id,  # type: ignore[arg-type]
            name=row.name,  # type: ignore[arg-type]
            trace_ids=json.loads(row.trace_ids_json),  # type: ignore[arg-type]
            created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at,  # type: ignore[arg-type]
            metadata=json.loads(row.metadata_json),  # type: ignore[arg-type]
        )
