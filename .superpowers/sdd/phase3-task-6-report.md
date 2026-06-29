# Phase 3 Task 6: Desktop Export/Import UI — Report

## Status: DONE

## Summary
Added export/import trace functionality to the desktop app. Users can export a selected trace's JSON (from `GET /api/traces/{id}/export`) and view/copy it, or import trace JSON by pasting it into a text input (posted to `POST /api/traces/import`).

## Commit
`feat(desktop): add export/import trace UI`

## Changes

### `desktop/src/app.rs`

**New Messages:**
- `ExportTrace` — triggers GET /api/traces/{id}/export
- `TraceExported(String)` — receives export JSON response
- `CopyExportToClipboard` — copies export JSON to clipboard
- `ShowImportPanel` — opens the import text input panel
- `ImportJsonChanged(String)` — updates import JSON input
- `ImportTrace` — triggers POST /api/traces/import
- `TraceImported` — import success, refreshes trace list
- `CloseExportPanel` / `CloseImportPanel` — dismiss panels

**New App State:**
- `export_json: Option<String>` — cached export JSON
- `show_export_panel: bool` — export panel visibility
- `show_import_panel: bool` — import panel visibility
- `import_json: String` — import text input content
- `import_loading: bool` — import request in progress

**UI:**
- Sidebar: "Import" button in header row next to "Traces" title
- Sidebar: "Export Trace" button below trace list (visible when trace selected)
- Main area: Export panel shows JSON text with Copy/Close buttons
- Main area: Import panel shows text input with Import/Close buttons

**Functions:**
- `export_trace(trace_id)` — GET /api/traces/{id}/export, returns raw JSON text
- `import_trace(json)` — POST /api/traces/import with JSON body, refreshes traces on success

## API Endpoints Used
- `GET /api/traces/{id}/export` — returns trace JSON
- `POST /api/traces/import` — accepts trace JSON body

## Verification
- `cargo build` passes (only pre-existing warnings)
