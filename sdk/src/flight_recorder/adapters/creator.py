from typing import Any, Callable, Optional

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import Step, StepType, Trace


def build_step(
    step_type: StepType | str,
    name: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    *,
    index: int = 0,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost: float = 0.0,
    duration_ms: float = 0.0,
    error: Optional[str] = None,
) -> Step:
    if isinstance(step_type, str):
        step_type = StepType(step_type)
    return Step(
        index=index,
        step_type=step_type,
        name=name,
        input_data=input_data,
        output_data=output_data,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
        duration_ms=duration_ms,
        error=error,
    )


class _DynamicAdapter(BaseAdapter):
    def __init__(
        self,
        name: str,
        event_handlers: dict[str, Callable[..., Optional[Step]]],
    ) -> None:
        self._name = name
        self._event_handlers = dict(event_handlers)
        self._steps: list[Step] = []

    def handle_event(self, event: str, **kwargs: Any) -> None:
        handler = self._event_handlers.get(event)
        if handler is None:
            raise ValueError(f"Unknown event: {event!r}")
        step = handler(**kwargs)
        if step is not None:
            step.index = len(self._steps)
            self._steps.append(step)

    def build_trace(self) -> Trace:
        return Trace(
            agent_name=self._name,
            steps=list(self._steps),
        )


def create_adapter(
    name: str,
    event_handlers: dict[str, Callable[..., Optional[Step]]],
) -> BaseAdapter:
    return _DynamicAdapter(name=name, event_handlers=event_handlers)
