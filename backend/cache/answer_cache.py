import hashlib
import json
import os
import random
import re
import unicodedata

from psycopg.types.json import Jsonb

from config.database_config import pool

PIPELINE_VERSION = os.environ.get("PIPELINE_VERSION", "1")
TTL_EXTERNAL = int(os.environ.get("CACHE_TTL_EXTERNAL_SECONDS", "86400"))
TTL_DIRECT = int(os.environ.get("CACHE_TTL_DIRECT_SECONDS", "604800"))
MAX_PAYLOAD_BYTES = 256 * 1024

_WS = re.compile(r"\s+")


def normalize_query(q: str) -> str:
    q = unicodedata.normalize("NFKC", q).strip().lower()
    q = _WS.sub(" ", q)
    return q.rstrip(" ?!.")


def cache_key(q: str) -> str:
    # Use dynamic PIPELINE_VERSION from env so test changes to env var are immediately reflected
    version = os.environ.get("PIPELINE_VERSION", PIPELINE_VERSION)
    return hashlib.sha256(f"{version}:{normalize_query(q)}".encode("utf-8")).hexdigest()


def is_cacheable(result: dict) -> bool:
    return (
        bool((result.get("response") or "").strip())
        and not result.get("termination_reason")
        and not result.get("degraded")
    )


def get_cached(query: str) -> dict | None:
    with pool.connection() as conn:
        row = conn.execute(
            "UPDATE answer_cache SET hit_count = hit_count + 1 "
            "WHERE cache_key = %s AND expires_at > now() RETURNING payload, created_at",
            (cache_key(query),),
        ).fetchone()
    if row is None:
        return None
    payload = row["payload"] if isinstance(row, dict) else row[0]
    created_at = row["created_at"] if isinstance(row, dict) else row[1]
    return {"payload": payload, "created_at": created_at}


def put_cached(query: str, result: dict) -> None:
    if not is_cacheable(result):
        return
    payload = {k: v for k, v in result.items() if k not in {"thread_id", "messages", "type", "status"}}
    if len(json.dumps(payload).encode("utf-8")) > MAX_PAYLOAD_BYTES:
        return
    external = bool(result.get("requires_external_research"))
    ttl_ext = int(os.environ.get("CACHE_TTL_EXTERNAL_SECONDS", str(TTL_EXTERNAL)))
    ttl_dir = int(os.environ.get("CACHE_TTL_DIRECT_SECONDS", str(TTL_DIRECT)))
    ttl = ttl_ext if external else ttl_dir
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO answer_cache (cache_key, query_normalized, payload, requires_external_research, expires_at) "
            "VALUES (%s, %s, %s, %s, now() + make_interval(secs => %s)) "
            "ON CONFLICT (cache_key) DO UPDATE SET payload = EXCLUDED.payload, "
            "requires_external_research = EXCLUDED.requires_external_research, "
            "created_at = now(), expires_at = EXCLUDED.expires_at, hit_count = 0",
            (cache_key(query), normalize_query(query), Jsonb(payload), external, ttl),
        )
        if random.random() < 0.02:
            try:
                conn.execute("DELETE FROM answer_cache WHERE expires_at < now()")
            except Exception as e:
                print("CACHE CLEANUP FAILED:", e)
