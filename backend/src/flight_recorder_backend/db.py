from pathlib import Path

from flight_recorder import AnnotationStorage, BranchStorage, SessionStorage, TraceStorage
from flight_recorder.log_config import get_logger

logger = get_logger(__name__)


class Database(TraceStorage):
    def __init__(self, db_path: Path) -> None:
        logger.info("Initializing database at %s", db_path)
        super().__init__(db_path)
        self.annotations = AnnotationStorage(db_path)
        self.branches = BranchStorage(db_path)
        self.sessions = SessionStorage(db_path)
