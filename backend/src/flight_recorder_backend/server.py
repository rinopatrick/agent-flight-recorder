from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from flight_recorder import Branch, export_trace, import_trace
from flight_recorder_backend.db import Database
from flight_recorder_backend.replay import ReplayEngine
from flight_recorder_backend.test_generator import TestGenerator


class CreateBranchRequest(BaseModel):
    name: str
    fork_step_index: int
    modifications: dict = {}


class ForkRequest(BaseModel):
    name: str
    fork_step_index: int
    modifications: dict = {}


def create_app(db: Database) -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/traces")
    def list_traces() -> list[dict]:
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
    def get_trace(trace_id: str) -> dict:
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
    def create_branch(trace_id: str, body: CreateBranchRequest) -> dict:
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
    def list_branches_for_trace(trace_id: str) -> list[dict]:
        branches = db.branches.list_branches_for_trace(trace_id)
        return [_branch_summary(b) for b in branches]

    @app.get("/api/branches/{branch_id}")
    def get_branch(branch_id: str) -> dict:
        branch = db.branches.get_branch(branch_id)
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        return _branch_to_dict(branch)

    @app.delete("/api/branches/{branch_id}")
    def delete_branch(branch_id: str) -> dict:
        branch = db.branches.get_branch(branch_id)
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        db.branches.delete_branch(branch_id)
        return {"deleted": branch_id}

    @app.post("/api/traces/{trace_id}/fork")
    def fork_trace(trace_id: str, body: ForkRequest) -> dict:
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
    def export_trace_endpoint(trace_id: str) -> dict:
        trace = db.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return export_trace(trace)

    @app.post("/api/traces/import")
    def import_trace_endpoint(body: dict) -> dict:
        try:
            trace = import_trace(body)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        db.save_trace(trace)
        return export_trace(trace)

    @app.post("/api/traces/{trace_id}/generate-test")
    def generate_test(trace_id: str) -> dict:
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
