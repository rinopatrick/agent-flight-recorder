import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, ForeignKey
from sqlalchemy.orm import Session, declarative_base, relationship

from flight_recorder.models import Step, StepType, Trace

Base = declarative_base()


class TraceRow(Base):
    __tablename__ = "traces"

    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")

    steps = relationship("StepRow", back_populates="trace", cascade="all, delete-orphan", order_by="StepRow.index")


class StepRow(Base):
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
        self._engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self._engine)

    def save_trace(self, trace: Trace) -> None:
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

    def get_trace(self, trace_id: str) -> Trace | None:
        with Session(self._engine) as session:
            row = session.get(TraceRow, trace_id)
            if row is None:
                return None
            return self._row_to_trace(row)

    def list_traces(self, limit: int = 50, offset: int = 0) -> list[Trace]:
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
        with Session(self._engine) as session:
            row = session.get(TraceRow, trace_id)
            if row is not None:
                session.delete(row)
                session.commit()

    @staticmethod
    def _row_to_trace(row: TraceRow) -> Trace:
        steps = [
            Step(
                index=s.index,
                step_type=StepType(s.step_type),
                name=s.name,
                input_data=json.loads(s.input_json),
                output_data=json.loads(s.output_json),
                tokens_in=s.tokens_in,
                tokens_out=s.tokens_out,
                cost=s.cost,
                duration_ms=s.duration_ms,
                context_snapshot=json.loads(s.context_json) if s.context_json is not None else None,
                error=s.error,
            )
            for s in row.steps
        ]
        return Trace(
            id=row.id,
            agent_name=row.agent_name,
            steps=steps,
            created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at,
            metadata=json.loads(row.metadata_json),
        )
