# Task 10: Backend Entry Point & CLI

## Context
Task 6 created the FastAPI server. This task adds a CLI entry point so the backend can be started with `python -m flight_recorder_backend`.

## What to Build
CLI entry point with argument parsing for db path, host, and port.

## Files
- Create: `backend/src/flight_recorder_backend/cli.py`
- Create: `backend/src/flight_recorder_backend/__main__.py`

## Steps

### Step 1: Create CLI
Create `backend/src/flight_recorder_backend/cli.py`:
- argparse with --db (default "traces.db"), --host (default "127.0.0.1"), --port (default 8420)
- Creates Database(Path(args.db))
- Creates app via create_app(db)
- Prints startup message
- Runs uvicorn

Create `backend/src/flight_recorder_backend/__main__.py`:
- Imports and calls main()

### Step 2: Test server starts
```bash
cd backend && python -m flight_recorder_backend --port 8421 &
sleep 2
curl http://127.0.0.1:8421/api/health
# Expected: {"status":"ok"}
```

### Step 3: Commit
```bash
git add backend/src/flight_recorder_backend/cli.py backend/src/flight_recorder_backend/__main__.py
git commit -m "feat(backend): add CLI entry point for server"
```

## Global Constraints
- Python 3.11+, FastAPI, uvicorn
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
