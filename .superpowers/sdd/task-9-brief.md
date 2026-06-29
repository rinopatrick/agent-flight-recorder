# Task 9: Integration Test — Full Pipeline

## Context
Tasks 1-8 built all components. This task creates an integration test that verifies the full pipeline: SDK records a trace → storage persists it → backend serves it via API.

## What to Build
An end-to-end integration test that exercises SDK, storage, and backend together.

## Files
- Create: `tests/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_full_pipeline.py`

## Interfaces
- Tests full flow: SDK recording → storage → API retrieval

## Steps

### Step 1: Write integration test
Create `tests/integration/test_full_pipeline.py`:
```python
def test_full_pipeline(tmp_path):
    # 1. Record a trace using SDK
    # 2. Save to storage
    # 3. Serve via API
    # 4. List traces
    # 5. Get full trace detail
    # 6. Verify cost tracking
```

Test should:
- Use `@record` decorator to create a trace with llm_call and tool_call
- Save it to SQLite via TraceStorage (or Database wrapper)
- Create FastAPI app via create_app(db)
- Use TestClient to verify:
  - GET /api/traces returns the trace
  - GET /api/traces/{id} returns full detail with correct steps
  - Total cost matches

### Step 2: Run integration test
```bash
python -m pytest tests/integration/test_full_pipeline.py -v
```
Expected: PASS

### Step 3: Commit
```bash
git add tests/
git commit -m "test: add full pipeline integration test"
```

## Global Constraints
- Python 3.11+, pytest
- All SDK and backend packages must be installed
- tmp_path for database location
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
