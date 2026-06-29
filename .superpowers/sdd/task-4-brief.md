# Task 4: Python SDK Core — @record Decorator

## Context
Tasks 2-3 created models and storage. This task builds the core `@record` decorator that developers use to instrument their agents.

## What to Build
A `@record` decorator that wraps agent functions and captures LLM calls, tool calls, and output steps.

## Files
- Create: `sdk/src/flight_recorder/recorder.py`
- Update: `sdk/src/flight_recorder/__init__.py` (add exports)
- Create: `sdk/tests/test_recorder.py`

## Interfaces
- Consumes: `Trace`, `Step`, `StepType` from models
- Produces:
  - `@record` decorator
  - `get_last_trace() -> Trace | None`
  - `clear_last_trace() -> None`
  - Inside decorated functions: `record.llm_call(...)`, `record.tool_call(...)`, `record.set_context(...)`

## Steps (TDD)

### Step 1: Write failing tests
Create `sdk/tests/test_recorder.py`:
- `test_record_captures_function_call` — decorate a simple function, verify trace is created with output step
- `test_record_captures_llm_simulation` — use `record.llm_call()` inside decorated function, verify LLM step captured
- `test_record_captures_tool_call` — use `record.tool_call()` inside, verify tool step captured
- `test_record_stores_context` — use `record.set_context()`, verify context_snapshot stored
- `test_record_no_trace_by_default` — verify get_last_trace() is None before any call

### Step 2: Run tests to verify they fail
```bash
cd sdk && python -m pytest tests/test_recorder.py -v
```

### Step 3: Implement recorder
Create `sdk/src/flight_recorder/recorder.py`:
- Module-level `_last_trace` variable
- `_RecorderContext` class with `llm_call()`, `tool_call()`, `set_context()` methods
- `record(fn)` decorator that:
  - Creates a `_RecorderContext` for the function call
  - Wraps the function, captures timing
  - Appends an OUTPUT step at the end
  - Sets `_last_trace` in finally block
  - Attaches `llm_call`, `tool_call`, `set_context` to the wrapper so they can be called inside the decorated function

### Step 4: Run tests to verify they pass
```bash
cd sdk && python -m pytest tests/test_recorder.py -v
```
Expected: 5 passed

### Step 5: Update __init__.py
Add exports: `record`, `get_last_trace`, `clear_last_trace`

### Step 6: Commit
```bash
git add sdk/src/flight_recorder/ sdk/tests/test_recorder.py
git commit -m "feat(sdk): add @record decorator with llm_call, tool_call, set_context"
```

## Global Constraints
- Python 3.11+, Pydantic v2
- TDD: write failing test first
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
