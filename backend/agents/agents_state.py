from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from config.retry_feedback import RetryFeedback

class AgentsState(TypedDict):
  original_query: str
  query: str
  is_valid: bool
  requires_approval: bool
  requires_external_research: bool
  knowledge_source: str
  knowledge_content: str
  classifier_reason: str
  approval_status: str
  approval_history: list[dict]
  termination_reason: str
  messages: Annotated[list, add_messages]
  search_results: list[dict] 
  retry_history: list[RetryFeedback]
  degraded: bool
  route: str
  raw_search_results: list[dict] # Raw Tavily Results
  evidence_extracted: list[dict]
  extraction_failed: bool
  conflicts_analysis: list[dict]
  findings: str
  next_agent: str
