from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentsState(TypedDict):
  messages: Annotated[list, add_messages]
  search_results: list[dict] # Raw Tavily Results
  findings: str
  query: str
  next_agent: str
