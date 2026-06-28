import json
from datetime import datetime
from pathlib import Path
from typing import Any

from flight_recorder.models import Step, StepType, Trace


def _serialize_step(step: Step) -> dict[str, Any]:
    return {
        "index": step.index,
        "step_type": step.step_type.value,
        "name": step.name,
        "input_data": step.input_data,
        "output_data": step.output_data,
        "tokens_in": step.tokens_in,
        "tokens_out": step.tokens_out,
        "cost": step.cost,
        "duration_ms": step.duration_ms,
        "context_snapshot": step.context_snapshot,
        "error": step.error,
    }


def _deserialize_step(data: dict[str, Any]) -> Step:
    return Step(
        index=data["index"],
        step_type=StepType(data["step_type"]),
        name=data["name"],
        input_data=data["input_data"],
        output_data=data["output_data"],
        tokens_in=data.get("tokens_in"),
        tokens_out=data.get("tokens_out"),
        cost=data.get("cost", 0.0),
        duration_ms=data.get("duration_ms", 0.0),
        context_snapshot=data.get("context_snapshot"),
        error=data.get("error"),
    )


def export_trace(trace: Trace) -> dict[str, Any]:
    return {
        "id": trace.id,
        "agent_name": trace.agent_name,
        "steps": [_serialize_step(s) for s in trace.steps],
        "created_at": trace.created_at.isoformat(),
        "metadata": trace.metadata,
    }


def import_trace(data: dict[str, Any]) -> Trace:
    return Trace(
        id=data["id"],
        agent_name=data["agent_name"],
        steps=[_deserialize_step(s) for s in data["steps"]],
        created_at=datetime.fromisoformat(data["created_at"]),
        metadata=data.get("metadata", {}),
    )


def export_to_file(trace: Trace, path: Path) -> None:
    data = export_trace(trace)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def import_from_file(path: Path) -> Trace:
    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return import_trace(data)
