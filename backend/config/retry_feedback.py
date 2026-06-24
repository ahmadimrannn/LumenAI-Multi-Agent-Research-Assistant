from typing import TypedDict

class RetryFeedback(TypedDict):
  attempt: int
  reason: str
  failed_metric: dict
  previous_query: str
  correction_hint: str