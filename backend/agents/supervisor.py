from agents.agents_state import AgentsState
from config.retry_feedback import RetryFeedback
from utils.results_evaluator import evaluate_results
from config.settings import MAX_RETRIES, EARLY_EXIT_SCORE_THRESHOLD

def supervisor_agent(state: AgentsState):
  """Assigns the task to different agents / nodes"""

  is_thin, reason, failed_metric = evaluate_results(state)
  if not is_thin:
    if reason == "borderline_pass":
      print(f"[supervisor] Passed on tolerance: avg_score={failed_metric.get('avg_score')}, margin={failed_metric.get('margin')}")
    return {
      "degraded": False,
      "route": "synthesizer",
    }

  attempt = len(state.get("retry_history", []))
  
  correction_map = {
    "low_relevance_score": "pivot_angle",
    "low_result_count": "broaden",
    "thin_content": "seek_context",
  }

  feedback: RetryFeedback = {
    "attempt": attempt + 1,
    "reason": reason,
    "failed_metric": failed_metric,
    "previous_query": state['query'],
    "correction_hint": correction_map[reason]
  }

  # Early exit: after the second invoke, if relevance is still under threshold, stop retrying
  if attempt == 1 and reason == "low_relevance_score" and failed_metric.get("avg_score", 1.0) < EARLY_EXIT_SCORE_THRESHOLD:
    return {
      "degraded": True,
      "retry_history": state.get("retry_history", []) + [feedback],
      "route": "synthesizer",
    }

  
  if attempt >= MAX_RETRIES:
    return {
      "degraded": True,
      "retry_history": state.get("retry_history", []) + [feedback],
      "route": "synthesizer",
    }

  return {
    "retry_history": state.get("retry_history", []) + [feedback],
    "route": "researcher"
  }

