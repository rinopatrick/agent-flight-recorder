# Task 7: Rust Desktop App — Window & Layout

## Context
Tasks 1-6 built the Python SDK and backend server. This task creates the Rust desktop app using the iced GUI framework. The app has a 3-panel layout: trace list sidebar, timeline view, and inspector panel.

## What to Build
A working iced application with a 3-panel layout and placeholder data.

## Files
- Modify: `desktop/Cargo.toml` (add serde, serde_json, reqwest)
- Create: `desktop/src/app.rs`
- Create: `desktop/src/views/mod.rs`
- Create: `desktop/src/views/trace_list.rs`
- Create: `desktop/src/views/timeline.rs`
- Create: `desktop/src/views/inspector.rs`
- Modify: `desktop/src/main.rs`

## Interfaces
- Produces: Running iced app with 3-panel layout (sidebar, timeline, inspector)

## Steps

### Step 1: Update Cargo.toml
Add dependencies: serde (with derive), serde_json, reqwest (with json).

### Step 2: Create app module
Create `desktop/src/app.rs`:
- `Message` enum: TracesLoaded, TraceSelected, TraceLoaded, StepSelected, Noop
- `TraceSummary` struct: id, agent_name, step_count, total_cost
- `TraceDetail` struct: id, agent_name, steps
- `StepDetail` struct: index, step_type, name, tokens_in, tokens_out, cost, duration_ms
- `App` struct with traces, selected_trace, selected_step, backend_url
- Implement `iced::Application` for App:
  - `new()` returns app with empty state
  - `update()` handles messages (placeholder for now)
  - `view()` returns 3-panel layout:
    - Left sidebar (250px): "Traces" header + scrollable list
    - Right main area: "Timeline" header + step list (or "Select a trace"), "Inspector" header + step detail (or "Select a step")
  - `theme()` returns Dark theme

### Step 3: Create view modules
Create `desktop/src/views/mod.rs`, `trace_list.rs`, `timeline.rs`, `inspector.rs` as stubs (logic is in app.rs for MVP).

### Step 4: Update main.rs
Import app module and run App with iced::Application::run. Set window size to 1200x800, title to "Agent Flight Recorder".

### Step 5: Build and verify
```bash
cd desktop && cargo build 2>&1
```
Expected: Successful compilation.

### Step 6: Commit
```bash
git add desktop/
git commit -m "feat(desktop): add iced app with 3-panel layout"
```

## Important Notes
- The iced API varies between versions. The plan specifies iced 0.12. If the API doesn't match exactly (e.g., Application trait signature), adapt to what the installed version requires. The key is: 3-panel layout with sidebar, timeline, and inspector.
- If iced 0.12 is not available or has different API, use whatever version Cargo resolves and adapt accordingly.

## Global Constraints
- Rust edition 2021
- iced GUI framework
- Dark theme
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
