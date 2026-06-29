# Task 5: LangChain Adapter

## Context
Task 4 built the @record decorator. This task creates the LangChain adapter that hooks into LangChain's callback system to automatically capture LLM and tool calls.

## What to Build
A `LangChainAdapter` class that converts LangChain callback events into a `Trace`.

## Files
- Create: `sdk/src/flight_recorder/adapters/base.py`
- Create: `sdk/src/flight_recorder/adapters/langchain.py`
- Create: `sdk/tests/test_langchain_adapter.py`

## Interfaces
- Consumes: `Trace`, `Step`, `StepType` from models
- Produces:
  - `BaseAdapter(ABC)` with `build_trace() -> Trace`
  - `LangChainAdapter(agent_name)` with:
    - `on_llm_start(serialized, prompts, run_id)`
    - `on_llm_end(output, run_id)`
    - `on_tool_start(serialized, input_str, run_id)`
    - `on_tool_end(output, run_id)`
    - `build_trace() -> Trace`

## Steps (TDD)

### Step 1: Write failing tests
Create `sdk/tests/test_langchain_adapter.py`:
- `test_adapter_is_subclass` — verify LangChainAdapter extends BaseAdapter
- `test_adapter_creates_trace_from_events` — simulate LLM + tool callback sequence, verify trace has correct steps
- `test_adapter_tracks_timing` — verify duration_ms > 0 after real time delay

### Step 2: Run tests to verify they fail
```bash
cd sdk && python -m pytest tests/test_langchain_adapter.py -v
```

### Step 3: Implement base adapter
Create `sdk/src/flight_recorder/adapters/base.py` with abstract `BaseAdapter` class.

### Step 4: Implement LangChain adapter
Create `sdk/src/flight_recorder/adapters/langchain.py`:
- Track pending operations by run_id
- `on_llm_start` stores name, input, start_time in _pending dict
- `on_llm_end` pops pending, calculates duration, extracts token usage, creates Step
- `on_tool_start` / `on_tool_end` similar pattern
- `build_trace()` returns Trace with all collected steps

### Step 5: Run tests to verify they pass
```bash
cd sdk && python -m pytest tests/test_langchain_adapter.py -v
```
Expected: 3 passed

### Step 6: Commit
```bash
git add sdk/src/flight_recorder/adapters/ sdk/tests/test_langchain_adapter.py
git commit -m "feat(sdk): add base adapter and LangChain adapter"
```

## Global Constraints
- Python 3.11+, Pydantic v2
- TDD: write failing test first
- Conventional commits

## Work from: `C:\Users\patri\agent-flight-recorder`
