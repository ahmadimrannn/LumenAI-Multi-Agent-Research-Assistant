from graph_builder import graph
from typing import Any
from langgraph.types import Command
from utils.make_serializable import make_serializable

def resume_graph(
    thread_id: str,
    action: str,
    edited_query: str | None = None,
):
    config = {"configurable": {"thread_id": thread_id}}

    resume_payload: dict[str, Any] = {"action": action}
    if action == "edit":
        resume_payload["edited_query"] = edited_query

    result = graph.invoke(Command(resume=resume_payload), config=config)

    if "__interrupt__" in result:
        return {
            "status": "interrupted",
            "interrupt": make_serializable(result["__interrupt__"][0].value),
            "thread_id": thread_id,
        }

    return {
        "status": "completed",
        "response": result.get("findings", ""),
        "requires_external_research": result.get("requires_external_research"),
        "knowledge_source": result.get("knowledge_source"),
        "messages": make_serializable(result.get("messages", [])),
        "termination_reason": result.get("termination_reason", ""),
        "search_results": make_serializable(result.get("search_results", [])),
        "raw_search_results": make_serializable(result.get("raw_search_results", [])),
        "evidence_extracted": make_serializable(result.get("evidence_extracted", [])),
        "conflicts_analysis": make_serializable(result.get("conflicts_analysis", [])),
        "degraded": result.get("degraded", False),
        "retry_history": make_serializable(result.get("retry_history", [])),
    }