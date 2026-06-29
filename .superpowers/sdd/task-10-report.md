# Task 10: Backend Entry Point & CLI

## Status: DONE

## Commit
- `ed1700f` feat(backend): add CLI entry point for server

## Test Summary
Server starts on custom port and health check returns `{"status":"ok"}` with HTTP 200.

## Files
- `backend/src/flight_recorder_backend/cli.py` — argparse with --db, --host, --port; creates Database, creates app, runs uvicorn
- `backend/src/flight_recorder_backend/__main__.py` — imports and calls main()
