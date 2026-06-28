from typing import Any

from flight_recorder.models import Branch, Step, Trace


class ReplayEngine:
    def create_branch_from_trace(
        self,
        trace: Trace,
        fork_step_index: int,
        name: str,
        modifications: dict[str, Any] | None = None,
    ) -> Branch:
        modifications = modifications or {}
        copied_steps = []
        for step in trace.steps[:fork_step_index]:
            copied_steps.append(self.apply_modification(step, modifications))

        return Branch(
            name=name,
            parent_trace_id=trace.id,
            fork_step_index=fork_step_index,
            modifications=modifications,
            steps=copied_steps,
        )

    def apply_modification(self, step: Step, modifications: dict[str, Any]) -> Step:
        updates: dict[str, Any] = {}
        if "model" in modifications:
            updates["name"] = modifications["model"]
        if "prompt" in modifications:
            updates["input_data"] = {**step.input_data, "prompt": modifications["prompt"]}
        if "context" in modifications:
            updates["context_snapshot"] = modifications["context"]

        if not updates:
            return step.model_copy()
        return step.model_copy(update=updates)

    def compare_branches(self, branch_a: Branch, branch_b: Branch) -> dict[str, Any]:
        cost_diff = branch_a.total_cost() - branch_b.total_cost()
        duration_diff = branch_a.total_duration_ms() - branch_b.total_duration_ms()
        step_count_diff = len(branch_a.steps) - len(branch_b.steps)

        max_steps = max(len(branch_a.steps), len(branch_b.steps))
        output_diffs = []
        for i in range(max_steps):
            a_out = branch_a.steps[i].output_data if i < len(branch_a.steps) else {}
            b_out = branch_b.steps[i].output_data if i < len(branch_b.steps) else {}
            output_diffs.append(
                {
                    "step_index": i,
                    "different": a_out != b_out,
                    "branch_a_output": a_out,
                    "branch_b_output": b_out,
                }
            )

        return {
            "cost_diff": cost_diff,
            "duration_diff": duration_diff,
            "step_count_diff": step_count_diff,
            "output_diffs": output_diffs,
        }
