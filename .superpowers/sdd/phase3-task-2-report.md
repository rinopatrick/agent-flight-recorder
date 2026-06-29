# Phase 3 Task 2: Test Generator API Endpoint — Report

**Status**: Done
**Commit**: `eb29637` — `feat(backend): add test generation API endpoint`

## What was added

### Endpoint: `POST /api/traces/{trace_id}/generate-test`

- **File**: `backend/src/flight_recorder_backend/server.py:124-130`
- Returns 404 if trace not found
- Uses `TestGenerator.generate_test(trace)` to produce test code
- Returns `{"test_code": "...", "trace_id": "..."}`

### Tests

- **File**: `backend/tests/test_server.py` — 3 new tests
  - `test_generate_test` — happy path, checks response shape
  - `test_generate_test_not_found` — 404 on missing trace
  - `test_generate_test_contains_assertions` — verifies generated code includes expected assertions

### Test results

```
19 passed in 1.51s
```
