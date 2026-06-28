# Task 1: Project Scaffolding

## Context
This is the first task in building the Agent Flight Recorder — a desktop app that records AI agent execution and enables time-travel debugging. This task creates the monorepo structure for the entire project.

## What to Build
Create the project directory structure with three components:
1. Python SDK package (`sdk/`)
2. Python backend package (`backend/`)
3. Rust desktop app (`desktop/`)
4. Shared protobuf definition (`proto/`)

## Steps

### Step 1: Create root directory and git repo
The project directory is at `C:\Users\patri\agent-flight-recorder` with git already initialized.

### Step 2: Create SDK package scaffolding
Create `sdk/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "flight-recorder"
version = "0.1.0"
description = "AI Agent Flight Recorder SDK"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "sqlalchemy>=2.0",
]

[project.optional-dependencies]
langchain = ["langchain>=0.2"]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]

[tool.hatch.build.targets.wheel]
packages = ["src/flight_recorder"]
```

Create `sdk/src/flight_recorder/__init__.py`:
```python
"""Agent Flight Recorder SDK."""
```

Create `sdk/src/flight_recorder/adapters/__init__.py`:
```python
"""Framework adapters."""
```

### Step 3: Create backend package scaffolding
Create `backend/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "flight-recorder-backend"
version = "0.1.0"
description = "Agent Flight Recorder Backend Server"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "sqlalchemy>=2.0",
    "pydantic>=2.0",
    "grpcio>=1.56",
    "grpcio-tools>=1.56",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "httpx>=0.24"]

[tool.hatch.build.targets.wheel]
packages = ["src/flight_recorder_backend"]
```

### Step 4: Create Rust desktop app
Create `desktop/Cargo.toml`:
```toml
[package]
name = "flight-recorder-desktop"
version = "0.1.0"
edition = "2021"

[dependencies]
iced = { version = "0.12", features = ["tokio"] }
tonic = "0.11"
prost = "0.12"
tokio = { version = "1", features = ["full"] }

[build-dependencies]
tonic-build = "0.11"
```

Create `desktop/src/main.rs`:
```rust
fn main() {
    println!("Agent Flight Recorder — Desktop UI");
}
```

### Step 5: Create initial protobuf definition
Create `proto/flight_recorder.proto`:
```protobuf
syntax = "proto3";
package flight_recorder;

service FlightRecorderService {
    rpc ListTraces(ListTracesRequest) returns (ListTracesResponse);
    rpc GetTrace(GetTraceRequest) returns (Trace);
}

message ListTracesRequest {
    int32 limit = 1;
    int32 offset = 2;
}

message ListTracesResponse {
    repeated TraceSummary traces = 1;
    int32 total = 2;
}

message TraceSummary {
    string id = 1;
    string agent_name = 2;
    int32 step_count = 3;
    string created_at = 4;
    string status = 5;
}

message GetTraceRequest {
    string id = 1;
}

message Trace {
    string id = 1;
    string agent_name = 2;
    repeated Step steps = 3;
    string created_at = 4;
}

message Step {
    int32 index = 1;
    string type = 2;
    string name = 3;
    string input = 4;
    string output = 5;
    int64 tokens_in = 6;
    int64 tokens_out = 7;
    float cost = 8;
    float duration_ms = 9;
    string context_snapshot = 10;
}
```

### Step 6: Initial commit
```bash
git add .
git commit -m "feat: scaffold agent-flight-recorder monorepo"
```

## Deliverables
- `sdk/` directory with pyproject.toml and package stubs
- `backend/` directory with pyproject.toml
- `desktop/` directory with Cargo.toml and main.rs
- `proto/flight_recorder.proto` with service and message definitions
- Initial git commit

## Work from: `C:\Users\patri\agent-flight-recorder`
