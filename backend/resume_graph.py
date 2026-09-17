from typing import Any, Generator
import traceback

from utils.make_serializable import make_serializable
from graph_builder import graph
from langgraph.types import Command


def resume_graph_stream(
    thread_id: str,
    action: str,
    edited_query: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Streams node-level updates while resuming an interrupted thread.
    Mirrors graph_executor_stream's event shapes and interrupt-detection
    technique (final_state.next / final_state.tasks) exactly, so the
    frontend handles both endpoints identically.
    """
    config = {"configurable": {"thread_id": thread_id}}

    resume_payload: dict[str, Any] = {"action": action}
    if action == "edit":
        resume_payload["edited_query"] = edited_query

    try:
        for event in graph.stream(
            Command(resume=resume_payload),
            config=config,
            stream_mode="updates",
        ):
            yield {
                "type": "node_update",
                "thread_id": thread_id,
                "data": make_serializable(event),
            }

        final_state = graph.get_state(config)

        if final_state.next:
            interrupt_value = None
            if final_state.tasks:
                for task in final_state.tasks:
                    if getattr(task, "interrupts", None):
                        interrupt_value = task.interrupts[0].value
                        break

            yield {
                "type": "interrupted",
                "status": "interrupted",
                "thread_id": thread_id,
                "interrupt": make_serializable(interrupt_value),
            }
        else:
            values = final_state.values or {}

            yield {
                "type": "completed",
                "status": "completed",
                "thread_id": thread_id,
                "response": values.get("findings", ""),
                "requires_external_research": values.get("requires_external_research"),
                "knowledge_source": values.get("knowledge_source"),
                "termination_reason": values.get("termination_reason", ""),
                "messages": make_serializable(values.get("messages", [])),
                "search_results": make_serializable(values.get("search_results", [])),
                "raw_search_results": make_serializable(values.get("raw_search_results", [])),
                "evidence_extracted": make_serializable(values.get("evidence_extracted", [])),
                "conflicts_analysis": make_serializable(values.get("conflicts_analysis", [])),
                "degraded": values.get("degraded", False),
                "retry_history": make_serializable(values.get("retry_history", [])),
            }

    except Exception as e:
        tb = traceback.format_exc()
        print("RESUME STREAM ERROR:", tb)
        yield {
            "type": "error",
            "status": "error",
            "thread_id": thread_id,
            "error": str(e),
            "detail": tb,
        }


def resume_graph(thread_id: str, action: str, edited_query: str | None = None):
    """Synchronous wrapper — kept for executor.py's __main__ CLI block."""
    final = None
    for event in resume_graph_stream(thread_id, action, edited_query):
        if event["type"] in ("completed", "interrupted", "error"):
            final = event
    return final