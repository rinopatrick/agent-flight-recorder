# Hardening Tasks 2-3 Report

## Task 2: Structured Logging — DONE

### Changes
- **`sdk/src/flight_recorder/log_config.py`** — New shared logging config module. Creates loggers with configurable level via `FLIGHT_RECORDER_LOG_LEVEL` env var (default: `INFO`). Uses standard Python `logging` module with `StreamHandler` and structured format.

- **`sdk/src/flight_recorder/recorder.py`** — Logs recording start/end with agent name and step count. Logs each LLM call and tool call step captured (debug level).

- **`sdk/src/flight_recorder/storage.py`** — Logs `save_trace`, `get_trace`, `list_traces`, `delete_trace` operations with trace IDs and parameters.

- **`backend/src/flight_recorder_backend/server.py`** — Added `RequestLoggingMiddleware` (Starlette `BaseHTTPMiddleware`) that logs every HTTP request/response with method, path, status code, and duration in ms.

- **`backend/src/flight_recorder_backend/db.py`** — Logs database initialization with path.

### Log level configuration
```bash
export FLIGHT_RECORDER_LOG_LEVEL=DEBUG  # default is INFO
```

## Task 3: Type Safety — DONE

### Changes
- **`sdk/mypy.ini`** — mypy config for SDK with `disallow_untyped_defs`, `warn_return_any`, `check_untyped_defs`.
- **`backend/mypy.ini`** — mypy config for backend with same settings + `ignore_missing_imports` for slowapi/grpcio.
- **`sdk/pyproject.toml`** — Added `mypy>=1.0` to dev dependencies.
- **`backend/pyproject.toml`** — Added `mypy>=1.0` to dev dependencies.
- **`sdk/src/flight_recorder/py.typed`** — PEP 561 marker file for typed package.

### mypy results
- SDK: `Success: no issues found in 13 source files`
- Backend: `Success: no issues found in 7 source files`

### Type fixes applied
- SQLAlchemy `declarative_base()` classes annotated with `# type: ignore[misc, valid-type]`
- SQLAlchemy row attribute accesses annotated with `# type: ignore[arg-type]`
- `_RecorderContext` lookup explicitly typed
- `_Record.__call__` annotated with `# type: ignore[no-untyped-def]`
- Rate limit handler annotated with `# type: ignore[override]` and `# type: ignore[arg-type]`

## Verification
- All 70 SDK tests pass
- All 52 backend tests pass
- mypy clean on both packages
