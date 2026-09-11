from event_logger import log_event

log_event(
    service="lumen",
    event_type="evidence_extractor_parse_failure",
    message="LLM output failed JSON parsing after 2 retries, falling back to degraded report",
    severity="critical",
    node_or_route="evidence_extractor",
    thread_id="test-verify-002",
    context={"attempt": 2, "raw_output_length": 4021, "query": "compare vector db options for RAG"},
)
print("log event completed...")