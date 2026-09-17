import uuid
from dotenv import load_dotenv
from typing import Generator, Any
import traceback

from config.database_config import checkpointer

from langgraph.graph import StateGraph, START, END

from agents.agents_state import AgentsState
from agents.query_classifier import query_classifier_agent
from agents.direct_knowledge_agent import direct_knowledge_agent
from agents.human_approval import human_approval_agent
from agents.researcher import researcher_agent
from agents.supervisor import supervisor_agent
from agents.source_critic import source_critic_agent
from agents.evidence_extractor import evidence_extractor_agent
from agents.conflict_detector import conflicts_analysis_agent
from agents.report_writer import report_writer_agent

from utils.select_route import select_route
from utils.make_serializable import make_serializable

from resume_graph import resume_graph

load_dotenv()


def build_graph():
    graph_builder = StateGraph(AgentsState)

    graph_builder.add_node("query_classifier", query_classifier_agent)
    graph_builder.add_node("human_approval", human_approval_agent)
    graph_builder.add_node("direct_knowledge_agent", direct_knowledge_agent)
    graph_builder.add_node("researcher", researcher_agent)
    graph_builder.add_node("supervisor", supervisor_agent)
    graph_builder.add_node("source_critic", source_critic_agent)
    graph_builder.add_node("evidence_extractor", evidence_extractor_agent)
    graph_builder.add_node("conflicts_analyst", conflicts_analysis_agent)
    graph_builder.add_node("report_writer", report_writer_agent)

    graph_builder.add_edge(START, "query_classifier")
    graph_builder.add_conditional_edges(
        "query_classifier",
        select_route,
        {
            "researcher": "researcher",
            "human_approval": "human_approval",
            "direct_knowledge_agent": "direct_knowledge_agent",
            "end": END,
        },
    )
    graph_builder.add_conditional_edges(
        "direct_knowledge_agent",
        select_route,
        {
            "report_writer": "report_writer",
            "researcher": "researcher",
        },
    )
    graph_builder.add_conditional_edges(
        "human_approval",
        select_route,
        {
            "researcher": "researcher",
            "query_classifier": "query_classifier",
            "end": END,
        },
    )
    graph_builder.add_edge("researcher", "supervisor")
    graph_builder.add_conditional_edges(
        "supervisor",
        select_route,
        {
            "researcher": "researcher",
            "source_critic": "source_critic",
        },
    )
    graph_builder.add_edge("source_critic", "evidence_extractor")
    graph_builder.add_conditional_edges(
        "evidence_extractor",
        select_route,
        {
            "conflicts_analyst": "conflicts_analyst",
            "report_writer": "report_writer",
        },
    )
    graph_builder.add_edge("conflicts_analyst", "report_writer")
    graph_builder.add_edge("report_writer", END)

    graph = graph_builder.compile(checkpointer=checkpointer)
    return graph


graph = build_graph()


def _build_initial_state(query: str) -> dict:
    """Full state for a brand-new thread."""
    return {
        "query": query,
        "original_query": query,
        "is_valid": True,
        "requires_approval": False,
        "approval_status": "",
        "approval_history": [],
        "termination_reason": "",
        "classifier_reason": "",
        "requires_external_research": True,
        "knowledge_source": "",
        "knowledge_content": "",
        "retry_history": [],
        "findings": "",
        "search_results": [],
        "raw_search_results": [],
        "evidence_extracted": [],
        "extraction_failed": False,
        "conflicts_analysis": [],
        "messages": [],
        "next_agent": "",
        "degraded": False,
        "route": "",
    }


def graph_executor_stream(
    query: str, thread_id: str
) -> Generator[dict[str, Any], None, None]:
    config = {"configurable": {"thread_id": thread_id}}

    try:
        existing = graph.get_state(config)
        is_continuation = bool(existing.values)

        if is_continuation:
            input_state = {
                "query": query,
                "messages": [{"role": "user", "content": query}],
            }
        else:
            input_state = _build_initial_state(query)

        for event in graph.stream(
            input_state,
            config=config,
            stream_mode="updates",
        ):
            yield {
                "type": "node_update",
                "thread_id": thread_id,
                "data": make_serializable(event),          # ← FIXED
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
        print("STREAM ERROR:", tb)
        yield {
            "type": "error",
            "status": "error",
            "thread_id": thread_id,
            "error": str(e),
            "detail": tb,
        }


def graph_executor(query: str, thread_id: str):
    """Synchronous wrapper – useful for the __main__ block and quick tests."""
    final = None
    for event in graph_executor_stream(query, thread_id):
        if event["type"] in ("completed", "interrupted"):
            final = event
    return final


if __name__ == "__main__":
    thread_id = str(uuid.uuid4())
    print("Thread ID:", thread_id)

    result = None
    for event in graph_executor_stream("what is recursion in programming?", thread_id):
        print("EVENT:", event["type"])
        if event["type"] in ("completed", "interrupted"):
            result = event

    while result and result["status"] == "interrupted":
        print("\nExecution stopped for human approval")
        print("Interrupt:", result.get("interrupt"))

        while True:
            choice = input(
                "\nChoose (approve / reject / edit): "
            ).strip().lower()
            if choice in {"approve", "reject", "edit"}:
                break
            print("Invalid choice")

        edited_query = None
        if choice == "edit":
            edited_query = input("Enter new query: ").strip()

        result = resume_graph(
            thread_id=result["thread_id"],
            action=choice,
            edited_query=edited_query,
        )

    if result:
        if result.get("termination_reason"):
            print("Workflow Terminated.")
            print("Reason:", result["termination_reason"])
        else:
            print("Workflow completed successfully.")
            print(f"Response: {result.get('response', '')[:300]}...")
            print("Knowledge Source:", result.get("knowledge_source"))
            print("Requires research:", result.get("requires_external_research"))