import os
import uuid
import json
import asyncio
from typing import Optional, Callable, Generator, Any, AsyncGenerator

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from executor import graph_executor_stream
from resume_graph import resume_graph_stream
from event_logger import log_event
from config.database_config import pool
from auth.security import get_current_user_id

app = FastAPI()
router = APIRouter()

# --- CORS Configuration ---
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---
class ResearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class ResumeRequest(BaseModel):
    thread_id: str
    action: str
    edited_query: Optional[str] = None

# --- Helper Functions ---
async def verify_or_create_thread_ownership(
    user_id: str, 
    thread_id: Optional[str], 
    initial_query: str = ""
) -> str:
    """
    Guarantees thread ownership before touching LangGraph state.
    Returns the validated or newly created thread_id.
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if thread_id:
                await cur.execute(
                    "SELECT user_id FROM chat_sessions WHERE thread_id = %s;",
                    (thread_id,)
                )
                row = await cur.fetchone()
                if row is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Requested thread session does not exist."
                    )
                if row[0] != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You do not own this research session."
                    )
                return thread_id
            else:
                new_thread_id = str(uuid.uuid4())
                title_preview = (initial_query[:45] + "...") if len(initial_query) > 45 else initial_query
                await cur.execute(
                    """
                    INSERT INTO chat_sessions (id, thread_id, user_id, title)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (str(uuid.uuid4()), new_thread_id, user_id, title_preview or "New Research")
                )
                await conn.commit()
                return new_thread_id

def _sse_stream(
    generator_factory: Callable[[], Generator[dict[str, Any], None, None]],
    thread_id: str,
    log_route: str,
    log_context: dict[str, Any],
):
    """
    Runs the blocking graph stream generator in a background thread executor 
    and forwards events asynchronously to SSE responses.
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

# --- Authenticated Router Endpoints ---
@router.get("/sessions")
async def get_user_sessions(user_id: str = Depends(get_current_user_id)):
    """Fetches all chat sessions for the authenticated user using RLS."""
    sessions = []
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("SET LOCAL app.current_user_id = %s;", (user_id,))
                await cur.execute(
                    """
                    SELECT id, thread_id, title, created_at, updated_at 
                    FROM chat_sessions 
                    ORDER BY updated_at DESC;
                    """
                )
                rows = await cur.fetchall()
                for row in rows:
                    sessions.append({
                        "id": str(row[0]),
                        "thread_id": row[1],
                        "title": row[2],
                        "created_at": row[3].isoformat(),
                        "updated_at": row[4].isoformat()
                    })
    return {"sessions": sessions}

@router.post("/research")
async def start_research(
    body: ResearchRequest,
    user_id: str = Depends(get_current_user_id)
):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Can't fetch results without a query.")

    validated_thread_id = await verify_or_create_thread_ownership(
        user_id=user_id, 
        thread_id=body.thread_id, 
        initial_query=body.query
    )

    user_scoped_thread = f"{user_id}::{validated_thread_id}"

    return _sse_stream(
        generator_factory=lambda: graph_executor_stream(query=body.query, thread_id=user_scoped_thread),
        thread_id=validated_thread_id,
        log_route="/research",
        log_context={"query": body.query, "user_id": user_id, "thread_id": validated_thread_id},
    )

@router.post("/research/resume")
async def resume_research(
    body: ResumeRequest,
    user_id: str = Depends(get_current_user_id)
):
    if body.action not in {"approve", "reject", "edit"}:
        raise HTTPException(status_code=400, detail="Invalid Action")

    if body.action == "edit" and (not body.edited_query or not body.edited_query.strip()):
        raise HTTPException(
            status_code=400,
            detail="edited_query is required when action = 'edit'.",
        )

    validated_thread_id = await verify_or_create_thread_ownership(
        user_id=user_id, 
        thread_id=body.thread_id
    )

    user_scoped_thread = f"{user_id}::{validated_thread_id}"

    return _sse_stream(
        generator_factory=lambda: resume_graph_stream(
            thread_id=user_scoped_thread,
            action=body.action,
            edited_query=body.edited_query,
        ),
        thread_id=validated_thread_id,
        log_route="/research/resume",
        log_context={"user_id": user_id, "thread_id": validated_thread_id, "action": body.action},
    )

# --- Public Endpoints ---
@app.get("/health")
def health_check():
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db unreachable: {str(e)}")

# Mount the router to the main FastAPI app
app.include_router(router)