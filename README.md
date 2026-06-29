# Agent Flight Recorder

[![CI](https://github.com/rinopatrick/agent-flight-recorder/actions/workflows/ci.yml/badge.svg)](https://github.com/rinopatrick/agent-flight-recorder/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Chrome DevTools + Black Box untuk AI Agents**

Rekam execution, replay secara interaktif, branch untuk eksplorasi alternatif, dan export sebagai test cases. Debug AI agents seperti debug browser — dengan time travel.

## ✨ Features

### Core
- **🎬 Trace Recording** — Rekam setiap step execution AI agent (LLM calls, tool calls, reasoning)
- **⏪ Time Travel Replay** — Mundur ke step manapun dan jalankan ulang dengan modifikasi
- **🔀 Branch & Fork** — Buat branch dari titik manapun untuk eksplorasi alternatif
- **💰 Cost Analysis** — Track cost per step dan total execution
- **📊 Export/Import** — Export trace sebagai JSON, import dari file atau API

### Adapters
- **🦜 LangChain** — Auto-instrument LangChain chains
- **🤖 CrewAI** — Record CrewAI agent executions
- **🔮 AutoGen** — Track AutoGen conversations
- **📈 LangGraph** — Record graph node executions dan conditional edges
- **🛠️ Community SDK** — Buat adapter custom untuk framework apapun

### Advanced
- **🧪 Test Generation** — Generate test cases dari recorded traces
- **🔍 Search & Filter** — Cari traces berdasarkan agent, cost, date, step type
- **📝 Annotations** — Tambah notes dan tags ke traces
- **👥 Session Grouping** — Group related traces menjadi sessions
- **⚡ WebSocket Streaming** — Real-time trace events ke desktop UI
- **🔄 Trace Comparison** — Bandingkan dua traces secara side-by-side

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Python SDK │ ──▶ │   Backend   │ ──▶ │   Desktop   │
│  (Recording)│     │  (FastAPI)  │     │  (Rust/iced)│
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  @record decorator   REST API           Visual Timeline
  Adapters (5)        WebSocket          Cost Analysis
  Storage (SQLite)    Search/Filter      Branch UI
```

## 🚀 Quick Start

### 1. Install

```bash
pip install -e ./sdk -e ./backend
```

### 2. Start Backend

```bash
python -m flight_recorder_backend
# API available at http://localhost:8420
```

### 3. Use SDK

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
# Trace automatically recorded!
```

### 4. Build Desktop App (Optional)

```bash
cd desktop && cargo run --release
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check with DB status |
| GET | `/api/metrics` | Trace statistics |
| GET | `/api/traces` | List all traces |
| GET | `/api/traces/{id}` | Get trace detail |
| GET | `/api/traces/search` | Search with filters |
| GET | `/api/traces/compare` | Compare two traces |
| POST | `/api/traces/import` | Import trace |
| GET | `/api/traces/{id}/export` | Export trace |
| POST | `/api/traces/{id}/fork` | Fork trace |
| POST | `/api/traces/{id}/generate-test` | Generate test |
| CRUD | `/api/sessions` | Session management |
| CRUD | `/api/traces/{id}/annotations` | Annotation management |
| WS | `/api/ws/traces` | Real-time streaming |

## 🐳 Docker

```bash
# Build and run
docker-compose up -d

# With PostgreSQL (production)
FLIGHT_RECORDER_DB_URL=postgresql://user:pass@host:5432/db docker-compose up -d
```

## 🧪 Testing

```bash
# SDK tests (165 tests)
cd sdk && python -m pytest

# Backend tests (72 tests)
cd backend && python -m pytest

# Integration tests
python -m pytest tests/
```

## 📁 Project Structure

```
agent-flight-recorder/
├── sdk/                    # Python SDK
│   ├── src/flight_recorder/
│   │   ├── models.py       # Trace, Step, Branch, etc.
│   │   ├── storage.py      # SQLite/PostgreSQL storage
│   │   ├── recorder.py     # @record decorator
│   │   ├── adapters/       # LangChain, CrewAI, AutoGen, LangGraph
│   │   └── export.py       # Import/Export
│   └── tests/
│
├── backend/                # FastAPI server
│   ├── src/flight_recorder_backend/
│   │   ├── server.py       # REST API + WebSocket
│   │   ├── db.py           # Database layer
│   │   └── replay.py       # Replay engine
│   └── tests/
│
├── desktop/                # Rust iced UI
│   └── src/
│       ├── app.rs          # Main app logic
│       └── views/          # Timeline, Inspector, etc.
│
└── tests/                  # Integration tests
```

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLIGHT_RECORDER_DB_URL` | - | PostgreSQL connection URL |
| `FLIGHT_RECORDER_DB_PATH` | `traces.db` | SQLite file path |
| `FLIGHT_RECORDER_API_KEY` | - | API authentication key |
| `FLIGHT_RECORDER_RATE_LIMIT` | `100/minute` | Rate limit per IP |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| SDK | Python + Pydantic + SQLAlchemy |
| Backend | Python + FastAPI + WebSocket |
| Desktop | Rust + iced |
| Database | SQLite (dev) / PostgreSQL (prod) |
| CI/CD | GitHub Actions |
| Container | Docker + docker-compose |

## 📊 Test Coverage

- **SDK**: 165 tests (models, storage, adapters, export)
- **Backend**: 72 tests (API endpoints, WebSocket, health)
- **Integration**: 7 tests (full pipeline)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

**Built by [Patrick Rino](https://github.com/rinopatrick)** — Nuclear Engineering → AI/ML Transition
