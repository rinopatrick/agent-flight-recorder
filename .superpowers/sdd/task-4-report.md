# Task 4 Report: Python SDK Core — @record Decorator

## Status: DONE

## Commit
- `15f7f47` feat(sdk): add @record decorator with llm_call, tool_call, set_context

## Test Summary
6 passed, 0 failed — `sdk/tests/test_recorder.py`

## Implementation

### Design: `_Record` callable class
- `record` is an instance of `_Record` — callable (so `@record` works as a decorator) and exposes `record.llm_call()`, `record.tool_call()`, `record.set_context()` methods.
- Uses `threading.local()` to track the active `_RecorderContext` per-thread, so nested/concurrent calls are isolated.
- `_RecorderContext` accumulates `Step` objects into a `Trace`; the OUTPUT step (or ERROR step) is appended after the function returns.

### Error handling
- If the decorated function raises, an ERROR step is captured with the exception message, then the exception is re-raised.
- `get_last_trace()` is set in the `finally` block so traces are always recorded.

### Thread safety
- `_ctx.active` is a `threading.local` attribute — each thread gets its own active context.

## Files Created/Modified
- `sdk/src/flight_recorder/recorder.py` — new
- `sdk/tests/test_recorder.py` — new
- `sdk/src/flight_recorder/__init__.py` — updated exports

## Concerns
- None.
