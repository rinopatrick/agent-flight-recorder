import time
from typing import Any

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import Step, StepType, Trace


class CrewAIAdapter(BaseAdapter):
    def __init__(self, agent_name: str) -> None:
        self._agent_name = agent_name
        self._steps: list[Step] = []
        self._pending: dict[str, dict[str, Any]] = {}

    def on_agent_start(
        self,
        agent_name: str,
        task_description: str,
        run_id: str,
    ) -> None:
        self._pending[run_id] = {
            "step_type": StepType.OUTPUT,
            "name": agent_name,
            "input_data": {"task": task_description},
            "start_time": time.monotonic(),
        }

    def on_agent_end(
        self,
        agent_name: str,
        result: str,
        run_id: str,
    ) -> None:
        pending = self._pending.pop(run_id, None)
        if pending is None:
            return
        duration_ms = (time.monotonic() - pending["start_time"]) * 1000
        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=pending["step_type"],
                name=pending["name"],
                input_data=pending["input_data"],
                output_data={"result": result},
                duration_ms=duration_ms,
            )
        )

    def on_tool_usage(
        self,
        agent_name: str,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        run_id: str,
    ) -> None:
        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=StepType.TOOL_CALL,
                name=tool_name,
                input_data=input_data,
                output_data=output_data,
            )
        )

    def on_llm_call_start(
        self,
        agent_name: str,
        prompt: str,
        run_id: str,
    ) -> None:
        self._pending[run_id] = {
            "step_type": StepType.LLM_CALL,
            "name": "llm_call",
            "input_data": {"prompt": prompt},
            "start_time": time.monotonic(),
        }

    def on_llm_call_end(
        self,
        agent_name: str,
        response: str,
        tokens_used: dict[str, int] | None,
        run_id: str,
    ) -> None:
        pending = self._pending.pop(run_id)
        duration_ms = (time.monotonic() - pending["start_time"]) * 1000

        tokens_in = None
        tokens_out = None
        if tokens_used:
            tokens_in = tokens_used.get("prompt_tokens")
            tokens_out = tokens_used.get("completion_tokens")

        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=pending["step_type"],
                name=pending["name"],
                input_data=pending["input_data"],
                output_data={"response": response},
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms,
            )
        )

    def build_trace(self) -> Trace:
        return Trace(
            agent_name=self._agent_name,
            steps=list(self._steps),
        )
