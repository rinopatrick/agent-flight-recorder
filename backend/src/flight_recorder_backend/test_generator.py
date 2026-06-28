from flight_recorder.models import StepType, Trace


class TestGenerator:
    def generate_test(self, trace: Trace) -> str:
        func_name = f"test_agent_{trace.agent_name}_{trace.id[:6]}"
        lines = [f"def {func_name}():", '    result = run_agent("original input")']

        for step in trace.steps:
            if step.step_type == StepType.TOOL_CALL:
                args_repr = repr(step.input_data)
                lines.append(
                    f'    assert_tool_called(result, "{step.name}", {args_repr})'
                )
            elif step.step_type == StepType.LLM_CALL:
                lines.append(f'    assert_model_used(result, "{step.name}")')

        total_cost = trace.total_cost()
        max_cost = round(total_cost * 1.1, 4)
        lines.append(f"    assert_cost(result, max_cost={max_cost})")

        total_duration = trace.total_duration_ms()
        max_ms = round(total_duration * 1.1, 1)
        lines.append(f"    assert_latency(result, max_ms={max_ms})")

        return "\n".join(lines) + "\n"
