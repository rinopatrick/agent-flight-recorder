"""Framework adapters."""

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.langchain import LangChainAdapter

__all__ = ["BaseAdapter", "LangChainAdapter"]
