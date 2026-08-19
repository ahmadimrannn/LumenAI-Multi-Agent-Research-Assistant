from agents.agents_state import AgentsState
from config.retry_feedback import RetryFeedback
from utils.results_evaluator import evaluate_results
from config.settings import MAX_RETRIES, EARLY_EXIT_SCORE_THRESHOLD
from event_logger import log_event

def supervisor_agent(state: AgentsState):
  """Assigns the task to different agents / nodes"""

  is_thin, reason, failed_metric = evaluate_results(state)
  if not is_thin:
    if reason == "borderline_pass":
      log_event(
        service="lumen", event_type="borderline_pass", severity="info",
        node_or_route="supervisor",
        message=f"Passed on tolerance: avg_score={failed_metric.get('avg_score')}, margin={failed_metric.get('margin')}",
        context=failed_metric,
      )
    return {
      "degraded": False,
      "route": "source_critic",
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

  # Early exit: after the second invoke, if relevance is still under threshold, we will stop retrying
  if attempt == 1 and reason == "low_relevance_score" and failed_metric.get("avg_score", 1.0) < EARLY_EXIT_SCORE_THRESHOLD:
    log_event(
      service="lumen", event_type="supervisor_early_exit", severity="warning",
      node_or_route="supervisor",
      message="Supervisor applied early exit and routed workflow to source_critic",
      context={"reason": reason, "failed_metric": failed_metric, "attempt": attempt + 1, "route": "source_critic", "degraded": True},
    )
    return {
      "degraded": True,
      "retry_history": state.get("retry_history", []) + [feedback],
      "route": "source_critic",
    }

  if attempt >= MAX_RETRIES:
    log_event(
      service="lumen", event_type="supervisor_max_retries_exceeded", severity="warning",
      node_or_route="supervisor",
      message="Supervisor reached max retries and routed workflow to source_critic",
      context={"reason": reason, "failed_metric": failed_metric, "attempt": attempt + 1, "route": "source_critic", "degraded": True},
    )
    return {
      "degraded": True,
      "retry_history": state.get("retry_history", []) + [feedback],
      "route": "source_critic",
    }

  log_event(
    service="lumen", event_type="supervisor_retry_correction", severity="info",
    node_or_route="supervisor",
    message=f"Supervisor routed to researcher for retry with correction_hint={correction_map[reason]}",
    context=feedback,
  )

  return {
    "retry_history": state.get("retry_history", []) + [feedback],
    "route": "researcher"
  }