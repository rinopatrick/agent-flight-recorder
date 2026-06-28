import functools
import threading
import time
from typing import Any

from flight_recorder.models import Step, StepType, Trace

_last_trace: Trace | None = None
_ctx: threading.local = threading.local()


def get_last_trace() -> Trace | None:
    return _last_trace


def clear_last_trace() -> None:
    global _last_trace
    _last_trace = None


class _RecorderContext:
    def __init__(self, agent_name: str) -> None:
        self._trace = Trace(agent_name=agent_name)
        self._index = 0
        self._context: dict[str, Any] | None = None

    def llm_call(
        self,
        name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost: float = 0.0,
        duration_ms: float = 0.0,
    ) -> None:
        step = Step(
            index=self._index,
            step_type=StepType.LLM_CALL,
            name=name,
            input_data=input_data,
            output_data=output_data,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            duration_ms=duration_ms,
            context_snapshot=self._context,
        )
        self._trace.steps.append(step)
        self._index += 1

    def tool_call(
        self,
        name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        duration_ms: float = 0.0,
    ) -> None:
        step = Step(
            index=self._index,
            step_type=StepType.TOOL_CALL,
            name=name,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            context_snapshot=self._context,
        )
        self._trace.steps.append(step)
        self._index += 1

    def set_context(self, context: dict[str, Any]) -> None:
        self._context = context


def _get_active_ctx() -> _RecorderContext:
    ctx = getattr(_ctx, "active", None)
    if ctx is None:
        raise RuntimeError(
            "record.llm_call/tool_call/set_context must be called inside a @record-decorated function"
        )
    return ctx


class _Record:
    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            global _last_trace
            ctx = _RecorderContext(agent_name=fn.__name__)
            _ctx.active = ctx
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                ctx._trace.steps.append(
                    Step(
                        index=ctx._index,
                        step_type=StepType.OUTPUT,
                        name="output",
                        input_data={"args": str(args), "kwargs": str(kwargs)},
                        output_data={"result": result},
                        duration_ms=duration_ms,
                        context_snapshot=ctx._context,
                    )
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                ctx._trace.steps.append(
                    Step(
                        index=ctx._index,
                        step_type=StepType.ERROR,
                        name="error",
                        input_data={"args": str(args), "kwargs": str(kwargs)},
                        output_data={},
                        duration_ms=duration_ms,
                        error=str(exc),
                        context_snapshot=ctx._context,
                    )
                )
                raise
            finally:
                _last_trace = ctx._trace
                _ctx.active = None

        return wrapper

    def llm_call(self, *args: Any, **kwargs: Any) -> None:
        _get_active_ctx().llm_call(*args, **kwargs)

    def tool_call(self, *args: Any, **kwargs: Any) -> None:
        _get_active_ctx().tool_call(*args, **kwargs)

    def set_context(self, context: dict[str, Any]) -> None:
        _get_active_ctx().set_context(context)


record = _Record()
