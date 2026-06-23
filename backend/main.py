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

    result = graph.invoke({"query": "what are the risks of ai agents in real life"}, config=config)
    response = result['findings']

    return response

if __name__=="__main__":
    output = main()
    print(output)
