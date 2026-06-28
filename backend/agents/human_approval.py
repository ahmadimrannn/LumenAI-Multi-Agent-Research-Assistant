from agents.agents_state import AgentsState
from langgraph.types import interrupt
from langchain_core.messages import AIMessage

def human_approval_agent(state: AgentsState):
  """
    Pause execution and wait for human approval.

    Expected resume payload:
    {
        "action": "approve" | "reject" | "edit",
        "edited_query": "..."   # only when action == "edit"
    }
  """

  query = state['query']
  classifier_reason = state['classifier_reason']

  approval = interrupt(
    {
      "type": "query_approval",
      "query": query,
      "classifier_reason": classifier_reason,
      'message': (
        "This message has been classified as potentially sensitive."
        "Choose one of the following options: approve, reject, edit"
      )
    }
  )

  action = approval.get("action")

  if action == "approve": 
    return {
      "approval_status": "approved",
      "route": "researcher",
      "messages": [AIMessage(content="Human approved the query. Next Agent -> Researcher")]
    }
  
  elif action == "edit":
    edited_query = approval.get("edited_query", query)

    return {
      "approval_status": "edited",
      "route": "query_classifier",
      "original_query": edited_query,
      "query": edited_query,
      "messages": [AIMessage(content=f"Human rejected the query. New edited query: {edited_query}.  Next Agent -> Query Classifier")]
    }
  

  return {
    "approval_status": "rejected",
    "route": "end",
    "messages": [AIMessage(content="Human rejected the query. Next Agent -> End")]
  }