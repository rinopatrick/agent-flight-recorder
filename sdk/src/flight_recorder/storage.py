import json
from datetime import timezone
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, relationship

from flight_recorder.log_config import get_logger
from flight_recorder.models import Step, StepType, Trace

logger = get_logger(__name__)

Base = declarative_base()


class TraceRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "traces"

    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    metadata_json = Column(Text, nullable=False, default="{}")

    steps = relationship("StepRow", back_populates="trace", cascade="all, delete-orphan", order_by="StepRow.index")


class StepRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String, ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True)
    index = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    input_json = Column(Text, nullable=False, default="{}")
    output_json = Column(Text, nullable=False, default="{}")
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    cost = Column(Float, nullable=False, default=0.0)
    duration_ms = Column(Float, nullable=False, default=0.0)
    context_json = Column(Text, nullable=True)
    error = Column(String, nullable=True)

    trace = relationship("TraceRow", back_populates="steps")


class TraceStorage:
    def __init__(self, db_path: Path) -> None:
        self._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self._engine)

    def save_trace(self, trace: Trace) -> None:
        logger.info("Saving trace: %s (agent=%s, steps=%d)", trace.id, trace.agent_name, len(trace.steps))
        with Session(self._engine) as session:
            row = TraceRow(
                id=trace.id,
                agent_name=trace.agent_name,
                created_at=trace.created_at,
                metadata_json=json.dumps(trace.metadata),
            )
            session.add(row)
            for step in trace.steps:
                step_row = StepRow(
                    trace_id=trace.id,
                    index=step.index,
                    step_type=step.step_type.value,
                    name=step.name,
                    input_json=json.dumps(step.input_data),
                    output_json=json.dumps(step.output_data),
                    tokens_in=step.tokens_in,
                    tokens_out=step.tokens_out,
                    cost=step.cost,
                    duration_ms=step.duration_ms,
                    context_json=json.dumps(step.context_snapshot) if step.context_snapshot is not None else None,
                    error=step.error,
                )
                session.add(step_row)
            session.commit()
            logger.debug("Trace %s saved successfully", trace.id)

    def get_trace(self, trace_id: str) -> Trace | None:
        logger.debug("Getting trace: %s", trace_id)
        with Session(self._engine) as session:
            row = session.get(TraceRow, trace_id)
            if row is None:
                logger.debug("Trace not found: %s", trace_id)
                return None
            return self._row_to_trace(row)

    def list_traces(self, limit: int = 50, offset: int = 0) -> list[Trace]:
        logger.debug("Listing traces (limit=%d, offset=%d)", limit, offset)
        with Session(self._engine) as session:
            rows = (
                session.query(TraceRow)
                .order_by(TraceRow.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._row_to_trace(r) for r in rows]

    def delete_trace(self, trace_id: str) -> None:
        logger.info("Deleting trace: %s", trace_id)
        with Session(self._engine) as session:
            row = session.get(TraceRow, trace_id)
            if row is not None:
                session.delete(row)
                session.commit()
                logger.debug("Trace %s deleted", trace_id)

    @staticmethod
    def _row_to_trace(row: TraceRow) -> Trace:
        steps = [
            Step(
                index=s.index,  # type: ignore[arg-type]
                step_type=StepType(s.step_type),  # type: ignore[arg-type]
                name=s.name,  # type: ignore[arg-type]
                input_data=json.loads(s.input_json),  # type: ignore[arg-type]
                output_data=json.loads(s.output_json),  # type: ignore[arg-type]
                tokens_in=s.tokens_in,  # type: ignore[arg-type]
                tokens_out=s.tokens_out,  # type: ignore[arg-type]
                cost=s.cost,  # type: ignore[arg-type]
                duration_ms=s.duration_ms,  # type: ignore[arg-type]
                context_snapshot=json.loads(s.context_json) if s.context_json is not None else None,  # type: ignore[arg-type]
                error=s.error,  # type: ignore[arg-type]
            )
            for s in row.steps
        ]
        return Trace(
            id=row.id,  # type: ignore[arg-type]
            agent_name=row.agent_name,  # type: ignore[arg-type]
            steps=steps,
            created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at,  # type: ignore[arg-type]
            metadata=json.loads(row.metadata_json),  # type: ignore[arg-type]
        )
