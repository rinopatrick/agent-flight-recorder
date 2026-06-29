import time
from typing import Any

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import Step, StepType, Trace


class LangChainAdapter(BaseAdapter):
    def __init__(self, agent_name: str) -> None:
        self._agent_name = agent_name
        self._steps: list[Step] = []
        self._pending: dict[str, dict[str, Any]] = {}

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        run_id: str,
    ) -> None:
        name = serialized.get("name", "unknown")
        self._pending[run_id] = {
            "step_type": StepType.LLM_CALL,
            "name": name,
            "input_data": {"prompts": prompts},
            "start_time": time.monotonic(),
        }

    def on_llm_end(
        self,
        output: dict[str, Any],
        run_id: str,
    ) -> None:
        pending = self._pending.pop(run_id)
        duration_ms = (time.monotonic() - pending["start_time"]) * 1000

        tokens_in = None
        tokens_out = None
        llm_output = output.get("llm_output")
        if llm_output and "token_usage" in llm_output:
            usage = llm_output["token_usage"]
            tokens_in = usage.get("prompt_tokens")
            tokens_out = usage.get("completion_tokens")

        generations = output.get("generations", [])
        response_text = ""
        if generations and generations[0]:
            response_text = generations[0][0].get("text", "")

        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=pending["step_type"],
                name=pending["name"],
                input_data=pending["input_data"],
                output_data={"response": response_text},
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms,
            )
        )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: str,
    ) -> None:
        name = serialized.get("name", "unknown")
        self._pending[run_id] = {
            "step_type": StepType.TOOL_CALL,
            "name": name,
            "input_data": {"input": input_str},
            "start_time": time.monotonic(),
        }

    def on_tool_end(
        self,
        output: str,
        run_id: str,
    ) -> None:
        pending = self._pending.pop(run_id)
        duration_ms = (time.monotonic() - pending["start_time"]) * 1000

        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=pending["step_type"],
                name=pending["name"],
                input_data=pending["input_data"],
                output_data={"output": output},
                duration_ms=duration_ms,
            )
        )

    def build_trace(self) -> Trace:
        return Trace(
            agent_name=self._agent_name,
            steps=list(self._steps),
        )
