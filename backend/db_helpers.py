from contextlib import contextmanager
from config.database_config import pool
from psycopg import sql
from fastapi import HTTPException


@contextmanager
def user_scoped_connection(user_id: str):
    """
    Opens a pooled connection, starts a transaction, and sets the RLS
    session variable with SET LOCAL so it is automatically cleared when
    the transaction ends — safe to reuse this pooled connection for a
    different user's request afterward. Never use a bare SET here.
    """
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute(sql.SQL("SET LOCAL app.current_user_id = {}").format(sql.Literal(user_id)))
            yield conn


def check_or_create_thread_ownership(conn, thread_id: str, user_id: str, title: str) -> None:
    """
    Call this at the very top of /research and /research/resume, after
    get_verified_user_id and before any graph.stream() call.
    Raises HTTPException(403) if the thread belongs to someone else.
    """
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
        # Support row whether row_factory is dict_row or default tuple
        owner_id = row["user_id"] if isinstance(row, dict) else row[0]
        if owner_id != user_id:
            raise HTTPException(status_code=403, detail="This conversation does not belong to you")
        else:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = now() WHERE thread_id = %s",
                (thread_id,),
            )
