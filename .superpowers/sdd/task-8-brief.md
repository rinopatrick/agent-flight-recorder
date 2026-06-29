# Task 8: Connect Desktop to Backend — Fetch Traces

## Context
Task 7 created the iced desktop app with a 3-panel layout and placeholder data. Task 6 created the FastAPI backend. This task connects them — the desktop app fetches real trace data from the backend API.

## What to Build
Add HTTP fetching to the desktop app so it loads traces from the backend and displays them.

## Files
- Modify: `desktop/src/app.rs` (add fetch logic, click handling)
- Modify: `desktop/src/main.rs` (if needed)

## Interfaces
- Consumes: `GET /api/traces` and `GET /api/traces/{id}` from backend at `http://127.0.0.1:8420`
- Produces: `Message::TracesLoaded`, `Message::TraceLoaded` with real data

## Steps

### Step 1: Add fetch logic
Add to `desktop/src/app.rs`:
- `fetch_traces(url: String) -> iced::Command<Message>` function that:
  - Uses reqwest to GET /api/traces
  - Parses JSON into Vec<TraceSummary>
  - Returns Message::TracesLoaded or Message::Noop on error
- Update Application::new to return fetch_traces command on startup

### Step 2: Add click handling for trace selection
- In the sidebar, wrap each trace item in a button that emits `Message::TraceSelected(id)`
- In `update()`, handle `TraceSelected` by fetching `GET /api/traces/{id}` and parsing into `TraceDetail`
- Update `Message::TraceLoaded` to store the trace in `selected_trace`

### Step 3: Add step click handling
- In the timeline view, wrap each step in a button that emits `Message::StepSelected(index)`
- In `update()`, handle `StepSelected` by setting `selected_step`

### Step 4: Build and verify
```bash
cd desktop && cargo build 2>&1
```
Expected: Successful compilation.

### Step 5: Commit
```bash
git add desktop/
git commit -m "feat(desktop): connect to backend API, fetch and display traces"
```

## Important Notes
- The app.rs currently has the data structures (TraceSummary, TraceDetail, StepDetail) and Application impl. You need to modify the existing code, not create new files.
- Make sure the data structures have `serde::Deserialize` derive so they can be parsed from JSON.
- Handle network errors gracefully (return Noop on failure).
- The backend runs on port 8420 by default.

## Global Constraints
- Rust edition 2021, iced 0.12
- reqwest for HTTP, serde for JSON
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
