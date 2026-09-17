from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Callable, Generator, Any
import os
import uuid
import json
import asyncio

from executor import graph_executor_stream
from resume_graph import resume_graph_stream
from event_logger import log_event
from config.database_config import pool

app = FastAPI()

_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


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


def _sse_stream(
    generator_factory: Callable[[], Generator[dict[str, Any], None, None]],
    thread_id: str,
    log_route: str,
    log_context: dict[str, Any],
):
    """
    Shared plumbing for both /research and /research/resume: runs the
    blocking graph.stream() generator in a background thread and forwards
    each event onto an asyncio queue, so FastAPI can await it without
    blocking the event loop. Both endpoints get identical event framing.
    """

    async def event_generator():
        try:
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def run_stream():
                try:
                    for event in generator_factory():
                        asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel
                except Exception as e:
                    log_event(
                        service="lumen",
                        event_type="api_exception",
                        severity="error",
                        node_or_route=log_route,
                        message=str(e),
                        context=log_context,
                    )
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "error", "status": "error", "thread_id": thread_id, "error": str(e)}),
                        loop,
                    )
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            loop.run_in_executor(None, run_stream)

            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_event = {
                "type": "error",
                "status": "error",
                "thread_id": thread_id,
                "error": str(e),
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
            "X-Thread-Id": thread_id,
        },
    )


@app.post("/research")
async def get_findings(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Can't fetch results without a query.")

    thread_id = request.thread_id or str(uuid.uuid4())

    return _sse_stream(
        generator_factory=lambda: graph_executor_stream(query=request.query, thread_id=thread_id),
        thread_id=thread_id,
        log_route="/research",
        log_context={"query": request.query, "thread_id": thread_id},
    )


@app.post("/research/resume")
async def resume(request: ResumeRequest):
    if request.action not in {"approve", "reject", "edit"}:
        raise HTTPException(status_code=400, detail="Invalid Action")

    if request.action == "edit" and (
        request.edited_query is None or not request.edited_query.strip()
    ):
        raise HTTPException(
            status_code=400,
            detail="edited_query is required when action = 'edit'.",
        )

    return _sse_stream(
        generator_factory=lambda: resume_graph_stream(
            thread_id=request.thread_id,
            action=request.action,
            edited_query=request.edited_query,
        ),
        thread_id=request.thread_id,
        log_route="/research/resume",
        log_context={"thread_id": request.thread_id, "action": request.action},
    )