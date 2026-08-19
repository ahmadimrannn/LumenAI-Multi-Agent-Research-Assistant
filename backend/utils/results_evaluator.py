from config.settings import MIN_AVG_SCORE, MIN_CONTENT_COUNT, MIN_RESULTS_COUNT
from agents.agents_state import AgentsState
from event_logger import log_event

def evaluate_results(state: AgentsState) -> tuple[bool, str, dict]: # is_thin_content => bool, reason => str, failed_metric => dict
  """Returns (is_thin_content, reason, failed metric) from the search results"""

  results = state.get('search_results', [])

  if len(results) < MIN_RESULTS_COUNT:
    return True, "low_result_count", {"result_count": len(results), "threshold": MIN_RESULTS_COUNT}
  
  avg_score = sum(r['score'] for r in results) / len(results)
  scores = [r['score'] for r in results]

  difference = MIN_AVG_SCORE - avg_score
  if difference > 0 and difference <= 0.05:
    return False, "borderline_pass", {"avg_score": avg_score, "threshold": MIN_AVG_SCORE, "margin": difference}
  
  if avg_score < MIN_AVG_SCORE:
    return True, "low_relevance_score", {"avg_score": avg_score, "threshold": MIN_AVG_SCORE}
  
  if avg_score - min(scores) > 0.3:  # your own number to pick, this is a guess same as your 0.05 tolerance was
    log_event(
      service="lumen", event_type="averaging_blend_risk", severity="warning",
      node_or_route="evaluate_results",
      message=f"Passed avg_score cleanly but individual scores show high spread (min={min(scores):.3f}, avg={avg_score:.3f})",
      context={"scores": scores, "avg_score": avg_score, "threshold": MIN_AVG_SCORE},
    )
  
  
  avg_len_content = sum(len(r["content"]) for r in results) / len(results)
  if avg_len_content < MIN_CONTENT_COUNT:
    return True, "thin_content", {"content_count": avg_len_content, "threshold": MIN_CONTENT_COUNT}
  
  return False, "", {}
  
