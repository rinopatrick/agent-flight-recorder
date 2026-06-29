import os
from pathlib import Path

from flight_recorder import AnnotationStorage, BranchStorage, SessionStorage, TraceStorage
from flight_recorder.log_config import get_logger

logger = get_logger(__name__)


class Database(TraceStorage):
    def __init__(self, db_path: Path | None = None) -> None:
        db_url = os.environ.get("FLIGHT_RECORDER_DB_URL")
        if db_url:
            logger.info("Connecting to database: %s", db_url)
            super().__init__(db_url=db_url)
            self.branches = BranchStorage(db_url=db_url)
            self.sessions = SessionStorage(db_url=db_url)
            self.annotations = AnnotationStorage(db_url=db_url)
        else:
            if db_path is None:
                db_path = Path("traces.db")
            logger.info("Initializing database at %s", db_path)
            super().__init__(db_path=db_path)
            self.branches = BranchStorage(db_path=db_path)
            self.sessions = SessionStorage(db_path=db_path)
            self.annotations = AnnotationStorage(db_path=db_path)
