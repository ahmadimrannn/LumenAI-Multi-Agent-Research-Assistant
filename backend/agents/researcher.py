from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from .agents_state import AgentsState
from langchain_tavily import TavilySearch
from config.llm import llm
from langchain_core.messages import HumanMessage

load_dotenv()

def invoke_tavily(query: str):
  tavily = TavilySearch(max_results=3)
  response = tavily.invoke({"query": query})
  result = response['results'] if "results" in response else "Couldn't find results due to some error"

  return result

def researcher_agent(state: AgentsState):
  """Gets raw tavily search results"""

  query = state['query']
  original_query = state['original_query']

  retry_history = state['retry_history']

  if len(retry_history) == 0:
    result = invoke_tavily(query=query)

    agent_message = f"Here are the search results based on the query {query}. \n\n 🔍 Search Results: {result[:2]}"

  else:
    correction_hint = retry_history[-1]["correction_hint"]
    previous_query = retry_history[-1]["previous_query"]

    new_query_prompt = f"""
      Original question: "{original_query}"
      Previous search query: "{previous_query}"
      It failed for this reason: {correction_hint}.

      - If correction_hint is "broaden": make the query less specific, remove narrow qualifiers, search for the general topic.
      - If correction_hint is "narrow": add specific qualifiers (timeframe, subtopic, named entities) to focus the search.
      - If correction_hint is "pivot_angle": keep the same topic but rephrase using different keywords or a different framing of intent — do not just add synonyms.

      Important: stay grounded in the original question above. If your rewrite is drifting toward
      a different subject than the original question, pull back toward the original instead of
      continuing further away.

      Return ONLY the rewritten query string, nothing else.
    """

    response = llm.invoke([HumanMessage(content=new_query_prompt)])
    refined_query = response.content
    result = invoke_tavily(query=refined_query)

    agent_message = f"Here are the search results based on the query {refined_query}. \n\n 🔍 Search Results: {result[:2]}"


  return {
    "messages": [AIMessage(content=agent_message)],
    "search_results": result,
    "query": refined_query if len(retry_history) > 0 else query # Update the query state with the latest query if the length of retry history > 0, otherwise keep the old query in the query state
  }