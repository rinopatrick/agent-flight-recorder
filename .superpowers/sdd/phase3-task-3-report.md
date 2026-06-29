# Phase 3 Task 3: Trace Export/Import — Report

## Status: ✅ Complete

## What was done

Created `sdk/src/flight_recorder/export.py` with four functions:

- `export_trace(trace) -> dict` — serializes Trace to JSON-compatible dict (datetime→ISO, StepType→str)
- `import_trace(data: dict) -> Trace` — deserializes dict back to Trace
- `export_to_file(trace, path)` — writes JSON file
- `import_from_file(path) -> Trace` — reads JSON file (raises FileNotFoundError if missing)

Updated `sdk/src/flight_recorder/__init__.py` to re-export all four functions.

## Tests (18 total, all passing)

| Category | Tests |
|----------|-------|
| TestExportTrace | returns dict, basic fields, datetime ISO, StepType enum, optional fields, JSON compatible |
| TestImportTrace | round trip, round trip steps, all step types |
| TestFileIO | export/import file, valid JSON content, round trip through file |
| TestEdgeCases | empty steps, None context_snapshot, None token fields, None error, empty metadata, nonexistent file |

## Files touched

- `sdk/src/flight_recorder/export.py` (new)
- `sdk/tests/test_export.py` (new)
- `sdk/src/flight_recorder/__init__.py` (modified)

## Commit

`feat(sdk): add trace export/import functionality` (48783fb)
