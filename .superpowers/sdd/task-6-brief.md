# Task 6: gRPC Backend Server

## Context
Tasks 2-5 built the SDK (models, storage, @record, LangChain adapter). This task creates the Python backend server that serves trace data via REST API (FastAPI). The Rust desktop app will consume this API.

## What to Build
A FastAPI server with REST endpoints for listing and retrieving traces.

## Files
- Create: `backend/src/flight_recorder_backend/__init__.py`
- Create: `backend/src/flight_recorder_backend/db.py`
- Create: `backend/src/flight_recorder_backend/server.py`
- Create: `backend/tests/test_server.py`

## Interfaces
- Consumes: `Trace`, `Step` models and `TraceStorage` from the SDK package
- Produces: FastAPI app with:
  - `GET /api/traces` — list traces (returns summary: id, agent_name, step_count, created_at, total_cost)
  - `GET /api/traces/{trace_id}` — get full trace detail with all steps
  - `GET /api/health` — health check

## Steps (TDD)

### Step 1: Write failing tests
Create `backend/tests/test_server.py`:
- `test_list_traces_empty` — GET /api/traces returns empty list
- `test_list_traces_with_data` — save 2 traces, GET returns 2 items
- `test_get_trace` — save trace, GET by id returns full detail
- `test_get_trace_not_found` — GET nonexistent id returns 404

Use `tmp_path` for database and `TestClient` from FastAPI.

### Step 2: Run tests to verify they fail
```bash
cd backend && python -m pytest tests/test_server.py -v
```

### Step 3: Implement database wrapper
Create `backend/src/flight_recorder_backend/db.py`:
- `Database(TraceStorage)` — thin wrapper (just inherits, no extra logic)

### Step 4: Implement FastAPI server
Create `backend/src/flight_recorder_backend/server.py`:
- `create_app(db: Database) -> FastAPI` factory function
- `/api/traces` returns list of summaries (dict with id, agent_name, step_count, created_at, total_cost)
- `/api/traces/{trace_id}` returns full trace with steps (each step as dict with all fields)
- `/api/health` returns `{"status": "ok"}`
- 404 for missing traces

### Step 5: Run tests to verify they pass
```bash
cd backend && python -m pytest tests/test_server.py -v
```
Expected: 4 passed

### Step 6: Commit
```bash
git add backend/
git commit -m "feat(backend): add FastAPI server with trace API endpoints"
```

## Global Constraints
- Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2
- TDD: write failing test first
- The SDK package must be installed (`pip install -e ./sdk`)
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
