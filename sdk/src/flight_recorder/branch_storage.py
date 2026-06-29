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

from flight_recorder.models import Branch, Step, StepType

Base = declarative_base()


class BranchRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "branches"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    parent_trace_id = Column(String, nullable=False, index=True)
    fork_step_index = Column(Integer, nullable=False)
    modifications_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, index=True)

    steps = relationship("BranchStepRow", back_populates="branch", cascade="all, delete-orphan", order_by="BranchStepRow.index")


class BranchStepRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "branch_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(String, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
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

    branch = relationship("BranchRow", back_populates="steps")


class BranchStorage:
    def __init__(self, db_path: Path | None = None, db_url: str | None = None) -> None:
        if db_url:
            self._engine = create_engine(db_url)
        elif db_path:
            self._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        else:
            raise ValueError("Either db_path or db_url must be provided")
        Base.metadata.create_all(self._engine)

    def save_branch(self, branch: Branch) -> None:
        with Session(self._engine) as session:
            row = BranchRow(
                id=branch.id,
                name=branch.name,
                parent_trace_id=branch.parent_trace_id,
                fork_step_index=branch.fork_step_index,
                modifications_json=json.dumps(branch.modifications),
                created_at=branch.created_at,
            )
            session.add(row)
            for step in branch.steps:
                step_row = BranchStepRow(
                    branch_id=branch.id,
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

    def get_branch(self, branch_id: str) -> Branch | None:
        with Session(self._engine) as session:
            row = session.get(BranchRow, branch_id)
            if row is None:
                return None
            return self._row_to_branch(row)

    def list_branches(self, limit: int = 50, offset: int = 0) -> list[Branch]:
        with Session(self._engine) as session:
            rows = (
                session.query(BranchRow)
                .order_by(BranchRow.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._row_to_branch(r) for r in rows]

    def list_branches_for_trace(self, trace_id: str) -> list[Branch]:
        with Session(self._engine) as session:
            rows = (
                session.query(BranchRow)
                .filter(BranchRow.parent_trace_id == trace_id)
                .order_by(BranchRow.created_at.desc())
                .all()
            )
            return [self._row_to_branch(r) for r in rows]

    def delete_branch(self, branch_id: str) -> None:
        with Session(self._engine) as session:
            row = session.get(BranchRow, branch_id)
            if row is not None:
                session.delete(row)
                session.commit()

    @staticmethod
    def _row_to_branch(row: BranchRow) -> Branch:
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
        return Branch(
            id=row.id,  # type: ignore[arg-type]
            name=row.name,  # type: ignore[arg-type]
            parent_trace_id=row.parent_trace_id,  # type: ignore[arg-type]
            fork_step_index=row.fork_step_index,  # type: ignore[arg-type]
            modifications=json.loads(row.modifications_json),  # type: ignore[arg-type]
            steps=steps,
            created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at,  # type: ignore[arg-type]
        )
