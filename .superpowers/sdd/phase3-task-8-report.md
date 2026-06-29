# Phase 3 Task 8: Full Pipeline Integration Test

**Status**: DONE
**Commit**: `13ae99d` — `test: add Phase 3 pipeline integration test`

## Deliverable

Created `tests/integration/test_phase3_pipeline.py` with 7 tests covering the full Phase 3 flow:

| Test | What it verifies |
|------|-----------------|
| `test_record_trace` | @record with llm_call + tool_call steps produces correct step types and data |
| `test_save_and_load_from_db` | Database.save_trace/get_trace round-trip preserves all fields |
| `test_export_import_roundtrip` | export_trace → import_trace preserves IDs, steps, costs, durations |
| `test_fork_imported_trace` | ReplayEngine forks imported trace at step 2 with model modification |
| `test_generate_test_code` | TestGenerator produces valid Python with assert_tool_called, assert_model_used, assert_cost, assert_latency |
| `test_export_import_via_api` | GET /export → POST /import via TestClient with new trace ID |
| `test_full_phase3_pipeline` | End-to-end: record → save → export → import → fork → generate test → API export/import/fork/generate-test |

## Key findings during implementation

- `ReplayEngine.create_branch_from_trace` takes steps **before** `fork_step_index` (`steps[:fork_step_index]`), so fork_step_index=0 yields 0 steps
- `POST /api/traces/import` saves to DB with the trace's original ID — re-importing the same trace requires a different ID to avoid UNIQUE constraint errors
- No `conftest.py` exists; each integration test defines its own fixtures inline (project convention)

## Files touched

- `tests/integration/test_phase3_pipeline.py` (new, 265 lines)
