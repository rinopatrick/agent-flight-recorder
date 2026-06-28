from pathlib import Path

from flight_recorder import TraceStorage


class Database(TraceStorage):
    def __init__(self, db_path: Path) -> None:
        super().__init__(db_path)
