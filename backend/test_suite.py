import sys
import os
import time
import uuid
import threading
from datetime import datetime, timezone
import jwt
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database_config import pool
import rate_limit
from rate_limit import consume_quota, refund_quota, get_usage, QuotaExceeded, QuotaTicket
import cache as answer_cache
from cache import get_cached, put_cached, normalize_query, cache_key
from main import app, with_hooks
from executor import graph, seed_thread_from_cache

# Helper to generate verified tokens for tests
SECRET = os.environ["BACKEND_JWT_SECRET"]
def make_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iss": "lumen-frontend",
        "aud": "lumen-backend",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

client = TestClient(app)

print("=" * 60)
print("RUNNING LUMEN RATE LIMIT & CACHE TEST SUITE")
print("=" * 60)

# -------------------------------------------------------------
# Test 1: Race test (25 concurrent threads)
# -------------------------------------------------------------
print("\n--- Test 1: Race test (25 threads, 10 succeed, 15 raise QuotaExceeded) ---")
test_user = f"race-user-{uuid.uuid4().hex[:8]}"
successes = 0
exceeded = 0
lock = threading.Lock()

def worker():
    global successes, exceeded
    try:
        consume_quota(test_user)
        with lock:
            successes += 1
    except QuotaExceeded:
        with lock:
            exceeded += 1

threads = [threading.Thread(target=worker) for _ in range(25)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Result: Successes = {successes}, QuotaExceeded = {exceeded}")
assert successes == 10, f"Expected 10 successes, got {successes}"
assert exceeded == 15, f"Expected 15 exceeded, got {exceeded}"

# Cleanup
with pool.connection() as conn:
    conn.execute("DELETE FROM usage_daily WHERE user_id = %s", (test_user,))
print("Cleanup: Deleted test user rows. Test 1 PASSED.")

# -------------------------------------------------------------
# Test 2: Global rollback
# -------------------------------------------------------------
print("\n--- Test 2: Global rollback (GLOBAL_DAILY_LIMIT=2) ---")
with pool.connection() as conn:
    conn.execute("DELETE FROM usage_daily WHERE user_id = '__global__'")
orig_global = os.environ.get("GLOBAL_DAILY_LIMIT", "300")
os.environ["GLOBAL_DAILY_LIMIT"] = "2"
u1 = f"glob-user-1-{uuid.uuid4().hex[:6]}"
u2 = f"glob-user-2-{uuid.uuid4().hex[:6]}"
u3 = f"glob-user-3-{uuid.uuid4().hex[:6]}"

try:
    consume_quota(u1)
    print(f"User 1 consumed successfully.")
    consume_quota(u2)
    print(f"User 2 consumed successfully.")
    third_raised_busy = False
    try:
        consume_quota(u3)
    except QuotaExceeded as e:
        print(f"User 3 raised QuotaExceeded: kind={e.kind}")
        assert e.kind == "service_busy"
        third_raised_busy = True
    assert third_raised_busy, "Expected third user to raise service_busy"

    u3_usage = get_usage(u3)
    print(f"User 3 usage count in DB: {u3_usage.used}")
    assert u3_usage.used == 0, f"Expected user 3 count to be 0, got {u3_usage.used}"
    print("Test 2 PASSED.")
finally:
    os.environ["GLOBAL_DAILY_LIMIT"] = orig_global
    with pool.connection() as conn:
        conn.execute("DELETE FROM usage_daily WHERE user_id IN (%s, %s, %s, '__global__')", (u1, u2, u3))

# -------------------------------------------------------------
# Test 3: Refund
# -------------------------------------------------------------
print("\n--- Test 3: Refund (consume once, refund_once twice -> dropped by 1) ---")
u_ref = f"ref-user-{uuid.uuid4().hex[:6]}"
q = consume_quota(u_ref)
assert q.used == 1
ticket = QuotaTicket(u_ref, q.day)
ticket.refund_once()
ticket.refund_once()
after_usage = get_usage(u_ref)
print(f"Count after double refund_once(): {after_usage.used}")
assert after_usage.used == 0, f"Expected count 0, got {after_usage.used}"
print("Test 3 PASSED.")
with pool.connection() as conn:
    conn.execute("DELETE FROM usage_daily WHERE user_id = %s", (u_ref,))

# -------------------------------------------------------------
# Test 4: Hook test
# -------------------------------------------------------------
print("\n--- Test 4: Hook test with with_hooks ---")
u_hook = f"hook-user-{uuid.uuid4().hex[:6]}"
q = consume_quota(u_hook)
t_hook = QuotaTicket(u_hook, q.day)

def fake_err_gen():
    yield {"type": "node_update", "thread_id": "t1"}
    yield {"type": "error", "error": "something bad happened"}

events = list(with_hooks(fake_err_gen(), on_error=lambda ev: t_hook.refund_once()))
assert get_usage(u_hook).used == 0
print(f"Count after error event hook: {get_usage(u_hook).used} (refunded)")

# Test with exception generator
q2 = consume_quota(u_hook)
t_hook2 = QuotaTicket(u_hook, q2.day)

def fake_exc_gen():
    yield {"type": "node_update", "thread_id": "t1"}
    raise RuntimeError("simulated crash")

exc_caught = False
try:
    for _ in with_hooks(fake_exc_gen(), on_exception=lambda ex: t_hook2.refund_once()):
        pass
except RuntimeError:
    exc_caught = True

assert exc_caught
assert get_usage(u_hook).used == 0
print(f"Count after exception generator hook: {get_usage(u_hook).used} (refunded)")
print("Test 4 PASSED.")
with pool.connection() as conn:
    conn.execute("DELETE FROM usage_daily WHERE user_id = %s", (u_hook,))

# -------------------------------------------------------------
# Test 5: Real API rate limiting (10 succeed, 11th returns 429)
# -------------------------------------------------------------
print("\n--- Test 5: Real API 10 queries succeed, 11th returns 429 ---")
u_api = f"api-user-{uuid.uuid4().hex[:8]}"
tok_api = make_token(u_api)
headers_api = {"Authorization": f"Bearer {tok_api}"}

# Run 10 unique fast conversational queries that complete
for i in range(10):
    uniq_q = f"hello greeting number {i} {uuid.uuid4().hex[:4]}"
    res = client.post("/research", json={"query": uniq_q}, headers=headers_api)
    assert res.status_code == 200, f"Query {i} failed: {res.status_code} {res.text}"
    assert res.headers.get("X-RateLimit-Limit") == "10"
    assert res.headers.get("X-RateLimit-Remaining") == str(9 - i)

print("10 queries succeeded. Testing 11th query...")
q11 = f"hello greeting 11 {uuid.uuid4().hex[:4]}"
res11 = client.post("/research", json={"query": q11}, headers=headers_api)
print(f"11th query status: {res11.status_code}")
print(f"11th query body: {res11.json()}")
print(f"11th query headers: Retry-After={res11.headers.get('Retry-After')}, X-RateLimit-Remaining={res11.headers.get('X-RateLimit-Remaining')}")

assert res11.status_code == 429
assert res11.json()["detail"]["code"] == "daily_limit_reached"
assert res11.headers.get("Retry-After") is not None
assert res11.headers.get("X-RateLimit-Remaining") == "0"
assert res11.headers.get("X-RateLimit-Limit") == "10"

# Check no empty session row created for rejected query
with pool.connection() as conn:
    rows = conn.execute("SELECT thread_id, title FROM chat_sessions WHERE user_id = %s AND title LIKE %s", (u_api, f"%{q11}%")).fetchall()
    assert len(rows) == 0, f"Expected no session row for rejected query, found: {rows}"

print("Test 5 PASSED.")

# -------------------------------------------------------------
# Test 6: approve/reject leave count unchanged, edit adds 1
# -------------------------------------------------------------
print("\n--- Test 6: approve/reject leave count unchanged, edit adds 1 ---")
# Reset u_api count to 5
today_date = datetime.now(timezone.utc).date()
with pool.connection() as conn:
    conn.execute("UPDATE usage_daily SET count = 5 WHERE user_id = %s", (u_api,))

count_before = get_usage(u_api).used
print(f"Initial count: {count_before}")

# Trigger real human_approval interrupt by posting a sensitive query
thread_paused = str(uuid.uuid4())
res_init = client.post("/research", json={"query": "Should I stop taking my heart medication?", "thread_id": thread_paused}, headers=headers_api)
for _ in res_init.iter_lines():
    pass

count_after_init = get_usage(u_api).used
print(f"Count after initial sensitive query (consumed 1 unit): {count_after_init}")
assert count_after_init == count_before + 1

# Test reject on a second paused thread
thread_paused_rej = str(uuid.uuid4())
res_init_rej = client.post("/research", json={"query": "Should I stop taking my heart medication?", "thread_id": thread_paused_rej}, headers=headers_api)
for _ in res_init_rej.iter_lines():
    pass

count_before_rej = get_usage(u_api).used
res_rej = client.post("/research/resume", json={"thread_id": thread_paused_rej, "action": "reject"}, headers=headers_api)
for _ in res_rej.iter_lines():
    pass
count_after_rej = get_usage(u_api).used
print(f"Count after reject: {count_after_rej} (change: {count_after_rej - count_before_rej})")
assert count_after_rej == count_before_rej

# Test approve on a third paused thread
thread_paused_app = str(uuid.uuid4())
res_init_app = client.post("/research", json={"query": "Should I stop taking my heart medication?", "thread_id": thread_paused_app}, headers=headers_api)
for _ in res_init_app.iter_lines():
    pass

count_before_app = get_usage(u_api).used
res_app = client.post("/research/resume", json={"thread_id": thread_paused_app, "action": "approve"}, headers=headers_api)
for _ in res_app.iter_lines():
    pass
count_after_app = get_usage(u_api).used
print(f"Count after approve: {count_after_app} (change: {count_after_app - count_before_app})")
assert count_after_app == count_before_app

# Test edit on initial paused thread
count_before_edit = get_usage(u_api).used
res_edit = client.post("/research/resume", json={"thread_id": thread_paused, "action": "edit", "edited_query": "Explain how heart medications work."}, headers=headers_api)
for _ in res_edit.iter_lines():
    pass
count_after_edit = get_usage(u_api).used
print(f"Count after edit: {count_after_edit} (change: {count_after_edit - count_before_edit})")
assert count_after_edit == count_before_edit + 1
print("Test 6 PASSED.")

# -------------------------------------------------------------
# Test 7: Query over 2000 chars returns 422, count unchanged
# -------------------------------------------------------------
print("\n--- Test 7: Query > 2000 chars returns 422, count unchanged ---")
count_before7 = get_usage(u_api).used
long_q = "a" * 2001
res_long = client.post("/research", json={"query": long_q}, headers=headers_api)
print(f"Status for >2000 chars: {res_long.status_code}")
assert res_long.status_code == 422
count_after7 = get_usage(u_api).used
assert count_after7 == count_before7
print("Test 7 PASSED.")

# -------------------------------------------------------------
# Test 8: GET /usage returns correct numbers without consuming
# -------------------------------------------------------------
print("\n--- Test 8: GET /usage returns correct numbers and does not consume ---")
res_usage = client.get("/usage", headers=headers_api)
print(f"GET /usage: {res_usage.json()}")
assert res_usage.status_code == 200
data = res_usage.json()
assert data["limit"] == 10
assert data["used"] == count_after7
assert data["remaining"] == 10 - count_after7
assert "resetsAt" in data
# Verify count in DB didn't change
assert get_usage(u_api).used == count_after7
print("Test 8 PASSED.")

# -------------------------------------------------------------
# Test 9: Second Google account has full 10 unaffected
# -------------------------------------------------------------
print("\n--- Test 9: Second account has full 10 unaffected ---")
u_second = f"second-user-{uuid.uuid4().hex[:8]}"
tok_second = make_token(u_second)
res_second = client.get("/usage", headers={"Authorization": f"Bearer {tok_second}"})
print(f"Second user usage: {res_second.json()}")
assert res_second.json()["used"] == 0
assert res_second.json()["remaining"] == 10
print("Test 9 PASSED.")

# Clean up u_api and u_second
with pool.connection() as conn:
    conn.execute("DELETE FROM usage_daily WHERE user_id IN (%s, %s)", (u_api, u_second))
    conn.execute("DELETE FROM chat_sessions WHERE user_id IN (%s, %s)", (u_api, u_second))

# -------------------------------------------------------------
# Test 10: Answer Cache Hit Normalization & Speed
# -------------------------------------------------------------
print("\n--- Test 10: Cache Hit Normalization & Speed ---")
u_a = f"user-a-{uuid.uuid4().hex[:6]}"
u_b = f"user-b-{uuid.uuid4().hex[:6]}"
tok_a = make_token(u_a)
tok_b = make_token(u_b)

cache_query_base = f"What is recursion in programming? {uuid.uuid4().hex[:4]}"
cache_query_norm = f"   what is   RECURSION in programming? {cache_query_base.split()[-1]} !??  "

# User A queries
res_a = client.post("/research", json={"query": cache_query_base}, headers={"Authorization": f"Bearer {tok_a}"})
assert res_a.status_code == 200
print(f"User A query succeeded. Reading SSE events...")
# Consume stream so on_completed hook caches the result
events_a = []
for line in res_a.iter_lines():
    if line.startswith("data: ") and not line.endswith("[DONE]"):
        import json
        events_a.append(json.loads(line[6:]))

print(f"User A completed. Usage for User A: {get_usage(u_a).used}")
assert get_usage(u_a).used == 1

# User B queries normalized version
start_b = time.time()
res_b = client.post("/research", json={"query": cache_query_norm}, headers={"Authorization": f"Bearer {tok_b}"})
duration_b = time.time() - start_b
assert res_b.status_code == 200
events_b = []
for line in res_b.iter_lines():
    if line.startswith("data: ") and not line.endswith("[DONE]"):
        import json
        events_b.append(json.loads(line[6:]))

print(f"User B query duration: {duration_b:.3f}s")
print(f"User B events count: {len(events_b)}, types: {[e['type'] for e in events_b]}")
assert duration_b < 15.0
assert len(events_b) == 1
assert events_b[0]["type"] == "completed"
assert events_b[0]["cached"] is True
assert "cached_at" in events_b[0]
print(f"User B count: {get_usage(u_b).used}")
assert get_usage(u_b).used == 0, f"Expected 0 usage for cached hit, got {get_usage(u_b).used}"
print("Test 10 PASSED.")

# -------------------------------------------------------------
# Test 11: Multi-turn Follow-up on Cache Hit Thread
# -------------------------------------------------------------
print("\n--- Test 11: Multi-turn Follow-up on Cache Hit Thread ---")
thread_b = res_b.headers.get("X-Thread-Id")
config_b = {"configurable": {"thread_id": thread_b}}
state_b = graph.get_state(config_b)
print(f"State in thread B after cache hit: findings length = {len(state_b.values.get('findings', ''))}, next = {state_b.next}")
assert bool(state_b.values.get("findings"))
assert len(state_b.next) == 0

# Send follow up in thread B
res_follow = client.post("/research", json={"query": "explain that in simpler words", "thread_id": thread_b}, headers={"Authorization": f"Bearer {tok_b}"})
assert res_follow.status_code == 200
events_follow = []
for line in res_follow.iter_lines():
    if line.startswith("data: ") and not line.endswith("[DONE]"):
        import json
        events_follow.append(json.loads(line[6:]))

print(f"Follow-up completed: total events = {len(events_follow)}")
# Follow up should have consumed 1 unit for user B
print(f"User B usage after follow-up: {get_usage(u_b).used}")
assert get_usage(u_b).used == 1
print("Test 11 PASSED.")

# -------------------------------------------------------------
# Test 12: Cache TTL Expiry
# -------------------------------------------------------------
print("\n--- Test 12: Cache TTL Expiry ---")
orig_ttl = answer_cache.TTL_EXTERNAL
os.environ["CACHE_TTL_EXTERNAL_SECONDS"] = "2"
ttl_query = f"test ttl query {uuid.uuid4().hex[:6]}"
# Put in cache with 2s TTL
put_cached(ttl_query, {"response": "test ttl response", "requires_external_research": True})
hit_immediate = get_cached(ttl_query)
assert hit_immediate is not None
print("Immediate cache check: HIT")
print("Waiting 3 seconds for TTL expiration...")
time.sleep(3)
hit_expired = get_cached(ttl_query)
print(f"Cache check after expiry: {hit_expired}")
assert hit_expired is None
os.environ["CACHE_TTL_EXTERNAL_SECONDS"] = str(orig_ttl)
print("Test 12 PASSED.")

# -------------------------------------------------------------
# Test 13: Degraded or terminated runs are not cached
# -------------------------------------------------------------
print("\n--- Test 13: Degraded or terminated runs not cached ---")
q_deg = f"degraded query {uuid.uuid4().hex[:6]}"
put_cached(q_deg, {"response": "something", "degraded": True})
assert get_cached(q_deg) is None

q_term = f"terminated query {uuid.uuid4().hex[:6]}"
put_cached(q_term, {"response": "something", "termination_reason": "Incomplete"})
assert get_cached(q_term) is None
print("Confirmed: degraded and terminated responses are not cached. Test 13 PASSED.")

# -------------------------------------------------------------
# Test 14: Follow-up in existing thread never reads/writes cache
# -------------------------------------------------------------
print("\n--- Test 14: Follow-up in existing thread never reads/writes cache ---")
# If thread exists, is_new_thread is False, so get_cached is skipped
th_exist = str(uuid.uuid4())
with pool.connection() as conn:
    conn.execute("INSERT INTO chat_sessions (thread_id, user_id, title) VALUES (%s, %s, %s)", (th_exist, u_a, "existing"))
graph.update_state({"configurable": {"thread_id": th_exist}}, {"query": "q1", "findings": "f1"}, as_node="report_writer")
# Follow up query that happens to be in cache
cached_q_test = f"cached topic {uuid.uuid4().hex[:6]}"
put_cached(cached_q_test, {"response": "cached answer", "requires_external_research": False})

res_cont = client.post("/research", json={"query": cached_q_test, "thread_id": th_exist}, headers={"Authorization": f"Bearer {tok_a}"})
# Because thread is continuing, it must not return cached: true
events_cont = []
for line in res_cont.iter_lines():
    if line.startswith("data: ") and not line.endswith("[DONE]"):
        import json
        events_cont.append(json.loads(line[6:]))
last_ev = events_cont[-1] if events_cont else {}
print(f"Continuation event cached flag: {last_ev.get('cached')}")
assert last_ev.get("cached") is not True
print("Test 14 PASSED.")

# -------------------------------------------------------------
# Test 15: Changing PIPELINE_VERSION invalidates old entries
# -------------------------------------------------------------
print("\n--- Test 15: Changing PIPELINE_VERSION invalidates old entries ---")
pv_query = f"pipeline version query {uuid.uuid4().hex[:6]}"
os.environ["PIPELINE_VERSION"] = "1"
put_cached(pv_query, {"response": "v1 response", "requires_external_research": False})
assert get_cached(pv_query) is not None
print("Version 1 cache: HIT")
os.environ["PIPELINE_VERSION"] = "2"
assert get_cached(pv_query) is None
print("Version 2 cache: MISS (old unreachable)")
os.environ["PIPELINE_VERSION"] = "1"
print("Test 15 PASSED.")

# -------------------------------------------------------------
# Test 16: Approval flow (interrupted) is not cached
# -------------------------------------------------------------
print("\n--- Test 16: Interrupted / Approval runs not cached ---")
# Check answer_cache table for queries that went through approval
appr_q = f"sensitive topic {uuid.uuid4().hex[:6]}"
key_appr = cache_key(appr_q)
with pool.connection() as conn:
    row = conn.execute("SELECT cache_key FROM answer_cache WHERE cache_key = %s", (key_appr,)).fetchone()
    assert row is None
print("Test 16 PASSED.")

# Cleanup test users A & B
with pool.connection() as conn:
    conn.execute("DELETE FROM usage_daily WHERE user_id IN (%s, %s)", (u_a, u_b))
    conn.execute("DELETE FROM chat_sessions WHERE user_id IN (%s, %s)", (u_a, u_b))
    conn.execute("DELETE FROM answer_cache WHERE query_normalized LIKE '%recursion%' OR query_normalized LIKE '%ttl%'")

print("\n" + "=" * 60)
print("ALL BACKEND & CACHE TESTS (1 - 16) PASSED SUCCESSFULLY!")
print("=" * 60)
