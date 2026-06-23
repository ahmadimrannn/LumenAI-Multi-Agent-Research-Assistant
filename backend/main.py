from langgraph.graph import StateGraph, START, END
from agents.researcher import researcher_agent
from agents.synthesizer import synthesizer_agent
from agents.agents_state import AgentsState
from langgraph.checkpoint.memory import MemorySaver

def main():
    graph_builder = StateGraph(AgentsState)

    memory = MemorySaver()

    graph_builder.add_node('researcher', researcher_agent)
    graph_builder.add_node('synthesizer', synthesizer_agent)

    graph_builder.add_edge(START, 'researcher')
    graph_builder.add_edge('researcher', 'synthesizer')
    graph_builder.add_edge('synthesizer', END)

    graph = graph_builder.compile(checkpointer=memory)
    config = {"configurable": {"thread_id": "test-1"}}

    result = graph.invoke({"query": "Does LangGraph's MemorySaver checkpointer persist state across server restarts, or only within a single process?"}, config=config)
    response = result['findings']
    search_results = result['search_results']

    return {
        "response": response,
        "search_results": search_results,
    }

if __name__=="__main__":
    output = main()
    print(f"Response: {output['response']}\n\n, Search Results: {output['search_results']}")
