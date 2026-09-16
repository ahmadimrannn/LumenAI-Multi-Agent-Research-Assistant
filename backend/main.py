from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import asyncio

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
        raise HTTPException(status_code=400, detail="Can't fetch results without a query.")

    thread_id = request.thread_id or str(uuid.uuid4())

    async def event_generator():
        try:
            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()

            def run_stream():
                try:
                    for event in graph_executor_stream(query=request.query, thread_id=thread_id):
                        # Put events into the async queue
                        asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel
                except Exception as e:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "error", "error": str(e), "thread_id": thread_id}),
                        loop
                    )
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            # Start the blocking stream in a background thread
            loop.run_in_executor(None, run_stream)

            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            # Last safety net
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
            context={"thread_id": request.thread_id, "action": request.action},
        )
        raise HTTPException(status_code=400, detail=f"Can't fetch results: {str(e)}")