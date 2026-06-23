from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from .agents_state import AgentsState
from config.llm import llm

load_dotenv()

def synthesizer_agent(state: AgentsState):
  """Generates the report from the search_results"""

  query = state['query']
  search_results = state['search_results']

  synthesizer_prompt = f"""
    You are a report synthesizer. Using ONLY the information present in the search results below, write findings on: {query}

    Search results:
    {search_results}

    Strict Rules (Must Follow):
    - Every claim must be grounded in the search results above. Do not add facts, statistics, or examples not present in them.
    - For each claim, note which source (by URL or source index) it came from.
    - If the search results are thin, outdated, or don't cover part of the question, say so explicitly rather than filling gaps with assumptions.
    - If sources disagree with each other, present both positions rather than picking one silently.
    - Organize into whatever sections the actual evidence supports — don't force categories (trends, statistics, case studies) that the source material doesn't contain.
    - Pay attention to dates/timeframes mentioned in the search results. If a source's content is significantly older than the query's implied timeframe, state its actual timing explicitly rather than presenting it as current.
    - If search results mix old and recent information, separate them clearly rather than blending into one timeline.
    - Use information from ALL provided search results unless a specific result is genuinely irrelevant to the query — and if you exclude one, say so explicitly and why.
    - **After your findings, include a "Sources Used" list that maps EVERY source URL provided to either: (a) which section of your findings it was used in, or (b) "Not used: [one-sentence reason]"**.
    - Before citing a source for a claim, check that the source is actually discussing the same specific subject as the claim — not just a related or adjacent topic. If a source discusses a different but related mechanism, name that distinction explicitly rather than treating it as direct evidence.

    Be concise but thorough.
  """

  synthesizer_llm_response = llm.invoke([HumanMessage(content=synthesizer_prompt)])
  findings = synthesizer_llm_response.content

  agent_message = f"Here are the findings from these search results {search_results[:1]} \n\n 🔍 Key Findings: {findings[:200]}"

  return {
    "messages": [AIMessage(content=agent_message)],
    "findings": findings,
    "next_agent": 'end'
  }