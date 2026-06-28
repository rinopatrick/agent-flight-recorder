"""Framework adapters."""

from flight_recorder.adapters.autogen import AutoGenAdapter
from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.crewai import CrewAIAdapter
from flight_recorder.adapters.langchain import LangChainAdapter

__all__ = ["AutoGenAdapter", "BaseAdapter", "CrewAIAdapter", "LangChainAdapter"]
