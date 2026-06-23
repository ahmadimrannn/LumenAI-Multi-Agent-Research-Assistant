from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from .agents_state import AgentsState
from config.llm import llm

load_dotenv()

def synthesizer_agent(state: AgentsState):
  """Generates the report from the search_results"""

  search_results = state['search_results']
  synthesizer_prompt = f"""
    As a report synthesizer specialist, generate detailed findings based on these search_results {search_results}

    Include:
    1. Key facts and background
    2. Current trends or developments
    3. Important statistics or data points
    4. Notable examples or case studies

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