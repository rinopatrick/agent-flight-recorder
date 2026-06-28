# Hardening Task 1: API Security — Complete

## Changes Made

### `backend/src/flight_recorder_backend/server.py`
1. **CORS middleware** — `CORSMiddleware` added with `allow_origins=["*"]`, all methods/headers, credentials enabled
2. **API key authentication** — Optional `FLIGHT_RECORDER_API_KEY` env var. If set, requires `Authorization: Bearer <key>`. If unset, all requests pass (local dev mode). Applied via `verify_api_key` dependency on all endpoints except `/api/health`.
3. **Rate limiting** — `slowapi` middleware with `100/minute` default. Configurable via `FLIGHT_RECORDER_RATE_LIMIT` env var. Applied to all endpoints via `@limiter.limit(RATE_LIMIT)`.
4. **Request validation** — Added `ImportTraceRequest(BaseModel)` with `data: dict` field. `POST /api/traces/import` now accepts `{ "data": <trace_export> }` instead of raw dict.

### `backend/pyproject.toml`
- Added `slowapi>=0.1.9` to dependencies

### `backend/tests/test_server.py`
- Updated 3 import-related tests to wrap payloads in `{"data": ...}` matching new `ImportTraceRequest` schema

## Test Results
- **52/52 tests pass**
- 275 deprecation warnings (slowapi uses deprecated `asyncio.iscoroutinefunction` — upstream issue, not blocking)

## Environment Variables
| Variable | Default | Description |
|---|---|---|
| `FLIGHT_RECORDER_API_KEY` | None (disabled) | Bearer token for API auth |
| `FLIGHT_RECORDER_RATE_LIMIT` | `100/minute` | Slowapi rate limit string |

## Breaking Change
`POST /api/traces/import` body changed from raw dict to `{"data": <dict>}`. Tests updated accordingly.
