# Agent Flight Recorder

Chrome DevTools + Black Box untuk AI agents. Rekam execution, replay secara interaktif, branch untuk eksplorasi alternatif, dan export sebagai test cases.

## Architecture

```
Python SDK → Python Backend (FastAPI) → Rust Desktop App (iced)
```

## Quick Start

### 1. Install SDK & Backend

```bash
pip install -e ./sdk -e ./backend
```

### 2. Start Backend

```bash
python -m flight_recorder_backend
```

### 3. Build Desktop App

```bash
cd desktop && cargo run --release
```

### 4. Use SDK

```python
from flight_recorder import record

@record
def my_agent(task: str):
    result = record.llm_call(
        model="gpt-4o",
        prompt=task,
        response="Hello!",
        tokens_in=10,
        tokens_out=3,
        cost=0.001,
    )
    return result

my_agent("test")
```

## Development

```bash
# SDK tests
cd sdk && python -m pytest

# Backend tests
cd backend && python -m pytest

# Integration tests
python -m pytest tests/

# Build desktop
cd desktop && cargo build
```

## Project Structure

```
agent-flight-recorder/
├── sdk/              # Python SDK (@record decorator, adapters)
├── backend/          # FastAPI server (REST API)
├── desktop/          # Rust iced desktop app (UI)
├── proto/            # Protobuf definitions
└── tests/            # Integration tests
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Desktop UI | Rust + iced |
| Backend | Python + FastAPI |
| Storage | SQLite |
| SDK | Python + Pydantic + SQLAlchemy |
