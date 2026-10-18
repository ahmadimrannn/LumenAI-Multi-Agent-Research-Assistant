import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from config.database_config import pool

DAILY_LIMIT = int(os.environ.get("DAILY_QUERY_LIMIT", "10"))
GLOBAL_LIMIT = int(os.environ.get("GLOBAL_DAILY_LIMIT", "300"))
GLOBAL_KEY = "__global__"

if DAILY_LIMIT < 1:
    raise RuntimeError("DAILY_QUERY_LIMIT must be at least 1")

_CONSUME_SQL = """
INSERT INTO usage_daily (user_id, day, count)
VALUES (%s, (now() AT TIME ZONE 'UTC')::date, 1)
ON CONFLICT (user_id, day)
DO UPDATE SET count = usage_daily.count + 1, updated_at = now()
WHERE usage_daily.count < %s
RETURNING count, day
"""


class QuotaExceeded(Exception):
    def __init__(self, kind: str, limit: int):
        super().__init__(kind)
        self.kind = kind          # "daily_limit_reached" or "service_busy"
        self.limit = limit


@dataclass
class Quota:
    limit: int
    used: int
    remaining: int
    day: date
    resets_at: datetime


def next_reset() -> datetime:
    now = datetime.now(timezone.utc)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def consume_quota(user_id: str) -> Quota:
    daily_limit = int(os.environ.get("DAILY_QUERY_LIMIT", str(DAILY_LIMIT)))
    global_limit = int(os.environ.get("GLOBAL_DAILY_LIMIT", str(GLOBAL_LIMIT)))

    with pool.connection() as conn:
        with conn.transaction():
            row = conn.execute(_CONSUME_SQL, (user_id, daily_limit)).fetchone()
            if row is None:
                raise QuotaExceeded("daily_limit_reached", daily_limit)
            used = row["count"] if isinstance(row, dict) else row[0]
            day = row["day"] if isinstance(row, dict) else row[1]
            if global_limit > 0:
                g = conn.execute(_CONSUME_SQL, (GLOBAL_KEY, global_limit)).fetchone()
                if g is None:
                    # Raising here rolls back the user's increment too.
                    raise QuotaExceeded("service_busy", global_limit)

    # Periodic cleanup outside the transaction with 2% probability
    if random.random() < 0.02:
        try:
            with pool.connection() as conn:
                conn.execute(
                    "DELETE FROM usage_daily WHERE day < (now() AT TIME ZONE 'UTC')::date - 35"
                )
        except Exception as e:
            print("USAGE CLEANUP FAILED:", e)

    return Quota(daily_limit, used, daily_limit - used, day, next_reset())


def refund_quota(user_id: str, day: date) -> None:
    global_limit = int(os.environ.get("GLOBAL_DAILY_LIMIT", str(GLOBAL_LIMIT)))
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute(
                "UPDATE usage_daily SET count = GREATEST(count - 1, 0) WHERE user_id = %s AND day = %s",
                (user_id, day),
            )
            if global_limit > 0:
                conn.execute(
                    "UPDATE usage_daily SET count = GREATEST(count - 1, 0) WHERE user_id = %s AND day = %s",
                    (GLOBAL_KEY, day),
                )


def get_usage(user_id: str) -> Quota:
    daily_limit = int(os.environ.get("DAILY_QUERY_LIMIT", str(DAILY_LIMIT)))
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT count, day FROM usage_daily WHERE user_id = %s AND day = (now() AT TIME ZONE 'UTC')::date",
            (user_id,),
        ).fetchone()
    used = (row["count"] if isinstance(row, dict) else row[0]) if row else 0
    today = datetime.now(timezone.utc).date()
    return Quota(daily_limit, used, max(daily_limit - used, 0), today, next_reset())


class QuotaTicket:
    """Makes sure one consumed unit is refunded at most once."""

    def __init__(self, user_id: str, day: date):
        self.user_id = user_id
        self.day = day
        self._refunded = False

    def refund_once(self) -> None:
        if self._refunded:
            return
        self._refunded = True
        try:
            refund_quota(self.user_id, self.day)
        except Exception as e:
            print("REFUND FAILED:", e)


def usage_headers(q: Quota) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(q.limit),
        "X-RateLimit-Remaining": str(q.remaining),
        "X-RateLimit-Reset": q.resets_at.isoformat(),
    }
