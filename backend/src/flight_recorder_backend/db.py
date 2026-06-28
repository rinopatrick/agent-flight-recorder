import logging
from pathlib import Path

from flight_recorder import BranchStorage, TraceStorage
from flight_recorder.log_config import get_logger

logger = get_logger(__name__)


class Database(TraceStorage):
    def __init__(self, db_path: Path) -> None:
        logger.info("Initializing database at %s", db_path)
        super().__init__(db_path)
        self.branches = BranchStorage(db_path)
