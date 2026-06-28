# Phase 3 Task 4: Export/Import API Endpoints

## Status: DONE

## What was implemented

### Endpoints added to `backend/src/flight_recorder_backend/server.py`

- **GET `/api/traces/{trace_id}/export`** — Returns full trace as JSON dict using `export_trace` from SDK. Returns 404 if trace not found.
- **POST `/api/traces/import`** — Accepts trace JSON dict, validates via `import_trace` from SDK, saves to DB, returns the imported trace as JSON. Returns 400 on invalid input.

### Tests added to `backend/tests/test_server.py`

- `test_export_trace` — Export returns full trace data (id, agent_name, steps, created_at, metadata)
- `test_export_trace_not_found` — 404 for nonexistent trace
- `test_import_trace` — Import creates trace in DB with correct data
- `test_import_trace_invalid_data` — 400 for malformed import payload
- `test_export_import_roundtrip` — Export then import into fresh DB preserves all data

## Key decisions

- Import preserves the original trace ID from the exported data (no ID regeneration)
- Import endpoint catches `KeyError`/`ValueError` from SDK and returns 400
- Roundtrip test uses a separate Database instance to avoid UNIQUE constraint conflicts

## Verification

- All 24 tests pass (18 existing + 5 new + 1 existing)
- `pip install -e ./sdk -e ./backend` successful
