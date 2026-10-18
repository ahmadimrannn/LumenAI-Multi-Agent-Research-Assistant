import os
import sys
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Generator, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from executor import (
    graph_executor_stream,
    seed_thread_from_cache,
    cached_events,
)
from graph_builder import graph
from resume_graph import resume_graph_stream
from event_logger import log_event
from config.database_config import pool
from auth import get_verified_user_id
from database import (
    user_scoped_connection,
    assert_thread_access,
    assert_thread_owned,
    ensure_session_row,
)
from rate_limit import (
    QuotaExceeded,
    consume_quota,
    get_usage,
    next_reset,
    usage_headers,
    QuotaTicket,
)
from cache import (
    get_cached,
    put_cached,
    is_cacheable,
)

MAX_QUERY_CHARS = int(os.environ.get("MAX_QUERY_CHARS", "2000"))

# Agents print LLM output containing characters outside Windows' default cp1252
# stdout encoding, which would raise UnicodeEncodeError mid-graph.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


app = FastAPI()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
)


# --- Pydantic Schemas ---
class ResearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class ResumeRequest(BaseModel):
    thread_id: str
    action: str
    edited_query: Optional[str] = None


def rate_limited(e: QuotaExceeded, user_id: str) -> HTTPException:
    resets_at = next_reset()
    now_utc = datetime.now(timezone.utc)
    retry_after = max(int((resets_at - now_utc).total_seconds()), 1)
    detail = {
        "code": e.kind,
        "limit": e.limit,
        "used": e.limit,
        "resetsAt": resets_at.isoformat(),
    }
    if e.kind == "daily_limit_reached":
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(e.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": resets_at.isoformat(),
        }
    else:
        headers = {
            "Retry-After": str(retry_after),
        }

    log_event(
        service="lumen",
        event_type="rate_limit_hit",
        severity="info",
        node_or_route="rate_limit",
        message=f"Rate limit hit: {e.kind}",
        context={"user_id": user_id, "kind": e.kind, "limit": e.limit},
    )
    return HTTPException(status_code=429, detail=detail, headers=headers)


def with_hooks(
    events: Generator[dict[str, Any], None, None],
    on_completed: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[dict[str, Any]], None] | None = None,
    on_exception: Callable[[Exception], None] | None = None,
) -> Generator[dict[str, Any], None, None]:
    try:
        for event in events:
            yield event
            ev_type = event.get("type") if isinstance(event, dict) else None
            if ev_type == "completed" and on_completed:
                try:
                    on_completed(event)
                except Exception as ex:
                    print("on_completed hook failed:", ex)
            elif ev_type == "error" and on_error:
                try:
                    on_error(event)
                except Exception as ex:
                    print("on_error hook failed:", ex)
    except Exception as e:
        if on_exception:
            try:
                on_exception(e)
            except Exception as ex:
                print("on_exception hook failed:", ex)
        raise


def _sse_stream(
    generator_factory: Callable[[], Generator[dict[str, Any], None, None]],
    thread_id: str,
    log_route: str,
    log_context: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
    on_exception: Callable[[Exception], None] | None = None,
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
                    if on_exception:
                        try:
                            on_exception(e)
                        except Exception as ex:
                            print("on_exception in sse_stream failed:", ex)
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
            if on_exception:
                try:
                    on_exception(e)
                except Exception as ex:
                    print("on_exception in event_generator failed:", ex)
            error_event = {
                "type": "error",
                "status": "error",
                "thread_id": thread_id,
                "error": str(e),
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    response_headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream",
        "X-Thread-Id": thread_id,
    }
    if extra_headers:
        response_headers.update(extra_headers)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=response_headers,
    )


# --- Authenticated Endpoints ---
@app.get("/sessions")
async def list_sessions(user_id: str = Depends(get_verified_user_id)):
    def _fetch():
        with user_scoped_connection(user_id) as conn:
            return conn.execute(
                "SELECT thread_id, title, created_at, updated_at "
                "FROM chat_sessions WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()

    rows = await run_in_threadpool(_fetch)
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


@app.get("/usage")
async def read_usage(user_id: str = Depends(get_verified_user_id)):
    quota = await run_in_threadpool(get_usage, user_id)
    return {
        "limit": quota.limit,
        "used": quota.used,
        "remaining": quota.remaining,
        "resetsAt": quota.resets_at.isoformat(),
    }


@app.post("/research")
async def start_research(
    body: ResearchRequest,
    user_id: str = Depends(get_verified_user_id),
):
    query = (body.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Can't fetch results without a query.")
    if len(query) > MAX_QUERY_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Query exceeds maximum allowed length of {MAX_QUERY_CHARS} characters.",
        )

    thread_id = body.thread_id or str(uuid.uuid4())
    await run_in_threadpool(assert_thread_access, user_id, thread_id)

    config = {"configurable": {"thread_id": thread_id}}
    existing_state = await run_in_threadpool(graph.get_state, config)
    is_new_thread = not bool(existing_state.values)

    if is_new_thread:
        hit = await run_in_threadpool(get_cached, query)
        if hit is not None:
            try:
                await run_in_threadpool(ensure_session_row, user_id, thread_id, query)
                await run_in_threadpool(seed_thread_from_cache, thread_id, query, hit["payload"])
                usage = await run_in_threadpool(get_usage, user_id)
                return _sse_stream(
                    generator_factory=lambda: cached_events(thread_id, hit),
                    thread_id=thread_id,
                    log_route="/research",
                    log_context={"query": query, "user_id": user_id, "thread_id": thread_id, "cached": True},
                    extra_headers=usage_headers(usage),
                )
            except Exception as ex:
                print("Cache hit handling failed, falling back to pipeline:", ex)

    try:
        quota = await run_in_threadpool(consume_quota, user_id)
    except QuotaExceeded as e:
        raise rate_limited(e, user_id)

    ticket = QuotaTicket(user_id, quota.day)
    try:
        await run_in_threadpool(ensure_session_row, user_id, thread_id, query)
    except Exception:
        ticket.refund_once()
        raise

    def on_completed(event: dict[str, Any]):
        if is_new_thread and is_cacheable(event):
            try:
                put_cached(query, event)
            except Exception as ex:
                print("put_cached failed:", ex)

    def on_error(event: dict[str, Any]):
        ticket.refund_once()

    def on_exception(ex: Exception):
        ticket.refund_once()

    def stream_factory():
        return with_hooks(
            graph_executor_stream(query=query, thread_id=thread_id),
            on_completed=on_completed,
            on_error=on_error,
            on_exception=on_exception,
        )

    return _sse_stream(
        generator_factory=stream_factory,
        thread_id=thread_id,
        log_route="/research",
        log_context={"query": query, "user_id": user_id, "thread_id": thread_id},
        extra_headers=usage_headers(quota),
        on_exception=on_exception,
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

    await run_in_threadpool(assert_thread_owned, user_id, body.thread_id)

    ticket: QuotaTicket | None = None
    if body.action == "edit":
        edited_query = body.edited_query.strip()
        if len(edited_query) > MAX_QUERY_CHARS:
            raise HTTPException(
                status_code=422,
                detail=f"Query exceeds maximum allowed length of {MAX_QUERY_CHARS} characters.",
            )
        try:
            quota = await run_in_threadpool(consume_quota, user_id)
        except QuotaExceeded as e:
            raise rate_limited(e, user_id)
        ticket = QuotaTicket(user_id, quota.day)
        extra_hdrs = usage_headers(quota)
        try:
            await run_in_threadpool(ensure_session_row, user_id, body.thread_id, edited_query)
        except Exception:
            ticket.refund_once()
            raise
    else:
        usage = await run_in_threadpool(get_usage, user_id)
        extra_hdrs = usage_headers(usage)

    def on_error(event: dict[str, Any]):
        if ticket:
            ticket.refund_once()

    def on_exception(ex: Exception):
        if ticket:
            ticket.refund_once()

    def stream_factory():
        return with_hooks(
            resume_graph_stream(
                thread_id=body.thread_id,
                action=body.action,
                edited_query=body.edited_query,
            ),
            on_completed=None,
            on_error=on_error,
            on_exception=on_exception,
        )

    return _sse_stream(
        generator_factory=stream_factory,
        thread_id=body.thread_id,
        log_route="/research/resume",
        log_context={"user_id": user_id, "thread_id": body.thread_id, "action": body.action},
        extra_headers=extra_hdrs,
        on_exception=on_exception,
    )


# --- Public Endpoints ---
@app.get("/health")
async def health_check():
    try:
        def _ping():
            with pool.connection() as conn:
                conn.execute("SELECT 1")
        await run_in_threadpool(_ping)
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=f"DB unreachable: {str(e)}"
        )