# File for compiling and invoking the graph

import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from agents.agents_state import AgentsState
from agents.query_classifier import query_classifier_agent
from agents.human_approval import human_approval_agent
from agents.researcher import researcher_agent
from agents.supervisor import supervisor_agent
from agents.source_critic import source_critic_agent
from agents.evidence_extractor import evidence_extractor_agent
from agents.conflict_detector import conflicts_analysis_agent
from agents.report_writer import report_writer_agent

from utils.select_route import select_route

def build_graph():
    graph_builder = StateGraph(AgentsState)

    memory = MemorySaver()

    graph_builder.add_node("query_classifier", query_classifier_agent)
    graph_builder.add_node("human_approval", human_approval_agent)
    graph_builder.add_node('researcher', researcher_agent)
    graph_builder.add_node('supervisor', supervisor_agent)
    graph_builder.add_node('source_critic', source_critic_agent)
    graph_builder.add_node('evidence_extractor', evidence_extractor_agent)
    graph_builder.add_node('conflicts_analyst', conflicts_analysis_agent)
    graph_builder.add_node('report_writer', report_writer_agent)

    graph_builder.add_edge(START, 'query_classifier')
    graph_builder.add_conditional_edges(
        "query_classifier",
        select_route,
        {
            "researcher": "researcher",
            "human_approval": "human_approval",
            "end": END
        }
    )
    graph_builder.add_conditional_edges(
        "human_approval",
        select_route,
        {
            "researcher": "researcher",
            "query_classifier": "query_classifier",
            "end": END
        }
    )
    graph_builder.add_edge('researcher', 'supervisor')
    graph_builder.add_conditional_edges(
        "supervisor",
        select_route,
        {
            "researcher": "researcher",
            "source_critic": "source_critic"
        }
    )
    graph_builder.add_edge('source_critic', 'evidence_extractor')
    graph_builder.add_edge('evidence_extractor', 'conflicts_analyst')
    graph_builder.add_edge('conflicts_analyst', 'report_writer')
    graph_builder.add_edge('report_writer', END)

    graph = graph_builder.compile(checkpointer=memory)

    return graph


graph = build_graph()

def graph_executor(query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "query": query,
        "original_query": query,
        "is_valid": True,
        "requires_approval": False,
        "approval_status": "",
        "approval_history": [],
        "termination_reason": "",
        "classifier_reason": "",
        "retry_history": [],
        "findings": "",
        "search_results": [],
        "raw_search_results": [],
        "evidence_extracted": [],
        "conflicts_analysis": [],
        "messages": [],
        "next_agent": "",
        "degraded": False,
        "route": ""
    }
    result = graph.invoke(initial_state, config=config)

    if "__interrupt__" in result:
        return {
            "status": "interrupted",
            "interrupt": result['__interrupt__'][0].value,
            "thread_id": thread_id
        }
    
    return {
        "status": "completed",
        "response": result["findings"],
        "termination_reason": result.get("termination_reason", ""),
        "messages": result["messages"],
        "search_results": result["search_results"],
        "raw_search_results": result["raw_search_results"],
        "evidence_extracted": result["evidence_extracted"],
        "conflicts_analysis": result["conflicts_analysis"],
        "degraded": result["degraded"],
        "retry_history": result["retry_history"],
    }

def resume_graph(
        thread_id: str,
        action: str,
        edited_query: str | None = None
):
    
    config = {"configurable": {
        "thread_id": thread_id
    }}
    
    resume_payload = {
        "action": action
    }

    if action == "edit":
        resume_payload["edited_query"] = edited_query

    result = graph.invoke(
        Command(resume=resume_payload),
        config=config
    )


    if "__interrupt__" in result:
        return {
            "status": "interrupted",
            "interrupt": result['__interrupt__'][0].value,
            "thread_id": thread_id
        }
    
    return {
        "status": "completed",
        "response": result["findings"],
        "messages": result["messages"],
        "termination_reason": result.get("termination_reason", ""),
        "search_results": result["search_results"],
        "raw_search_results": result["raw_search_results"],
        "evidence_extracted": result["evidence_extracted"],
        "conflicts_analysis": result["conflicts_analysis"],
        "degraded": result["degraded"],
        "retry_history": result["retry_history"],
    }

if __name__=="__main__":

    thread_id = str(uuid.uuid4())

    output = graph_executor("Should I sue my employer?", thread_id)

    result = output
    while result['status'] == "interrupted":
        print("Execution stopped because of human approval")

        interrupt = result['interrupt']
        print("Interrupt:", interrupt)
    
        while True:
            choice = input(
                "\n Choose from one of the following options (approve, reject, edit): " 
            ).strip().lower()

            if choice in {"approve", "reject", "edit"}:
                break

            print("Invalid Choice")

        edited_query = None
        if choice == "edit":
            edited_query = input("Enter new query: ").strip()
        
        result = resume_graph(
            thread_id=result['thread_id'],
            action=choice,
            edited_query=edited_query
        )


    if result["termination_reason"]:
        print("Workflow Terminated.")
        print("Reason:", result["termination_reason"])
    else:
        print("Workflow completed successfully.")
        print(f"Response: {result['response']}")
    print(f"Agent Messages: {result['messages']}")
