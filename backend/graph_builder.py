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