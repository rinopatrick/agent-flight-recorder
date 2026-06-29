# Phase 3 Task 1 Report: Test Generator

## Status: DONE

## Commits
- `15b081a` feat(backend): add test generator for traces

## Test Summary
16/16 tests passing — covers function naming, tool_call assertions, llm_call assertions, cost/duration margins, empty traces, and generated code validity (ast.parse).

## Files Created
- `backend/src/flight_recorder_backend/test_generator.py` — TestGenerator class with `generate_test(trace) -> str`
- `backend/tests/test_test_generator.py` — 16 TDD tests

## Design
- `generate_test()` produces a valid pytest function string
- Function name: `test_agent_{agent_name}_{trace.id[:6]}`
- Tool call steps → `assert_tool_called(result, name, args)`
- LLM call steps → `assert_model_used(result, model_name)`
- Cost assertion: `assert_cost(result, max_cost=sum*1.1)` (10% margin)
- Duration assertion: `assert_latency(result, max_ms=sum*1.1)` (10% margin)

## Concerns
None.
