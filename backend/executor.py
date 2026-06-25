# File for compiling and invoking the graph

from langgraph.graph import StateGraph, START, END
from agents.researcher import researcher_agent
from agents.synthesizer import synthesizer_agent
from agents.agents_state import AgentsState
from langgraph.checkpoint.memory import MemorySaver
from agents.supervisor import supervisor_agent
from agents.select_route import select_route

def graph_executor(query: str):
    graph_builder = StateGraph(AgentsState)

    memory = MemorySaver()

    graph_builder.add_node('researcher', researcher_agent)
    graph_builder.add_node('supervisor', supervisor_agent)
    graph_builder.add_node('synthesizer', synthesizer_agent)

    graph_builder.add_edge(START, 'researcher')
    graph_builder.add_edge('researcher', 'supervisor')
    graph_builder.add_conditional_edges(
        "supervisor",
        select_route,
        {
            "researcher": "researcher",
            "synthesizer": "synthesizer"
        }
    )

    graph = graph_builder.compile(checkpointer=memory)
    config = {"configurable": {"thread_id": 1}}

    initial_state = {
        "query": query,
        "original_query": query,
        "retry_history": [],
        "findings": "",
        "search_results": [],
        "messages": [],
        "next_agent": "",
        "degraded": False,
        "route": ""
    }
    result = graph.invoke(initial_state, config=config)
    response = result['findings']
    search_results = result['search_results']
    degraded = result['degraded']
    retry_history = result['retry_history']

    return {
        "response": response,
        "search_results": search_results,
        "degraded": degraded,
        "retry_history": retry_history
    }

if __name__=="__main__":
    output = graph_executor("Compare the Series B and Series C funding trends for enterprise AI software startups over the last 12 months. Include average round sizes, leading venture capital firms, and notable market exits.")
    print(f"Response: {output['response']}\n\n, Search Results: {output['search_results']}\n\n, Degraded: {output['degraded']}\n\n, Retry History: {output['retry_history']}")
