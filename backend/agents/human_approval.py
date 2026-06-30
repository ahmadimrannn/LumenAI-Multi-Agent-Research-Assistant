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
  approval_history = state.get("approval_history", [])

  if len(approval_history) >= 3:
    return {
      "approval_history": approval_history,
      "route": "end",
      "termination_reason": (
            "Maximum human approval attempts exceeded. "
            "Please submit a new request."
      ),
      "messages": [
        AIMessage(
          content="Maximum approval attempts exceeded. Ending workflow."
        )
      ]
    }

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

  history = approval_history.copy()
  history.append(
    {
      "query": query,
      "action": action,
      "classifier_reason": classifier_reason
    }
  )


  if action == "approve": 
    next_route = "researcher"
    return {
      "approval_status": "approved",
      "route": next_route,
      "messages": [AIMessage(content="Human approved the query. Next Agent -> Researcher")],
      "approval_history": history
    }
  
  elif action == "edit":
    next_route = "query_classifier"
    edited_query = approval.get("edited_query", query)

    return {
      "approval_status": "edited",
      "route": next_route,
      "original_query": edited_query,
      "query": edited_query,
      "messages": [AIMessage(content=f"Human rejected the query. New edited query: {edited_query}.  Next Agent -> Query Classifier")],
      "approval_history": history
    }
  

  next_route = "end"
  return {
    "approval_status": "rejected",
    "route": next_route,
    "termination_reason": "Research request was rejected during human approval.  Please write the complete query again.",
    "messages": [AIMessage(content="Human rejected the query. Next Agent -> End")],
    "approval_history": history
  }