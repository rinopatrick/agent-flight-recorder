from abc import ABC, abstractmethod

from flight_recorder.models import Trace


class BaseAdapter(ABC):
    @abstractmethod
    def build_trace(self) -> Trace:
        """Build a Trace from collected callback events."""
