# Task 2: Trace Data Model (Python SDK)

## Context
This is the second task in the Agent Flight Recorder project. The monorepo structure is already set up (Task 1). This task creates the core data models that ALL subsequent Python tasks depend on.

## What to Build
Create Pydantic models for `Trace`, `Step`, and `StepType` in the SDK package.

## Files
- Create: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_models.py`

## Interfaces Produced
- `StepType` enum: `LLM_CALL`, `TOOL_CALL`, `OUTPUT`, `ERROR`, `REASONING`
- `Step` model: index, step_type, name, input_data, output_data, tokens_in, tokens_out, cost, duration_ms, context_snapshot, error
- `Trace` model: id, agent_name, steps, created_at, metadata
- `Trace.total_cost()` -> float
- `Trace.total_duration_ms()` -> float

## Steps (TDD)

### Step 1: Write failing tests
Create `sdk/tests/test_models.py` with these test cases:
- `test_step_creation` — create a Step, verify all fields
- `test_trace_creation` — create a Trace with steps, verify id auto-generated
- `test_trace_total_cost` — verify `total_cost()` sums step costs
- `test_step_context_snapshot` — verify context_snapshot is optional dict

### Step 2: Run tests to verify they fail
```bash
cd sdk && python -m pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'flight_recorder.models'`

### Step 3: Implement models
Create `sdk/src/flight_recorder/models.py` with:
- `StepType(str, Enum)` with values: llm_call, tool_call, output, error, reasoning
- `Step(BaseModel)` with all fields listed above, context_snapshot optional
- `Trace(BaseModel)` with id as uuid hex[:12], created_at with timezone-aware default, metadata dict
- `total_cost()` sums step.cost, `total_duration_ms()` sums step.duration_ms

### Step 4: Run tests to verify they pass
```bash
cd sdk && python -m pytest tests/test_models.py -v
```
Expected: 4 passed

### Step 5: Commit
```bash
git add sdk/src/flight_recorder/models.py sdk/tests/test_models.py
git commit -m "feat(sdk): add trace data models with Step and Trace"
```

## Global Constraints
- Python 3.11+, Pydantic v2, SQLAlchemy 2.0
- TDD: write failing test first
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
