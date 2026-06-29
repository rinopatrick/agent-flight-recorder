# Phase 2 Task 9: AutoGen Adapter

## Status: DONE

## Commit
- `eaec887` feat(sdk): add AutoGen adapter

## Test Summary
9/9 tests pass, 40/40 full SDK suite passes (no regressions)

## Files Created/Modified
- `sdk/src/flight_recorder/adapters/autogen.py` — AutoGenAdapter with on_message, on_llm_call, build_trace
- `sdk/src/flight_recorder/adapters/__init__.py` — added AutoGenAdapter export
- `sdk/tests/test_autogen_adapter.py` — 9 tests covering subclass, messages, tool calls, LLM calls, ordering, metadata, empty trace
