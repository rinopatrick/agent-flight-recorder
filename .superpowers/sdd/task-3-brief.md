# Task 3: SQLite Storage Layer (Python SDK)

## Context
Task 2 created the data models (Trace, Step, StepType). This task builds the SQLite persistence layer that saves and retrieves traces.

## What to Build
A `TraceStorage` class that persists `Trace` objects to SQLite using SQLAlchemy.

## Files
- Create: `sdk/src/flight_recorder/storage.py`
- Create: `sdk/tests/test_storage.py`

## Interfaces
- Consumes: `Trace`, `Step`, `StepType` from `flight_recorder.models`
- Produces: `TraceStorage(db_path: Path)` class with:
  - `save_trace(trace: Trace) -> None`
  - `get_trace(trace_id: str) -> Trace | None`
  - `list_traces(limit: int = 50, offset: int = 0) -> list[Trace]`
  - `delete_trace(trace_id: str) -> None`

## Steps (TDD)

### Step 1: Write failing tests
Create `sdk/tests/test_storage.py` with these tests:
- `test_save_and_get_trace` — save a trace, retrieve it, verify all fields match
- `test_list_traces` — save 2 traces, list them
- `test_list_traces_with_limit` — save 5, list with limit=2, verify 2 returned
- `test_delete_trace` — save, delete, verify get returns None
- `test_get_nonexistent_trace` — get with bad id returns None

Use `tmp_path` fixture for database location.

### Step 2: Run tests to verify they fail
```bash
cd sdk && python -m pytest tests/test_storage.py -v
```

### Step 3: Implement storage
Create `sdk/src/flight_recorder/storage.py`:
- SQLAlchemy ORM: `TraceRow` (id, agent_name, created_at, metadata_json) and `StepRow` (trace_id, index, step_type, name, input_json, output_json, tokens_in, tokens_out, cost, duration_ms, context_json, error)
- `TraceStorage.__init__` creates engine and tables
- `save_trace` inserts TraceRow + all StepRows in one session
- `get_trace` reads TraceRow + ordered StepRows, reconstructs Trace model
- `list_traces` returns traces ordered by created_at desc
- `delete_trace` removes StepRows then TraceRow

### Step 4: Run tests to verify they pass
```bash
cd sdk && python -m pytest tests/test_storage.py -v
```
Expected: 5 passed

### Step 5: Commit
```bash
git add sdk/src/flight_recorder/storage.py sdk/tests/test_storage.py
git commit -m "feat(sdk): add SQLite trace storage layer"
```

## Global Constraints
- Python 3.11+, Pydantic v2, SQLAlchemy 2.0
- TDD: write failing test first
- Local SQLite only, no cloud
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
