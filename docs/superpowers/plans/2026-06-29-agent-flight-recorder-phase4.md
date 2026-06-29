# Agent Flight Recorder Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add search/filter, session grouping, annotations, trace comparison, LangGraph adapter, and WebSocket real-time streaming to Agent Flight Recorder.

**Architecture:** Six features layered on existing SDK/Backend/Desktop stack. Search & Filter is foundational (others depend on it). Session Grouping + Annotations add organizational metadata. Trace Comparison and LangGraph Adapter are standalone. WebSocket Streaming ties everything together with real-time push.

**Tech Stack:** Python + FastAPI + SQLAlchemy (SDK/Backend), Rust + iced (Desktop), WebSocket (streaming)

## Global Constraints

- All new SDK models go in `sdk/src/flight_recorder/models.py`
- All new storage tables use SQLAlchemy declarative_base from existing `storage.py` or `branch_storage.py`
- Backend endpoints follow existing pattern: `@app.get/post`, `@limiter.limit`, `Depends(verify_api_key)`
- Desktop UI uses iced 0.12 `Application` trait with `Command::perform` for async
- TDD: write failing test first, implement, verify pass, commit
- All tests must pass before committing: `cd sdk && python -m pytest` and `cd backend && python -m pytest`

---

## Feature 1: Search & Filter

### Task 1.1: Add Search Models to SDK

**Files:**
- Modify: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_search_models.py`

**Interfaces:**
- Produces: `TraceFilter` model with fields: `agent_name`, `created_after`, `created_before`, `min_cost`, `max_cost`, `step_type`, `has_error`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_search_models.py
from datetime import datetime, timezone

from flight_recorder.models import StepType, TraceFilter


def test_trace_filter_creation():
    f = TraceFilter(
        agent_name="test-agent",
        created_after=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_before=datetime(2026, 12, 31, tzinfo=timezone.utc),
        min_cost=0.001,
        max_cost=1.0,
        step_type=StepType.LLM_CALL,
        has_error=True,
    )
    assert f.agent_name == "test-agent"
    assert f.min_cost == 0.001
    assert f.max_cost == 1.0
    assert f.step_type == StepType.LLM_CALL
    assert f.has_error is True


def test_trace_filter_defaults():
    f = TraceFilter()
    assert f.agent_name is None
    assert f.created_after is None
    assert f.min_cost is None
    assert f.max_cost is None
    assert f.step_type is None
    assert f.has_error is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_search_models.py -v`
Expected: FAIL with "cannot import name 'TraceFilter'"

- [ ] **Step 3: Write minimal implementation**

Add to `sdk/src/flight_recorder/models.py` after the `Trace` class:

```python
class TraceFilter(BaseModel):
    agent_name: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    min_cost: Optional[float] = None
    max_cost: Optional[float] = None
    step_type: Optional[StepType] = None
    has_error: Optional[bool] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_search_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/models.py sdk/tests/test_search_models.py
git commit -m "feat(sdk): add TraceFilter model for search/filter"
```

---

### Task 1.2: Add search_traces to TraceStorage

**Files:**
- Modify: `sdk/src/flight_recorder/storage.py`
- Create: `sdk/tests/test_search_storage.py`

**Interfaces:**
- Consumes: `TraceFilter` from Task 1.1
- Produces: `TraceStorage.search_traces(filter: TraceFilter, limit: int, offset: int) -> list[Trace]`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_search_storage.py
from datetime import datetime, timezone
from pathlib import Path

from flight_recorder.models import Step, StepType, Trace, TraceFilter
from flight_recorder.storage import TraceStorage


def _make_trace(agent: str, cost: float = 0.0, error: bool = False) -> Trace:
    step = Step(
        index=0,
        step_type=StepType.LLM_CALL,
        name="test",
        input_data={},
        output_data={},
        cost=cost,
        error="fail" if error else None,
    )
    return Trace(agent_name=agent, steps=[step], created_at=datetime(2026, 6, 15, tzinfo=timezone.utc))


def test_search_by_agent_name(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("agent-a"))
    store.save_trace(_make_trace("agent-b"))
    store.save_trace(_make_trace("agent-a"))

    result = store.search_traces(TraceFilter(agent_name="agent-a"))
    assert len(result) == 2
    assert all(t.agent_name == "agent-a" for t in result)


def test_search_by_cost_range(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("a", cost=0.001))
    store.save_trace(_make_trace("b", cost=0.5))
    store.save_trace(_make_trace("c", cost=5.0))

    result = store.search_traces(TraceFilter(min_cost=0.01, max_cost=1.0))
    assert len(result) == 1
    assert result[0].agent_name == "b"


def test_search_by_has_error(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("a", error=False))
    store.save_trace(_make_trace("b", error=True))

    result = store.search_traces(TraceFilter(has_error=True))
    assert len(result) == 1
    assert result[0].agent_name == "b"


def test_search_by_step_type(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    t1 = Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})])
    t2 = Trace(agent_name="b", steps=[Step(index=0, step_type=StepType.TOOL_CALL, name="y", input_data={}, output_data={})])
    store.save_trace(t1)
    store.save_trace(t2)

    result = store.search_traces(TraceFilter(step_type=StepType.TOOL_CALL))
    assert len(result) == 1
    assert result[0].agent_name == "b"


def test_search_no_filter_returns_all(tmp_path: Path):
    store = TraceStorage(tmp_path / "test.db")
    store.save_trace(_make_trace("a"))
    store.save_trace(_make_trace("b"))

    result = store.search_traces(TraceFilter())
    assert len(result) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_search_storage.py -v`
Expected: FAIL with "TraceStorage has no attribute 'search_traces'"

- [ ] **Step 3: Write minimal implementation**

Add to `sdk/src/flight_recorder/storage.py` in the `TraceStorage` class after `delete_trace`:

```python
def search_traces(self, filter: TraceFilter, limit: int = 50, offset: int = 0) -> list[Trace]:
    from sqlalchemy import and_
    
    logger.debug("Searching traces with filter: %s", filter)
    with Session(self._engine) as session:
        query = session.query(TraceRow)
        conditions = []
        
        if filter.agent_name is not None:
            conditions.append(TraceRow.agent_name == filter.agent_name)
        if filter.created_after is not None:
            conditions.append(TraceRow.created_at >= filter.created_after)
        if filter.created_before is not None:
            conditions.append(TraceRow.created_at <= filter.created_before)
        if filter.min_cost is not None:
            conditions.append(TraceRow.id.in_(
                session.query(StepRow.trace_id)
                .group_by(StepRow.trace_id)
                .having(sqlalchemy.func.sum(StepRow.cost) >= filter.min_cost)
            ))
        if filter.max_cost is not None:
            conditions.append(TraceRow.id.in_(
                session.query(StepRow.trace_id)
                .group_by(StepRow.trace_id)
                .having(sqlalchemy.func.sum(StepRow.cost) <= filter.max_cost)
            ))
        if filter.step_type is not None:
            conditions.append(TraceRow.id.in_(
                session.query(StepRow.trace_id)
                .where(StepRow.step_type == filter.step_type.value)
            ))
        if filter.has_error is True:
            conditions.append(TraceRow.id.in_(
                session.query(StepRow.trace_id)
                .where(StepRow.error.isnot(None))
            ))
        elif filter.has_error is False:
            conditions.append(TraceRow.id.in_(
                session.query(StepRow.trace_id)
                .group_by(StepRow.trace_id)
                .having(sqlalchemy.func.sum(sqlalchemy.case((StepRow.error.isnot(None), 1), else_=0)) == 0)
            ))
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        rows = query.order_by(TraceRow.created_at.desc()).offset(offset).limit(limit).all()
        return [self._row_to_trace(r) for r in rows]
```

Also add `import sqlalchemy` at the top of the file (it's already imported via specific names, but we need `sqlalchemy.func` and `sqlalchemy.case`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_search_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/storage.py sdk/tests/test_search_storage.py
git commit -m "feat(sdk): add search_traces with multi-field filtering"
```

---

### Task 1.3: Add Search API Endpoint

**Files:**
- Modify: `backend/src/flight_recorder_backend/server.py`
- Create: `backend/tests/test_search_api.py`

**Interfaces:**
- Consumes: `TraceStorage.search_traces` from Task 1.2, `TraceFilter` from Task 1.1
- Produces: `GET /api/traces/search` endpoint with query params

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_search_api.py
from pathlib import Path

from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_search_by_agent_name(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="agent-a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    db.save_trace(Trace(agent_name="agent-b", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="y", input_data={}, output_data={})]))

    client = TestClient(app)
    resp = client.get("/api/traces/search", params={"agent_name": "agent-a"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "agent-a"


def test_search_by_cost_range(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="cheap", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={}, cost=0.001)]))
    db.save_trace(Trace(agent_name="expensive", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="y", input_data={}, output_data={}, cost=5.0)]))

    client = TestClient(app)
    resp = client.get("/api/traces/search", params={"min_cost": "1.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "expensive"


def test_search_with_pagination(tmp_path: Path):
    app, db = _make_app(tmp_path)
    for i in range(5):
        db.save_trace(Trace(agent_name=f"agent-{i}", steps=[]))

    client = TestClient(app)
    resp = client.get("/api/traces/search", params={"limit": "2", "offset": "0"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_search_no_results(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="agent-a", steps=[]))

    client = TestClient(app)
    resp = client.get("/api/traces/search", params={"agent_name": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_search_api.py -v`
Expected: FAIL with 404 Not Found (endpoint doesn't exist)

- [ ] **Step 3: Write minimal implementation**

Add to `backend/src/flight_recorder_backend/server.py` after the `list_traces` endpoint:

```python
@app.get("/api/traces/search")
@limiter.limit(RATE_LIMIT)
def search_traces(
    request: Request,
    agent_name: str | None = None,
    min_cost: float | None = None,
    max_cost: float | None = None,
    step_type: str | None = None,
    has_error: bool | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _auth: None = Depends(verify_api_key),
) -> list[dict]:
    from datetime import datetime
    from flight_recorder.models import StepType, TraceFilter
    
    filter = TraceFilter(
        agent_name=agent_name,
        min_cost=min_cost,
        max_cost=max_cost,
        step_type=StepType(step_type) if step_type else None,
        has_error=has_error,
        created_after=datetime.fromisoformat(created_after) if created_after else None,
        created_before=datetime.fromisoformat(created_before) if created_before else None,
    )
    traces = db.search_traces(filter, limit=limit, offset=offset)
    return [
        {
            "id": t.id,
            "agent_name": t.agent_name,
            "step_count": len(t.steps),
            "created_at": t.created_at.isoformat(),
            "total_cost": t.total_cost(),
        }
        for t in traces
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_search_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/flight_recorder_backend/server.py backend/tests/test_search_api.py
git commit -m "feat(backend): add search traces API endpoint"
```

---

## Feature 2: Session Grouping

### Task 2.1: Add Session Model to SDK

**Files:**
- Modify: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_session_models.py`

**Interfaces:**
- Produces: `Session` model with: `id`, `name`, `trace_ids`, `created_at`, `metadata`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_session_models.py
from flight_recorder.models import TraceSession


def test_session_creation():
    s = TraceSession(name="test-session", trace_ids=["abc", "def"])
    assert s.name == "test-session"
    assert len(s.trace_ids) == 2
    assert s.id is not None
    assert len(s.id) == 12


def test_session_empty_traces():
    s = TraceSession(name="empty")
    assert s.trace_ids == []
    assert s.metadata == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_session_models.py -v`
Expected: FAIL with "cannot import name 'TraceSession'"

- [ ] **Step 3: Write minimal implementation**

Add to `sdk/src/flight_recorder/models.py` after `TraceFilter`:

```python
class TraceSession(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    trace_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_session_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/models.py sdk/tests/test_session_models.py
git commit -m "feat(sdk): add TraceSession model for session grouping"
```

---

### Task 2.2: Add Session Storage to SDK

**Files:**
- Create: `sdk/src/flight_recorder/session_storage.py`
- Create: `sdk/tests/test_session_storage.py`

**Interfaces:**
- Consumes: `TraceSession` from Task 2.1
- Produces: `SessionStorage` class with `save_session`, `get_session`, `list_sessions`, `add_trace_to_session`, `remove_trace_from_session`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_session_storage.py
from pathlib import Path

from flight_recorder.models import TraceSession
from flight_recorder.session_storage import SessionStorage


def test_save_and_get_session(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    s = TraceSession(name="test", trace_ids=["abc", "def"])
    store.save_session(s)
    loaded = store.get_session(s.id)
    assert loaded is not None
    assert loaded.name == "test"
    assert loaded.trace_ids == ["abc", "def"]


def test_list_sessions(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    store.save_session(TraceSession(name="s1"))
    store.save_session(TraceSession(name="s2"))
    sessions = store.list_sessions()
    assert len(sessions) == 2


def test_add_trace_to_session(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    s = TraceSession(name="test", trace_ids=["abc"])
    store.save_session(s)
    store.add_trace_to_session(s.id, "def")
    loaded = store.get_session(s.id)
    assert "def" in loaded.trace_ids


def test_remove_trace_from_session(tmp_path: Path):
    store = SessionStorage(tmp_path / "test.db")
    s = TraceSession(name="test", trace_ids=["abc", "def"])
    store.save_session(s)
    store.remove_trace_from_session(s.id, "abc")
    loaded = store.get_session(s.id)
    assert "abc" not in loaded.trace_ids
    assert "def" in loaded.trace_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_session_storage.py -v`
Expected: FAIL with "cannot import name 'SessionStorage'"

- [ ] **Step 3: Write minimal implementation**

Create `sdk/src/flight_recorder/session_storage.py`:

```python
import json
from datetime import timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base

from flight_recorder.models import TraceSession

Base = declarative_base()


class SessionRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    trace_ids_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")


class SessionStorage:
    def __init__(self, db_path: Path) -> None:
        self._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self._engine)

    def save_session(self, session: TraceSession) -> None:
        with Session(self._engine) as db:
            row = SessionRow(
                id=session.id,
                name=session.name,
                trace_ids_json=json.dumps(session.trace_ids),
                created_at=session.created_at,
                metadata_json=json.dumps(session.metadata),
            )
            db.merge(row)
            db.commit()

    def get_session(self, session_id: str) -> TraceSession | None:
        with Session(self._engine) as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                return None
            return TraceSession(
                id=row.id,
                name=row.name,
                trace_ids=json.loads(row.trace_ids_json),
                created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at,
                metadata=json.loads(row.metadata_json),
            )

    def list_sessions(self) -> list[TraceSession]:
        with Session(self._engine) as db:
            rows = db.query(SessionRow).order_by(SessionRow.created_at.desc()).all()
            return [
                TraceSession(
                    id=r.id,
                    name=r.name,
                    trace_ids=json.loads(r.trace_ids_json),
                    created_at=r.created_at.replace(tzinfo=timezone.utc) if r.created_at.tzinfo is None else r.created_at,
                    metadata=json.loads(r.metadata_json),
                )
                for r in rows
            ]

    def add_trace_to_session(self, session_id: str, trace_id: str) -> None:
        with Session(self._engine) as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                return
            ids = json.loads(row.trace_ids_json)
            if trace_id not in ids:
                ids.append(trace_id)
                row.trace_ids_json = json.dumps(ids)
                db.commit()

    def remove_trace_from_session(self, session_id: str, trace_id: str) -> None:
        with Session(self._engine) as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                return
            ids = json.loads(row.trace_ids_json)
            if trace_id in ids:
                ids.remove(trace_id)
                row.trace_ids_json = json.dumps(ids)
                db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_session_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/session_storage.py sdk/tests/test_session_storage.py
git commit -m "feat(sdk): add SessionStorage for session grouping"
```

---

### Task 2.3: Add Session API Endpoints

**Files:**
- Modify: `backend/src/flight_recorder_backend/server.py`
- Modify: `backend/src/flight_recorder_backend/db.py`
- Create: `backend/tests/test_session_api.py`

**Interfaces:**
- Consumes: `SessionStorage` from Task 2.2
- Produces: `POST /api/sessions`, `GET /api/sessions`, `GET /api/sessions/{id}`, `POST /api/sessions/{id}/traces/{trace_id}`, `DELETE /api/sessions/{id}/traces/{trace_id}`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_session_api.py
from pathlib import Path

from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_create_and_get_session(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)

    resp = client.post("/api/sessions", json={"name": "test-session"})
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-session"


def test_list_sessions(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)

    client.post("/api/sessions", json={"name": "s1"})
    client.post("/api/sessions", json={"name": "s2"})

    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_add_and_remove_trace_from_session(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    traces = db.list_traces()
    trace_id = traces[0].id

    client = TestClient(app)
    resp = client.post("/api/sessions", json={"name": "test"})
    session_id = resp.json()["id"]

    resp = client.post(f"/api/sessions/{session_id}/traces/{trace_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/sessions/{session_id}")
    assert trace_id in resp.json()["trace_ids"]

    resp = client.delete(f"/api/sessions/{session_id}/traces/{trace_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/sessions/{session_id}")
    assert trace_id not in resp.json()["trace_ids"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_session_api.py -v`
Expected: FAIL with 404 (endpoints don't exist)

- [ ] **Step 3: Write minimal implementation**

Update `backend/src/flight_recorder_backend/db.py` to add session storage:

```python
from pathlib import Path

from flight_recorder import BranchStorage, TraceStorage
from flight_recorder.log_config import get_logger
from flight_recorder.session_storage import SessionStorage

logger = get_logger(__name__)


class Database(TraceStorage):
    def __init__(self, db_path: Path) -> None:
        logger.info("Initializing database at %s", db_path)
        super().__init__(db_path)
        self.branches = BranchStorage(db_path)
        self.sessions = SessionStorage(db_path)
```

Add to `backend/src/flight_recorder_backend/server.py` after the search endpoint:

```python
class CreateSessionRequest(BaseModel):
    name: str
    metadata: dict = {}

@app.post("/api/sessions")
@limiter.limit(RATE_LIMIT)
def create_session(
    request: Request,
    body: CreateSessionRequest,
    _auth: None = Depends(verify_api_key),
) -> dict:
    from flight_recorder.models import TraceSession
    session = TraceSession(name=body.name, metadata=body.metadata)
    db.sessions.save_session(session)
    return {"id": session.id, "name": session.name, "trace_ids": session.trace_ids, "created_at": session.created_at.isoformat()}

@app.get("/api/sessions")
@limiter.limit(RATE_LIMIT)
def list_sessions(
    request: Request, _auth: None = Depends(verify_api_key)
) -> list[dict]:
    sessions = db.sessions.list_sessions()
    return [
        {"id": s.id, "name": s.name, "trace_ids": s.trace_ids, "created_at": s.created_at.isoformat()}
        for s in sessions
    ]

@app.get("/api/sessions/{session_id}")
@limiter.limit(RATE_LIMIT)
def get_session(
    request: Request, session_id: str, _auth: None = Depends(verify_api_key)
) -> dict:
    session = db.sessions.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": session.id, "name": session.name, "trace_ids": session.trace_ids, "created_at": session.created_at.isoformat()}

@app.post("/api/sessions/{session_id}/traces/{trace_id}")
@limiter.limit(RATE_LIMIT)
def add_trace_to_session(
    request: Request, session_id: str, trace_id: str, _auth: None = Depends(verify_api_key)
) -> dict:
    session = db.sessions.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db.sessions.add_trace_to_session(session_id, trace_id)
    return {"ok": True}

@app.delete("/api/sessions/{session_id}/traces/{trace_id}")
@limiter.limit(RATE_LIMIT)
def remove_trace_from_session(
    request: Request, session_id: str, trace_id: str, _auth: None = Depends(verify_api_key)
) -> dict:
    session = db.sessions.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db.sessions.remove_trace_from_session(session_id, trace_id)
    return {"ok": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_session_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/flight_recorder_backend/db.py backend/src/flight_recorder_backend/server.py backend/tests/test_session_api.py
git commit -m "feat(backend): add session grouping API endpoints"
```

---

## Feature 3: Annotations/Tags

### Task 3.1: Add Annotation Model to SDK

**Files:**
- Modify: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_annotation_models.py`

**Interfaces:**
- Produces: `Annotation` model with: `id`, `trace_id`, `content`, `tags`, `created_at`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_annotation_models.py
from flight_recorder.models import Annotation


def test_annotation_creation():
    a = Annotation(trace_id="abc123", content="This trace is slow", tags=["performance", "investigate"])
    assert a.trace_id == "abc123"
    assert a.content == "This trace is slow"
    assert "performance" in a.tags
    assert a.id is not None


def test_annotation_defaults():
    a = Annotation(trace_id="abc123", content="note")
    assert a.tags == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_annotation_models.py -v`
Expected: FAIL with "cannot import name 'Annotation'"

- [ ] **Step 3: Write minimal implementation**

Add to `sdk/src/flight_recorder/models.py` after `TraceSession`:

```python
class Annotation(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_annotation_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/models.py sdk/tests/test_annotation_models.py
git commit -m "feat(sdk): add Annotation model with tags"
```

---

### Task 3.2: Add Annotation Storage to SDK

**Files:**
- Create: `sdk/src/flight_recorder/annotation_storage.py`
- Create: `sdk/tests/test_annotation_storage.py`

**Interfaces:**
- Consumes: `Annotation` from Task 3.1
- Produces: `AnnotationStorage` class with `save_annotation`, `get_annotations_for_trace`, `delete_annotation`, `add_tag`, `remove_tag`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_annotation_storage.py
from pathlib import Path

from flight_recorder.models import Annotation
from flight_recorder.annotation_storage import AnnotationStorage


def test_save_and_get_annotations(tmp_path: Path):
    store = AnnotationStorage(tmp_path / "test.db")
    a = Annotation(trace_id="abc", content="slow trace", tags=["perf"])
    store.save_annotation(a)
    results = store.get_annotations_for_trace("abc")
    assert len(results) == 1
    assert results[0].content == "slow trace"


def test_delete_annotation(tmp_path: Path):
    store = AnnotationStorage(tmp_path / "test.db")
    a = Annotation(trace_id="abc", content="note")
    store.save_annotation(a)
    store.delete_annotation(a.id)
    assert store.get_annotations_for_trace("abc") == []


def test_add_and_remove_tag(tmp_path: Path):
    store = AnnotationStorage(tmp_path / "test.db")
    a = Annotation(trace_id="abc", content="note", tags=["initial"])
    store.save_annotation(a)
    
    store.add_tag(a.id, "new-tag")
    results = store.get_annotations_for_trace("abc")
    assert "new-tag" in results[0].tags
    
    store.remove_tag(a.id, "initial")
    results = store.get_annotations_for_trace("abc")
    assert "initial" not in results[0].tags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_annotation_storage.py -v`
Expected: FAIL with "cannot import name 'AnnotationStorage'"

- [ ] **Step 3: Write minimal implementation**

Create `sdk/src/flight_recorder/annotation_storage.py`:

```python
import json
from datetime import timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base

from flight_recorder.models import Annotation

Base = declarative_base()


class AnnotationRow(Base):  # type: ignore[misc, valid-type]
    __tablename__ = "annotations"

    id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    tags_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False)


class AnnotationStorage:
    def __init__(self, db_path: Path) -> None:
        self._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self._engine)

    def save_annotation(self, annotation: Annotation) -> None:
        with Session(self._engine) as db:
            row = AnnotationRow(
                id=annotation.id,
                trace_id=annotation.trace_id,
                content=annotation.content,
                tags_json=json.dumps(annotation.tags),
                created_at=annotation.created_at,
            )
            db.add(row)
            db.commit()

    def get_annotations_for_trace(self, trace_id: str) -> list[Annotation]:
        with Session(self._engine) as db:
            rows = db.query(AnnotationRow).filter(AnnotationRow.trace_id == trace_id).order_by(AnnotationRow.created_at.desc()).all()
            return [
                Annotation(
                    id=r.id,
                    trace_id=r.trace_id,
                    content=r.content,
                    tags=json.loads(r.tags_json),
                    created_at=r.created_at.replace(tzinfo=timezone.utc) if r.created_at.tzinfo is None else r.created_at,
                )
                for r in rows
            ]

    def delete_annotation(self, annotation_id: str) -> None:
        with Session(self._engine) as db:
            row = db.get(AnnotationRow, annotation_id)
            if row is not None:
                db.delete(row)
                db.commit()

    def add_tag(self, annotation_id: str, tag: str) -> None:
        with Session(self._engine) as db:
            row = db.get(AnnotationRow, annotation_id)
            if row is None:
                return
            tags = json.loads(row.tags_json)
            if tag not in tags:
                tags.append(tag)
                row.tags_json = json.dumps(tags)
                db.commit()

    def remove_tag(self, annotation_id: str, tag: str) -> None:
        with Session(self._engine) as db:
            row = db.get(AnnotationRow, annotation_id)
            if row is None:
                return
            tags = json.loads(row.tags_json)
            if tag in tags:
                tags.remove(tag)
                row.tags_json = json.dumps(tags)
                db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_annotation_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/annotation_storage.py sdk/tests/test_annotation_storage.py
git commit -m "feat(sdk): add AnnotationStorage with tag management"
```

---

### Task 3.3: Add Annotation API Endpoints

**Files:**
- Modify: `backend/src/flight_recorder_backend/db.py`
- Modify: `backend/src/flight_recorder_backend/server.py`
- Create: `backend/tests/test_annotation_api.py`

**Interfaces:**
- Consumes: `AnnotationStorage` from Task 3.2
- Produces: `POST /api/traces/{id}/annotations`, `GET /api/traces/{id}/annotations`, `DELETE /api/annotations/{id}`, `POST /api/annotations/{id}/tags/{tag}`, `DELETE /api/annotations/{id}/tags/{tag}`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_annotation_api.py
from pathlib import Path

from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_create_and_get_annotations(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id

    client = TestClient(app)
    resp = client.post(f"/api/traces/{trace_id}/annotations", json={"content": "slow trace", "tags": ["perf"]})
    assert resp.status_code == 200
    ann_id = resp.json()["id"]

    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["content"] == "slow trace"


def test_delete_annotation(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id

    client = TestClient(app)
    resp = client.post(f"/api/traces/{trace_id}/annotations", json={"content": "note"})
    ann_id = resp.json()["id"]

    resp = client.delete(f"/api/annotations/{ann_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert len(resp.json()) == 0


def test_add_and_remove_tag(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(agent_name="a", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="x", input_data={}, output_data={})]))
    trace_id = db.list_traces()[0].id

    client = TestClient(app)
    resp = client.post(f"/api/traces/{trace_id}/annotations", json={"content": "note", "tags": ["initial"]})
    ann_id = resp.json()["id"]

    resp = client.post(f"/api/annotations/{ann_id}/tags/new-tag")
    assert resp.status_code == 200

    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert "new-tag" in resp.json()[0]["tags"]

    resp = client.delete(f"/api/annotations/{ann_id}/tags/initial")
    assert resp.status_code == 200

    resp = client.get(f"/api/traces/{trace_id}/annotations")
    assert "initial" not in resp.json()[0]["tags"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_annotation_api.py -v`
Expected: FAIL with 404

- [ ] **Step 3: Write minimal implementation**

Update `db.py` to add annotation storage:

```python
class Database(TraceStorage):
    def __init__(self, db_path: Path) -> None:
        logger.info("Initializing database at %s", db_path)
        super().__init__(db_path)
        self.branches = BranchStorage(db_path)
        self.sessions = SessionStorage(db_path)
        self.annotations = AnnotationStorage(db_path)
```

Add endpoints to `server.py`:

```python
class CreateAnnotationRequest(BaseModel):
    content: str
    tags: list[str] = []

@app.post("/api/traces/{trace_id}/annotations")
@limiter.limit(RATE_LIMIT)
def create_annotation(
    request: Request, trace_id: str, body: CreateAnnotationRequest, _auth: None = Depends(verify_api_key)
) -> dict:
    from flight_recorder.models import Annotation
    annotation = Annotation(trace_id=trace_id, content=body.content, tags=body.tags)
    db.annotations.save_annotation(annotation)
    return {"id": annotation.id, "trace_id": annotation.trace_id, "content": annotation.content, "tags": annotation.tags, "created_at": annotation.created_at.isoformat()}

@app.get("/api/traces/{trace_id}/annotations")
@limiter.limit(RATE_LIMIT)
def get_annotations(
    request: Request, trace_id: str, _auth: None = Depends(verify_api_key)
) -> list[dict]:
    annotations = db.annotations.get_annotations_for_trace(trace_id)
    return [{"id": a.id, "trace_id": a.trace_id, "content": a.content, "tags": a.tags, "created_at": a.created_at.isoformat()} for a in annotations]

@app.delete("/api/annotations/{annotation_id}")
@limiter.limit(RATE_LIMIT)
def delete_annotation(
    request: Request, annotation_id: str, _auth: None = Depends(verify_api_key)
) -> dict:
    db.annotations.delete_annotation(annotation_id)
    return {"deleted": annotation_id}

@app.post("/api/annotations/{annotation_id}/tags/{tag}")
@limiter.limit(RATE_LIMIT)
def add_tag(
    request: Request, annotation_id: str, tag: str, _auth: None = Depends(verify_api_key)
) -> dict:
    db.annotations.add_tag(annotation_id, tag)
    return {"ok": True}

@app.delete("/api/annotations/{annotation_id}/tags/{tag}")
@limiter.limit(RATE_LIMIT)
def remove_tag(
    request: Request, annotation_id: str, tag: str, _auth: None = Depends(verify_api_key)
) -> dict:
    db.annotations.remove_tag(annotation_id, tag)
    return {"ok": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_annotation_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/flight_recorder_backend/db.py backend/src/flight_recorder_backend/server.py backend/tests/test_annotation_api.py
git commit -m "feat(backend): add annotation and tag API endpoints"
```

---

## Feature 4: Trace Comparison

### Task 4.1: Add Comparison Model to SDK

**Files:**
- Modify: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_comparison_models.py`

**Interfaces:**
- Produces: `TraceComparison` model with: `trace_a_id`, `trace_b_id`, `steps_a`, `steps_b`, `cost_diff`, `duration_diff`, `step_type_diff`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_comparison_models.py
from flight_recorder.models import Step, StepType, Trace, TraceComparison


def test_comparison_creation():
    a = Trace(id="a", agent_name="x", steps=[
        Step(index=0, step_type=StepType.LLM_CALL, name="s1", input_data={}, output_data={}, cost=0.1, duration_ms=100),
    ])
    b = Trace(id="b", agent_name="x", steps=[
        Step(index=0, step_type=StepType.LLM_CALL, name="s1", input_data={}, output_data={}, cost=0.2, duration_ms=200),
        Step(index=1, step_type=StepType.TOOL_CALL, name="s2", input_data={}, output_data={}, cost=0.05, duration_ms=50),
    ])
    comp = TraceComparison(trace_a=a, trace_b=b)
    assert comp.cost_diff == pytest.approx(0.15)
    assert comp.duration_diff == pytest.approx(150.0)
    assert comp.step_count_diff == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_comparison_models.py -v`
Expected: FAIL with "cannot import name 'TraceComparison'"

- [ ] **Step 3: Write minimal implementation**

Add to `sdk/src/flight_recorder/models.py` after `Annotation`:

```python
class TraceComparison(BaseModel):
    trace_a: Trace
    trace_b: Trace

    @property
    def cost_diff(self) -> float:
        return self.trace_b.total_cost() - self.trace_a.total_cost()

    @property
    def duration_diff(self) -> float:
        return self.trace_b.total_duration_ms() - self.trace_a.total_duration_ms()

    @property
    def step_count_diff(self) -> int:
        return len(self.trace_b.steps) - len(self.trace_a.steps)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_comparison_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/models.py sdk/tests/test_comparison_models.py
git commit -m "feat(sdk): add TraceComparison model"
```

---

### Task 4.2: Add Comparison API Endpoint

**Files:**
- Modify: `backend/src/flight_recorder_backend/server.py`
- Create: `backend/tests/test_comparison_api.py`

**Interfaces:**
- Consumes: `TraceComparison` from Task 4.1
- Produces: `GET /api/traces/compare?a={id}&b={id}`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_comparison_api.py
from pathlib import Path

from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_compare_traces(tmp_path: Path):
    app, db = _make_app(tmp_path)
    db.save_trace(Trace(id="aaa", agent_name="x", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="s", input_data={}, output_data={}, cost=0.1, duration_ms=100)]))
    db.save_trace(Trace(id="bbb", agent_name="x", steps=[Step(index=0, step_type=StepType.LLM_CALL, name="s", input_data={}, output_data={}, cost=0.2, duration_ms=200)]))

    client = TestClient(app)
    resp = client.get("/api/traces/compare", params={"a": "aaa", "b": "bbb"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cost_diff"] == pytest.approx(0.1)
    assert data["duration_diff"] == pytest.approx(100.0)
    assert data["step_count_diff"] == 0


def test_compare_traces_not_found(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/traces/compare", params={"a": "nonexistent", "b": "also-not"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_comparison_api.py -v`
Expected: FAIL with 404

- [ ] **Step 3: Write minimal implementation**

Add to `backend/src/flight_recorder_backend/server.py`:

```python
@app.get("/api/traces/compare")
@limiter.limit(RATE_LIMIT)
def compare_traces(
    request: Request,
    a: str,
    b: str,
    _auth: None = Depends(verify_api_key),
) -> dict:
    from flight_recorder.models import TraceComparison
    
    trace_a = db.get_trace(a)
    trace_b = db.get_trace(b)
    if trace_a is None or trace_b is None:
        raise HTTPException(status_code=404, detail="One or both traces not found")
    
    comp = TraceComparison(trace_a=trace_a, trace_b=trace_b)
    return {
        "trace_a_id": a,
        "trace_b_id": b,
        "cost_diff": comp.cost_diff,
        "duration_diff": comp.duration_diff,
        "step_count_diff": comp.step_count_diff,
        "steps_a": len(trace_a.steps),
        "steps_b": len(trace_b.steps),
        "cost_a": trace_a.total_cost(),
        "cost_b": trace_b.total_cost(),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_comparison_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/flight_recorder_backend/server.py backend/tests/test_comparison_api.py
git commit -m "feat(backend): add trace comparison API endpoint"
```

---

## Feature 5: LangGraph Adapter

### Task 5.1: Add LangGraph Adapter to SDK

**Files:**
- Create: `sdk/src/flight_recorder/adapters/langgraph.py`
- Create: `sdk/tests/test_langgraph_adapter.py`

**Interfaces:**
- Consumes: `BaseAdapter` from `adapters/base.py`
- Produces: `LangGraphAdapter` that records graph node executions as steps

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_langgraph_adapter.py
from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.adapters.langgraph import LangGraphAdapter
from flight_recorder.models import StepType


def test_langgraph_adapter_is_base_adapter():
    adapter = LangGraphAdapter(agent_name="test-graph")
    assert isinstance(adapter, BaseAdapter)


def test_langgraph_record_node():
    adapter = LangGraphAdapter(agent_name="test-graph")
    adapter.record_node("agent_node", input_data={"query": "hello"}, output_data={"response": "hi"})
    trace = adapter.get_trace()
    assert len(trace.steps) == 1
    assert trace.steps[0].name == "agent_node"
    assert trace.steps[0].step_type == StepType.TOOL_CALL
    assert trace.steps[0].input_data == {"query": "hello"}


def test_langgraph_record_multiple_nodes():
    adapter = LangGraphAdapter(agent_name="test-graph")
    adapter.record_node("node_a", input_data={}, output_data={})
    adapter.record_node("node_b", input_data={}, output_data={})
    trace = adapter.get_trace()
    assert len(trace.steps) == 2
    assert trace.steps[0].name == "node_a"
    assert trace.steps[1].name == "node_b"


def test_langgraph_record_conditional_edge():
    adapter = LangGraphAdapter(agent_name="test-graph")
    adapter.record_conditional_edge("router", chosen_path="path_a", input_data={"state": "x"})
    trace = adapter.get_trace()
    assert len(trace.steps) == 1
    assert trace.steps[0].name == "router"
    assert trace.steps[0].output_data == {"chosen_path": "path_a"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_langgraph_adapter.py -v`
Expected: FAIL with "cannot import name 'LangGraphAdapter'"

- [ ] **Step 3: Write minimal implementation**

Create `sdk/src/flight_recorder/adapters/langgraph.py`:

```python
import time
from typing import Any

from flight_recorder.adapters.base import BaseAdapter
from flight_recorder.models import Step, StepType, Trace


class LangGraphAdapter(BaseAdapter):
    def __init__(self, agent_name: str) -> None:
        self._trace = Trace(agent_name=agent_name)

    def get_trace(self) -> Trace:
        return self._trace

    def record_node(
        self,
        node_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        cost: float = 0.0,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> None:
        step = Step(
            index=len(self._trace.steps),
            step_type=StepType.TOOL_CALL,
            name=node_name,
            input_data=input_data,
            output_data=output_data,
            cost=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        self._trace.steps.append(step)

    def record_conditional_edge(
        self,
        edge_name: str,
        chosen_path: str,
        input_data: dict[str, Any],
    ) -> None:
        step = Step(
            index=len(self._trace.steps),
            step_type=StepType.REASONING,
            name=edge_name,
            input_data=input_data,
            output_data={"chosen_path": chosen_path},
        )
        self._trace.steps.append(step)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_langgraph_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/adapters/langgraph.py sdk/tests/test_langgraph_adapter.py
git commit -m "feat(sdk): add LangGraph adapter for graph workflow recording"
```

---

## Feature 6: WebSocket Real-time Streaming

### Task 6.1: Add WebSocket Event Model to SDK

**Files:**
- Modify: `sdk/src/flight_recorder/models.py`
- Create: `sdk/tests/test_ws_models.py`

**Interfaces:**
- Produces: `StreamEvent` model with: `event_type` (trace_start, step_complete, trace_end, error), `trace_id`, `step`, `timestamp`

- [ ] **Step 1: Write failing test**

```python
# sdk/tests/test_ws_models.py
from flight_recorder.models import Step, StepType, StreamEvent


def test_stream_event_trace_start():
    e = StreamEvent(event_type="trace_start", trace_id="abc123", data={"agent_name": "test"})
    assert e.event_type == "trace_start"
    assert e.trace_id == "abc123"
    assert e.timestamp is not None


def test_stream_event_step_complete():
    step = Step(index=0, step_type=StepType.LLM_CALL, name="call", input_data={}, output_data={})
    e = StreamEvent(event_type="step_complete", trace_id="abc123", data={"step": step.model_dump()})
    assert e.event_type == "step_complete"
    assert "step" in e.data


def test_stream_event_trace_end():
    e = StreamEvent(event_type="trace_end", trace_id="abc123", data={"total_steps": 5})
    assert e.event_type == "trace_end"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest sdk/tests/test_ws_models.py -v`
Expected: FAIL with "cannot import name 'StreamEvent'"

- [ ] **Step 3: Write minimal implementation**

Add to `sdk/src/flight_recorder/models.py` after `TraceComparison`:

```python
class StreamEvent(BaseModel):
    event_type: str  # "trace_start", "step_complete", "trace_end", "error"
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest sdk/tests/test_ws_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sdk/src/flight_recorder/models.py sdk/tests/test_ws_models.py
git commit -m "feat(sdk): add StreamEvent model for real-time streaming"
```

---

### Task 6.2: Add WebSocket Endpoint to Backend

**Files:**
- Modify: `backend/src/flight_recorder_backend/server.py`
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/test_websocket.py`

**Interfaces:**
- Consumes: `StreamEvent` from Task 6.1
- Produces: `WebSocket /api/ws/traces` endpoint that broadcasts events to connected clients

- [ ] **Step 1: Add websockets dependency**

Add `websockets>=12.0` to `backend/pyproject.toml` dependencies.

- [ ] **Step 2: Write failing test**

```python
# backend/tests/test_websocket.py
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from flight_recorder import Step, StepType, Trace

from flight_recorder_backend.db import Database
from flight_recorder_backend.server import create_app


def _make_app(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return create_app(db), db


def test_websocket_connect(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/api/ws/traces") as ws:
        # Just verifying connection works
        assert ws is not None


def test_websocket_receives_trace_event(tmp_path: Path):
    app, db = _make_app(tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/api/ws/traces") as ws:
        # Create a trace via API to trigger event
        client.post("/api/traces/import", json={
            "data": {
                "id": "ws-test",
                "agent_name": "ws-agent",
                "steps": [],
                "created_at": "2026-01-01T00:00:00Z",
            }
        })
        # Should receive event
        data = ws.receive_json()
        assert data["event_type"] == "trace_saved"
        assert data["trace_id"] == "ws-test"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_websocket.py -v`
Expected: FAIL (WebSocket endpoint doesn't exist)

- [ ] **Step 4: Write minimal implementation**

Add to `backend/src/flight_recorder_backend/server.py`:

```python
import asyncio
import json as json_module

# Inside create_app, add:
connected_clients: set = set()

@app.websocket("/api/ws/traces")
async def websocket_traces(websocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        connected_clients.discard(websocket)

async def broadcast_event(event: dict) -> None:
    dead = set()
    for client in connected_clients:
        try:
            await client.send_json(event)
        except Exception:
            dead.add(client)
    connected_clients.difference_update(dead)
```

Also modify the `import_trace_endpoint` to broadcast after saving:

```python
@app.post("/api/traces/import")
@limiter.limit(RATE_LIMIT)
def import_trace_endpoint(
    request: Request, body: ImportTraceRequest, _auth: None = Depends(verify_api_key)
) -> dict:
    try:
        trace = import_trace(body.data)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.save_trace(trace)
    asyncio.create_task(broadcast_event({"event_type": "trace_saved", "trace_id": trace.id}))
    return export_trace(trace)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_websocket.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/flight_recorder_backend/server.py backend/pyproject.toml backend/tests/test_websocket.py
git commit -m "feat(backend): add WebSocket endpoint for real-time trace streaming"
```

---

### Task 6.3: Update SDK __init__.py exports

**Files:**
- Modify: `sdk/src/flight_recorder/__init__.py`

- [ ] **Step 1: Add new exports**

```python
"""Agent Flight Recorder SDK."""

from flight_recorder.annotation_storage import AnnotationStorage
from flight_recorder.branch_storage import BranchStorage
from flight_recorder.export import (
    export_to_file,
    export_trace,
    import_from_file,
    import_trace,
)
from flight_recorder.models import (
    Annotation,
    Branch,
    Step,
    StepType,
    StreamEvent,
    Trace,
    TraceComparison,
    TraceFilter,
    TraceSession,
)
from flight_recorder.recorder import clear_last_trace, get_last_trace, record
from flight_recorder.session_storage import SessionStorage
from flight_recorder.storage import TraceStorage

__all__ = [
    "Annotation",
    "AnnotationStorage",
    "Branch",
    "BranchStorage",
    "SessionStorage",
    "Step",
    "StepType",
    "StreamEvent",
    "Trace",
    "TraceComparison",
    "TraceFilter",
    "TraceSession",
    "TraceStorage",
    "clear_last_trace",
    "export_to_file",
    "export_trace",
    "get_last_trace",
    "import_from_file",
    "import_trace",
    "record",
]
```

- [ ] **Step 2: Run all tests to verify nothing breaks**

Run: `cd sdk && python -m pytest --tb=short -q` and `cd backend && python -m pytest --tb=short -q`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add sdk/src/flight_recorder/__init__.py
git commit -m "feat(sdk): export new Phase 4 models and storage classes"
```

---

## Summary

| Task | Feature | Deliverable |
|------|---------|------------|
| 1.1 | Search | TraceFilter model |
| 1.2 | Search | search_traces storage method |
| 1.3 | Search | GET /api/traces/search endpoint |
| 2.1 | Sessions | TraceSession model |
| 2.2 | Sessions | SessionStorage class |
| 2.3 | Sessions | Session CRUD API endpoints |
| 3.1 | Annotations | Annotation model |
| 3.2 | Annotations | AnnotationStorage class |
| 3.3 | Annotations | Annotation + Tag API endpoints |
| 4.1 | Comparison | TraceComparison model |
| 4.2 | Comparison | GET /api/traces/compare endpoint |
| 5.1 | LangGraph | LangGraphAdapter class |
| 6.1 | WebSocket | StreamEvent model |
| 6.2 | WebSocket | WebSocket endpoint + broadcast |
| 6.3 | WebSocket | SDK exports update |

**Total: 15 tasks across 6 features**
