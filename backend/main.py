from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json

from executor import graph_executor_stream, resume_graph
from event_logger import log_event
from config.database_config import pool

app = FastAPI()


class ResearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


class ResumeRequest(BaseModel):
    thread_id: str
    action: str
    edited_query: Optional[str] = None


@app.get("/health")
def health_check():
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db unreachable: {str(e)}")


@app.post("/research")
async def get_findings(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(
            status_code=400, detail="Can't fetch results without a query."
        )

    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        def event_generator():
            for event in graph_executor_stream(
                query=request.query, thread_id=thread_id
            ):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Thread-Id": thread_id, 
            },
        )

    except Exception as e:
        log_event(
            service="lumen",
            event_type="api_exception",
            severity="error",
            node_or_route="/research",
            message=str(e),
            context={"query": request.query, "thread_id": thread_id},
        )
        raise HTTPException(
            status_code=500, detail=f"Can't fetch results: {str(e)}"
        )


@app.post("/research/resume")
def resume(request: ResumeRequest):
    if request.action not in {"approve", "reject", "edit"}:
        raise HTTPException(status_code=400, detail="Invalid Action")

    if request.action == "edit" and (
        request.edited_query is None or not request.edited_query.strip()
    ):
        raise HTTPException(
            status_code=400,
            detail="edited_query is required when action = 'edit'.",
        )

    try:
        result = resume_graph(
            action=request.action,
            thread_id=request.thread_id,
            edited_query=request.edited_query,
        )
        return result

    except Exception as e:
        log_event(
            service="lumen",
            event_type="api_exception",
            severity="error",
            node_or_route="/research/resume",
            message=str(e),
            context={
                "thread_id": request.thread_id,
                "action": request.action,
            },
        )
        raise HTTPException(
            status_code=400, detail=f"Can't fetch results: {str(e)}"
        )