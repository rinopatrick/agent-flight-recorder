import asyncio
import os
import time
from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from flight_recorder import Annotation, Branch, export_trace, import_trace
from flight_recorder.models import TraceSession
from flight_recorder.log_config import get_logger
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.websockets import WebSocket

from flight_recorder_backend.db import Database
from flight_recorder_backend.replay import ReplayEngine
from flight_recorder_backend.test_generator import TestGenerator

logger = get_logger(__name__)


class CreateBranchRequest(BaseModel):
    name: str
    fork_step_index: int
    modifications: dict = {}


class ForkRequest(BaseModel):
    name: str
    fork_step_index: int
    modifications: dict = {}


class ImportTraceRequest(BaseModel):
    data: dict


class CreateAnnotationRequest(BaseModel):
    content: str
    tags: list[str] = []


class CreateSessionRequest(BaseModel):
    name: str


API_KEY = os.environ.get("FLIGHT_RECORDER_API_KEY")
RATE_LIMIT = os.environ.get("FLIGHT_RECORDER_RATE_LIMIT", "100/minute")

security = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if API_KEY is None:
        return
    if credentials is None or credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:  # type: ignore[override]
    raise HTTPException(status_code=429, detail="Rate limit exceeded")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.perf_counter()
        logger.info("Request: %s %s", request.method, request.url.path)
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Response: %s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def create_app(db: Database) -> FastAPI:
    app = FastAPI()
    connected_clients: set[WebSocket] = set()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/api/health")
    @limiter.limit(RATE_LIMIT)
    def health(request: Request) -> dict:
        db_status = "ok"
        try:
            with Session(db._engine) as session:
                session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {str(e)}"

        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "version": "0.4.0",
            "database": db_status,
            "timestamp": time.time(),
        }

    @app.get("/api/metrics")
    @limiter.limit(RATE_LIMIT)
    def metrics(
        request: Request, _auth: None = Depends(verify_api_key)
    ) -> dict:
        traces = db.list_traces(limit=1000)
        total_cost = sum(t.total_cost() for t in traces)
        total_steps = sum(len(t.steps) for t in traces)

        return {
            "total_traces": len(traces),
            "total_steps": total_steps,
            "total_cost": round(total_cost, 4),
            "avg_steps_per_trace": round(total_steps / len(traces), 1) if traces else 0,
        }

    @app.get("/api/traces")
    @limiter.limit(RATE_LIMIT)
    def list_traces(
        request: Request, _auth: None = Depends(verify_api_key)
    ) -> list[dict]:
        traces = db.list_traces()
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

    @app.get("/api/traces/search")
    @limiter.limit(RATE_LIMIT)
    def search_traces_endpoint(
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

    @app.get("/api/traces/compare")
    @limiter.limit(RATE_LIMIT)
    def compare_traces(
        request: Request, a: str, b: str, _auth: None = Depends(verify_api_key)
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

    @app.get("/api/traces/{trace_id}")
    @limiter.limit(RATE_LIMIT)
    def get_trace(
        request: Request, trace_id: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {
            "id": trace.id,
            "agent_name": trace.agent_name,
            "created_at": trace.created_at.isoformat(),
            "metadata": trace.metadata,
            "steps": [
                {
                    "index": s.index,
                    "step_type": s.step_type.value,
                    "name": s.name,
                    "input_data": s.input_data,
                    "output_data": s.output_data,
                    "tokens_in": s.tokens_in,
                    "tokens_out": s.tokens_out,
                    "cost": s.cost,
                    "duration_ms": s.duration_ms,
                    "context_snapshot": s.context_snapshot,
                    "error": s.error,
                }
                for s in trace.steps
            ],
        }

    @app.post("/api/traces/{trace_id}/branches")
    @limiter.limit(RATE_LIMIT)
    def create_branch(
        request: Request,
        trace_id: str,
        body: CreateBranchRequest,
        _auth: None = Depends(verify_api_key),
    ) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        branch = Branch(
            name=body.name,
            parent_trace_id=trace_id,
            fork_step_index=body.fork_step_index,
            modifications=body.modifications,
        )
        db.branches.save_branch(branch)
        return _branch_to_dict(branch)

    @app.get("/api/traces/{trace_id}/branches")
    @limiter.limit(RATE_LIMIT)
    def list_branches_for_trace(
        request: Request, trace_id: str, _auth: None = Depends(verify_api_key)
    ) -> list[dict]:
        branches = db.branches.list_branches_for_trace(trace_id)
        return [_branch_summary(b) for b in branches]

    @app.get("/api/branches/{branch_id}")
    @limiter.limit(RATE_LIMIT)
    def get_branch(
        request: Request, branch_id: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        branch = db.branches.get_branch(branch_id)
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        return _branch_to_dict(branch)

    @app.delete("/api/branches/{branch_id}")
    @limiter.limit(RATE_LIMIT)
    def delete_branch(
        request: Request, branch_id: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        branch = db.branches.get_branch(branch_id)
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        db.branches.delete_branch(branch_id)
        return {"deleted": branch_id}

    @app.post("/api/traces/{trace_id}/fork")
    @limiter.limit(RATE_LIMIT)
    def fork_trace(
        request: Request,
        trace_id: str,
        body: ForkRequest,
        _auth: None = Depends(verify_api_key),
    ) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        if body.fork_step_index < 0 or body.fork_step_index > len(trace.steps):
            raise HTTPException(
                status_code=400,
                detail=f"fork_step_index must be between 0 and {len(trace.steps)}",
            )
        engine = ReplayEngine()
        branch = engine.create_branch_from_trace(
            trace=trace,
            fork_step_index=body.fork_step_index,
            name=body.name,
            modifications=body.modifications,
        )
        db.branches.save_branch(branch)
        return _branch_to_dict(branch)

    @app.get("/api/traces/{trace_id}/export")
    @limiter.limit(RATE_LIMIT)
    def export_trace_endpoint(
        request: Request, trace_id: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return export_trace(trace)

    @app.post("/api/traces/import")
    @limiter.limit(RATE_LIMIT)
    async def import_trace_endpoint(
        request: Request, body: ImportTraceRequest, _auth: None = Depends(verify_api_key)
    ) -> dict:
        try:
            trace = import_trace(body.data)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        db.save_trace(trace)
        asyncio.create_task(broadcast_event({"event_type": "trace_saved", "trace_id": trace.id}))
        return export_trace(trace)

    @app.post("/api/traces/{trace_id}/generate-test")
    @limiter.limit(RATE_LIMIT)
    def generate_test(
        request: Request, trace_id: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        generator = TestGenerator()
        test_code = generator.generate_test(trace)
        return {"test_code": test_code, "trace_id": trace_id}

    # --- Session endpoints ---

    @app.post("/api/sessions")
    @limiter.limit(RATE_LIMIT)
    def create_session(
        request: Request,
        body: CreateSessionRequest,
        _auth: None = Depends(verify_api_key),
    ) -> dict:
        session = TraceSession(name=body.name)
        db.sessions.save_session(session)
        return _session_to_dict(session)

    @app.get("/api/sessions")
    @limiter.limit(RATE_LIMIT)
    def list_sessions(
        request: Request, _auth: None = Depends(verify_api_key)
    ) -> list[dict]:
        sessions = db.sessions.list_sessions()
        return [_session_to_dict(s) for s in sessions]

    @app.get("/api/sessions/{session_id}")
    @limiter.limit(RATE_LIMIT)
    def get_session(
        request: Request, session_id: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        session = db.sessions.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return _session_to_dict(session)

    @app.post("/api/sessions/{session_id}/traces/{trace_id}")
    @limiter.limit(RATE_LIMIT)
    def add_trace_to_session(
        request: Request,
        session_id: str,
        trace_id: str,
        _auth: None = Depends(verify_api_key),
    ) -> dict:
        session = db.sessions.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        db.sessions.add_trace_to_session(session_id, trace_id)
        return {"added": trace_id}

    @app.delete("/api/sessions/{session_id}/traces/{trace_id}")
    @limiter.limit(RATE_LIMIT)
    def remove_trace_from_session(
        request: Request,
        session_id: str,
        trace_id: str,
        _auth: None = Depends(verify_api_key),
    ) -> dict:
        session = db.sessions.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        db.sessions.remove_trace_from_session(session_id, trace_id)
        return {"removed": trace_id}

    # --- WebSocket endpoint ---

    async def broadcast_event(event: dict) -> None:
        dead = set()
        for client in connected_clients:
            try:
                await client.send_json(event)
            except Exception:
                dead.add(client)
        connected_clients.difference_update(dead)

    @app.websocket("/api/ws/traces")
    async def websocket_traces(websocket: WebSocket):
        await websocket.accept()
        connected_clients.add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            connected_clients.discard(websocket)

    # --- Annotation endpoints ---

    @app.post("/api/traces/{trace_id}/annotations")
    @limiter.limit(RATE_LIMIT)
    def create_annotation(
        request: Request,
        trace_id: str,
        body: CreateAnnotationRequest,
        _auth: None = Depends(verify_api_key),
    ) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        annotation = Annotation(trace_id=trace_id, content=body.content, tags=body.tags)
        db.annotations.save_annotation(annotation)
        return _annotation_to_dict(annotation)

    @app.get("/api/traces/{trace_id}/annotations")
    @limiter.limit(RATE_LIMIT)
    def list_annotations(
        request: Request, trace_id: str, _auth: None = Depends(verify_api_key)
    ) -> list[dict]:
        annotations = db.annotations.get_annotations_for_trace(trace_id)
        return [_annotation_to_dict(a) for a in annotations]

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
        return {"added": tag}

    @app.delete("/api/annotations/{annotation_id}/tags/{tag}")
    @limiter.limit(RATE_LIMIT)
    def remove_tag(
        request: Request, annotation_id: str, tag: str, _auth: None = Depends(verify_api_key)
    ) -> dict:
        db.annotations.remove_tag(annotation_id, tag)
        return {"removed": tag}

    return app


def _annotation_to_dict(annotation: Annotation) -> dict:
    return {
        "id": annotation.id,
        "trace_id": annotation.trace_id,
        "content": annotation.content,
        "tags": annotation.tags,
        "created_at": annotation.created_at.isoformat(),
    }


def _session_to_dict(session: TraceSession) -> dict:
    return {
        "id": session.id,
        "name": session.name,
        "trace_ids": session.trace_ids,
        "created_at": session.created_at.isoformat(),
        "metadata": session.metadata,
    }


def _branch_summary(branch: Branch) -> dict:
    return {
        "id": branch.id,
        "name": branch.name,
        "parent_trace_id": branch.parent_trace_id,
        "fork_step_index": branch.fork_step_index,
        "created_at": branch.created_at.isoformat(),
    }


def _branch_to_dict(branch: Branch) -> dict:
    return {
        "id": branch.id,
        "name": branch.name,
        "parent_trace_id": branch.parent_trace_id,
        "fork_step_index": branch.fork_step_index,
        "modifications": branch.modifications,
        "created_at": branch.created_at.isoformat(),
        "steps": [
            {
                "index": s.index,
                "step_type": s.step_type.value,
                "name": s.name,
                "input_data": s.input_data,
                "output_data": s.output_data,
                "tokens_in": s.tokens_in,
                "tokens_out": s.tokens_out,
                "cost": s.cost,
                "duration_ms": s.duration_ms,
                "context_snapshot": s.context_snapshot,
                "error": s.error,
            }
            for s in branch.steps
        ],
    }
