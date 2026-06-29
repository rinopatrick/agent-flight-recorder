# Phase 3 Task 5: Desktop Test Generation UI

**Status**: Complete
**Commit**: `feat(desktop): add test generation UI` (9b93636)

## Changes Made

### `desktop/src/app.rs`

1. **New Message variants**:
   - `GenerateTest` — triggers POST to `/api/traces/{trace_id}/generate-test`
   - `TestGenerated(String)` — receives generated test code from backend
   - `CopyTestToClipboard` — copies test code to system clipboard

2. **New App fields**:
   - `generated_test: Option<String>` — stores the generated test code
   - `test_loading: bool` — tracks loading state during generation

3. **Generate Test button**:
   - Visible in inspector panel when any trace is loaded
   - Shows "Generating..." while request is in-flight (button disabled)
   - Clears test state when switching traces

4. **Test output display**:
   - Scrollable text view showing generated test code below the inspector
   - "Copy" button using `iced::clipboard::write()` to copy test code to clipboard

5. **New async function**:
   - `generate_test(trace_id)` — POSTs to backend and returns `TestGenerated(code)`

## Build Verification

`cargo build` succeeds with only pre-existing dead-code warnings (unrelated fields in `TraceDetail`/`BranchDetail`).
