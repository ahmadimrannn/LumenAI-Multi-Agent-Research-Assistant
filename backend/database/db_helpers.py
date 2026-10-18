from contextlib import contextmanager
from config.database_config import pool
from psycopg import sql
from fastapi import HTTPException


@contextmanager
def user_scoped_connection(user_id: str):
    """
    Opens a pooled connection, starts a transaction, and sets the RLS
    session variable with SET LOCAL so it is automatically cleared when
    the transaction ends - safe to reuse this pooled connection for a
    different user's request afterward. Never use a bare SET here.
    """
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute(sql.SQL("SET LOCAL app.current_user_id = {}").format(sql.Literal(user_id)))
            yield conn


def assert_thread_access(user_id: str, thread_id: str) -> None:
    """Read only. If a row exists and belongs to another user, raise 403. If no row exists, do nothing."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM chat_sessions WHERE thread_id = %s",
            (thread_id,),
        ).fetchone()
        if row is not None:
            owner_id = row["user_id"] if isinstance(row, dict) else row[0]
            if owner_id != user_id:
                raise HTTPException(status_code=403, detail="This conversation does not belong to you")


def assert_thread_owned(user_id: str, thread_id: str) -> None:
    """For resume. No row means 404, another owner means 403."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM chat_sessions WHERE thread_id = %s",
            (thread_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        owner_id = row["user_id"] if isinstance(row, dict) else row[0]
        if owner_id != user_id:
            raise HTTPException(status_code=403, detail="This conversation does not belong to you")


def ensure_session_row(user_id: str, thread_id: str, title: str) -> None:
    """Insert the chat_sessions row if it does not exist (title is the first 120 chars of query), otherwise update updated_at."""
    with pool.connection() as conn:
        with conn.transaction():
            row = conn.execute(
                "SELECT user_id FROM chat_sessions WHERE thread_id = %s",
                (thread_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO chat_sessions (thread_id, user_id, title) VALUES (%s, %s, %s)",
                    (thread_id, user_id, title[:120]),
                )
            else:
                owner_id = row["user_id"] if isinstance(row, dict) else row[0]
                if owner_id != user_id:
                    raise HTTPException(status_code=403, detail="This conversation does not belong to you")
                conn.execute(
                    "UPDATE chat_sessions SET updated_at = now() WHERE thread_id = %s",
                    (thread_id,),
                )


def check_or_create_thread_ownership(conn, thread_id: str, user_id: str, title: str) -> None:
    """Legacy helper kept for backward compatibility."""
    row = conn.execute(
        "SELECT user_id FROM chat_sessions WHERE thread_id = %s",
        (thread_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO chat_sessions (thread_id, user_id, title) VALUES (%s, %s, %s)",
            (thread_id, user_id, title[:120]),
        )
    else:
        owner_id = row["user_id"] if isinstance(row, dict) else row[0]
        if owner_id != user_id:
            raise HTTPException(status_code=403, detail="This conversation does not belong to you")
        else:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = now() WHERE thread_id = %s",
                (thread_id,),
            )
