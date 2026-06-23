from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from .agents_state import AgentsState
from langchain_community.tools.tavily_search import TavilySearchResults 

load_dotenv()

def researcher_agent(state: AgentsState):
  """Gets raw tavily search results"""

  query = state['query']
  tavily = TavilySearchResults(max_results=3)
  result = tavily.invoke(query)

  agent_message = f"Here are the search results based on the query {query}. \n\n 🔍 Search Results: {result[:2]}"

  return {
    "messages": [AIMessage(content=agent_message)],
    "search_results": result,
    "next_agent": "synthesizer"
  }