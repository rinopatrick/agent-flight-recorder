import argparse
from pathlib import Path

import uvicorn

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Flight Recorder Backend")
    parser.add_argument("--db", default="traces.db", help="Path to traces database")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8420, help="Bind port")
    args = parser.parse_args()

    db = Database(Path(args.db))
    app = create_app(db)

    print(f"Flight Recorder backend starting on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
