from fastapi import FastAPI, HTTPException

from flight_recorder_backend.db import Database


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

    return app
