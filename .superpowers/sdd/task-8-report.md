# Task 8 Report: Connect Desktop to Backend — Fetch Traces

## Status: DONE

## Commits
- `f86e15f` feat(desktop): connect to backend API, fetch and display traces

## Test Summary
- `cargo build` — compiles successfully (1 warning about unused `id`/`agent_name` fields in `TraceDetail`, harmless)

## Changes Made

### `desktop/src/app.rs`
1. Added `serde::Deserialize` derive to `TraceSummary`, `TraceDetail`, `StepDetail`
2. Fixed backend URL from `50051` to `8420` (defined as `const BACKEND_URL`)
3. Added `fetch_traces()` — GET `/api/traces`, parses `Vec<TraceSummary>`
4. Added `fetch_trace_detail(id)` — GET `/api/traces/{id}`, parses `TraceDetail`
5. `Application::new` now returns `fetch_traces()` command on startup
6. `TraceSelected` handler now calls `fetch_trace_detail`
7. Sidebar traces wrapped in `button` emitting `TraceSelected(id)`
8. Timeline steps wrapped in `button` emitting `StepSelected(idx)`
9. Removed unused `_backend_url` field from `App`

## Concerns
- None.
