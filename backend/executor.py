# File for compiling and invoking the graph

from langgraph.graph import StateGraph, START, END
from agents.researcher import researcher_agent
from agents.supervisor import supervisor_agent
from agents.source_critic import source_critic_agent
from agents.evidence_extractor import evidence_extractor_agent
from agents.conflict_detector import conflicts_analysis_agent
from agents.report_writer import report_writer_agent
from agents.agents_state import AgentsState
from langgraph.checkpoint.memory import MemorySaver
from utils.select_route import select_route
import uuid

def graph_executor(query: str):
    graph_builder = StateGraph(AgentsState)

    memory = MemorySaver()

    graph_builder.add_node('researcher', researcher_agent)
    graph_builder.add_node('supervisor', supervisor_agent)
    graph_builder.add_node('source_critic', source_critic_agent)
    graph_builder.add_node('evidence_extractor', evidence_extractor_agent)
    graph_builder.add_node('conflicts_analyst', conflicts_analysis_agent)
    graph_builder.add_node('report_writer', report_writer_agent)

    graph_builder.add_edge(START, 'researcher')
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
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial_state = {
        "query": query,
        "original_query": query,
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
    response = result['findings']

    raw_search_results = result['raw_search_results']
    # print(f"Raw Search Results: {raw_search_results}\n")

    search_results = result['search_results']
    # print(f"Search Results: {search_results}\n")

    evidence_extracted = result['evidence_extracted']
    # print(f"Extracted Evidence: {evidence_extracted}\n")

    conflicts_analysis = result['conflicts_analysis']
    # print(f"Conflicts Analysis: {conflicts_analysis}\n")

    degraded = result['degraded']
    # print(f"Degraded: {degraded}\n")

    retry_history = result['retry_history']
    print(f"Retry History: {retry_history}\n")

    messages = result['messages']
    print(f"Messages: {messages}")

    return {
        "response": response,
        "search_results": search_results,
        "raw_search_results": raw_search_results,
        "evidence_extracted": evidence_extracted,
        "conflicts_analysis": conflicts_analysis,
        "degraded": degraded,
        "retry_history": retry_history
    }

if __name__=="__main__":

    output = graph_executor("What's the current state of nuclear reactor construction, how are governments funding it, and what safety concerns remain unresolved?")

    print(f"Response: {output['response']}\n\n, Degraded: {output['degraded']}\n\n")


# , Raw Search Results: {output['raw_search_results']}\n\n, Search Results: {output['search_results']}\n\n, Evidence Extracted: {output['evidence_extracted']}\n\n, Conflicts Analysis: {output['conflicts_analysis']}\n\n, Degraded: {output['degraded']}\n\n, Retry History: {output['retry_history']}