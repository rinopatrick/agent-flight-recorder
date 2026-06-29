# Task 1: Branch Data Model (Python SDK)

## Context
Phase 1 MVP is complete with Trace/Step models. Phase 2 adds branch/fork execution. This task adds the Branch data model.

## What to Build
Add `Branch` model to `sdk/src/flight_recorder/models.py`.

## Files
- Modify: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_branch_models.py`

## Steps (TDD)

### Step 1: Write failing tests
Create `sdk/tests/test_branch_models.py` with:
- `test_branch_creation` — create Branch with name, parent_trace_id, fork_step_index, modifications, verify fields and auto-generated id
- `test_branch_with_steps` — create Branch with steps, verify total_cost()
- `test_branch_total_cost` — verify cost and duration aggregation

### Step 2: Run tests to verify they fail

### Step 3: Add Branch model to models.py
- `Branch(BaseModel)` with: id (uuid hex[:12]), name, parent_trace_id, fork_step_index, modifications (dict), steps (list[Step]), created_at
- `total_cost()` and `total_duration_ms()` methods (same pattern as Trace)

### Step 4: Run tests to verify they pass

### Step 5: Commit: `feat(sdk): add Branch model for fork execution`

## Work from: `C:\Users\patri\agent-flight-recorder`
