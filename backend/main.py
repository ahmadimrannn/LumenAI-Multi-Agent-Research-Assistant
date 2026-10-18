import os
import sys
import uuid
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Callable, Generator, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from executor import graph_executor_stream
from resume_graph import resume_graph_stream
from event_logger import log_event
from config.database_config import pool
from auth_dependency import get_verified_user_id
from db_helpers import user_scoped_connection, check_or_create_thread_ownership

# Agents print LLM output containing characters outside Windows' default cp1252
# stdout encoding, which would raise UnicodeEncodeError mid-graph.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


app = FastAPI()

# --- CORS Configuration ---
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000"
)

# Strip trailing slashes from origins to prevent browser CORS preflight mismatches
parsed_origins = [o.strip().rstrip("/") for o in ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=parsed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Thread-Id", "Content-Type"],
)

# --- Pydantic Schemas ---
class ResearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class ResumeRequest(BaseModel):
    thread_id: str
    action: str
    edited_query: Optional[str] = None


def _sse_stream(
    generator_factory: Callable[[], Generator[dict[str, Any], None, None]],
    thread_id: str,
    log_route: str,
    log_context: dict[str, Any],
):
    async def event_generator():
        try:
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def run_stream():
                try:
                    for event in generator_factory():
                        asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)
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


# --- Authenticated Endpoints ---
@app.get("/sessions")
async def list_sessions(user_id: str = Depends(get_verified_user_id)):
    with user_scoped_connection(user_id) as conn:
        rows = conn.execute(
            "SELECT thread_id, title, created_at, updated_at "
            "FROM chat_sessions WHERE user_id = %s ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()

    return {
        "sessions": [
            {
                "id": r["thread_id"] if isinstance(r, dict) else r[0],
                "title": r["title"] if isinstance(r, dict) else r[1],
                "createdAt": (r["created_at"] if isinstance(r, dict) else r[2]).isoformat(),
                "updatedAt": (r["updated_at"] if isinstance(r, dict) else r[3]).isoformat(),
            }
            for r in rows
        ]
    }


@app.post("/research")
async def start_research(
    body: ResearchRequest,
    user_id: str = Depends(get_verified_user_id),
):
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=400, detail="Can't fetch results without a query.")

    thread_id = body.thread_id or str(uuid.uuid4())

    with user_scoped_connection(user_id) as conn:
        check_or_create_thread_ownership(conn, thread_id, user_id, body.query)

    return _sse_stream(
        generator_factory=lambda: graph_executor_stream(query=body.query, thread_id=thread_id),
        thread_id=thread_id,
        log_route="/research",
        log_context={"query": body.query, "user_id": user_id, "thread_id": thread_id},
    )


@app.post("/research/resume")
async def resume_research(
    body: ResumeRequest,
    user_id: str = Depends(get_verified_user_id),
):
    if body.action not in {"approve", "reject", "edit"}:
        raise HTTPException(status_code=400, detail="Invalid Action")

    if body.action == "edit" and (not body.edited_query or not body.edited_query.strip()):
        raise HTTPException(
            status_code=400,
            detail="edited_query is required when action = 'edit'.",
        )

    with user_scoped_connection(user_id) as conn:
        check_or_create_thread_ownership(conn, body.thread_id, user_id, body.edited_query or "")

    return _sse_stream(
        generator_factory=lambda: resume_graph_stream(
            thread_id=body.thread_id,
            action=body.action,
            edited_query=body.edited_query,
        ),
        thread_id=body.thread_id,
        log_route="/research/resume",
        log_context={"user_id": user_id, "thread_id": body.thread_id, "action": body.action},
    )


# --- Public Endpoints ---
@app.get("/health")
async def health_check():
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=f"DB unreachable: {str(e)}"
        )