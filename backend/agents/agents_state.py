from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from config.retry_feedback import RetryFeedback


class AgentsState(TypedDict):
  messages: Annotated[list, add_messages]
  search_results: list[dict] # Raw Tavily Results
  findings: str
  original_query: str
  query: str
  evidence_extracted: list[dict]
  conflicts_analysis: list[dict]
  next_agent: str
  retry_history: list[RetryFeedback]
  degraded: bool
  route: str
