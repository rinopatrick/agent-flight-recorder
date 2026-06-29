import os
import time
from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from flight_recorder import Branch, export_trace, import_trace
from flight_recorder.log_config import get_logger
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

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
        return {"status": "ok"}

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
    def import_trace_endpoint(
        request: Request, body: ImportTraceRequest, _auth: None = Depends(verify_api_key)
    ) -> dict:
        try:
            trace = import_trace(body.data)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        db.save_trace(trace)
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

    return app


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
