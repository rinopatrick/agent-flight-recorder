from typing import Any

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import Step, StepType, Trace


class LangGraphAdapter(BaseAdapter):
    def __init__(self, agent_name: str) -> None:
        self._agent_name = agent_name
        self._steps: list[Step] = []

    def record_node(
        self,
        node_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        cost: float = 0.0,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> None:
        step = Step(
            index=len(self._steps),
            step_type=StepType.TOOL_CALL,
            name=node_name,
            input_data=input_data,
            output_data=output_data,
            cost=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        self._steps.append(step)

    def record_conditional_edge(
        self,
        edge_name: str,
        chosen_path: str,
        input_data: dict[str, Any],
    ) -> None:
        step = Step(
            index=len(self._steps),
            step_type=StepType.REASONING,
            name=edge_name,
            input_data=input_data,
            output_data={"chosen_path": chosen_path},
        )
        self._steps.append(step)

    def build_trace(self) -> Trace:
        return Trace(
            agent_name=self._agent_name,
            steps=list(self._steps),
        )
