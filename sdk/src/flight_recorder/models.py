import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    OUTPUT = "output"
    ERROR = "error"
    REASONING = "reasoning"


class Step(BaseModel):
    index: int
    step_type: StepType
    name: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost: float = 0.0
    duration_ms: float = 0.0
    context_snapshot: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class Trace(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_name: str
    steps: list[Step] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def total_cost(self) -> float:
        return sum(step.cost for step in self.steps)

    def total_duration_ms(self) -> float:
        return sum(step.duration_ms for step in self.steps)
