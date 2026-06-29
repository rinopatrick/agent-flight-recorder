# Phase 2 Task 8 Report: CrewAI Adapter

## Status: DONE

## Commit
- `f764a38` — feat(sdk): add CrewAI adapter

## Test Summary
4 tests, 4 passed (31/31 full SDK suite). Tests cover: subclass check, full event sequence with LLM + tool + agent steps, timing tracking, and None tokens handling.

## Files Created
- `sdk/src/flight_recorder/adapters/crewai.py` — CrewAIAdapter with 5 callback methods
- `sdk/tests/test_crewai_adapter.py` — 4 tests following TDD

## Files Modified
- `sdk/src/flight_recorder/adapters/__init__.py` — added CrewAIAdapter export
