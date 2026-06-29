# Hardening Tasks 4-5 Report

## Task 4: Linting

### Ruff Configuration
- Created `sdk/ruff.toml` with rules: E, F, I, W (ignoring E501 line length)
- Created `backend/ruff.toml` with rules: E, F, I, W (ignoring E501 line length)

### Dependencies Updated
- Added `ruff>=0.4.0` to `sdk/pyproject.toml` dev dependencies
- Added `ruff>=0.4.0` to `backend/pyproject.toml` dev dependencies

### Pre-commit Configuration
- Created `.pre-commit-config.yaml` at project root with ruff hooks:
  - `ruff` for linting with auto-fix
  - `ruff-format` for formatting

### Linting Results
- **SDK**: Found 21 errors, all 21 fixed
- **Backend**: Found 6 errors, all 6 fixed

## Task 5: SQLite Performance

### Indexes Added

#### `sdk/src/flight_recorder/storage.py`
- Added index on `traces.agent_name` column
- Added index on `traces.created_at` column
- `steps.trace_id` index already existed

#### `sdk/src/flight_recorder/branch_storage.py`
- `branches.parent_trace_id` index already existed
- Added index on `branches.created_at` column

### Connection Pooling
- Added `check_same_thread=False` to both `TraceStorage` and `BranchStorage` engines
- Enables multi-threaded access for concurrent operations

## Files Modified

1. `sdk/ruff.toml` (created)
2. `backend/ruff.toml` (created)
3. `.pre-commit-config.yaml` (created)
4. `sdk/pyproject.toml` (updated dev dependencies)
5. `backend/pyproject.toml` (updated dev dependencies)
6. `sdk/src/flight_recorder/storage.py` (added indexes + connection args)
7. `sdk/src/flight_recorder/branch_storage.py` (added index + connection args)
8. Various SDK and backend source files (ruff auto-fixes)

## Verification

- Ruff linting passes for both sdk and backend
- All indexes are defined declaratively via SQLAlchemy
- Connection pooling enabled for multi-threaded SQLite access
