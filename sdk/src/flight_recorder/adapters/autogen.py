from typing import Any

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import Step, StepType, Trace


class AutoGenAdapter(BaseAdapter):
    def __init__(self, agent_name: str, metadata: dict[str, Any] | None = None) -> None:
        self._agent_name = agent_name
        self._metadata = metadata or {}
        self._steps: list[Step] = []

    def on_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        is_tool_call: bool = False,
    ) -> None:
        step_type = StepType.TOOL_CALL if is_tool_call else StepType.OUTPUT
        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=step_type,
                name=f"{sender} -> {receiver}",
                input_data={"sender": sender, "receiver": receiver},
                output_data={"content": content},
            )
        )

    def on_llm_call(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        tokens: dict[str, int] | None = None,
    ) -> None:
        tokens_in = tokens.get("prompt_tokens") if tokens else None
        tokens_out = tokens.get("completion_tokens") if tokens else None

        self._steps.append(
            Step(
                index=len(self._steps),
                step_type=StepType.LLM_CALL,
                name=agent_name,
                input_data={"prompt": prompt},
                output_data={"response": response},
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
        )

    def build_trace(self) -> Trace:
        return Trace(
            agent_name=self._agent_name,
            steps=list(self._steps),
            metadata=dict(self._metadata),
        )
