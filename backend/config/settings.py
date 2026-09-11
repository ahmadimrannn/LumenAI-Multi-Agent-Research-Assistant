GROQ_LLM_MODEL_NAME="meta-llama/llama-4-scout-17b-16e-instruct"
GEMINI_LLM_MODEL_NAME="gemini-3.1-flash-lite"
MIN_RESULTS_COUNT=3
MAX_RETRIES=2
MIN_CONTENT_COUNT=200
MIN_AVG_SCORE=0.70
EARLY_EXIT_SCORE_THRESHOLD = 0.4
EXCLUDE_DOMAINS = [
  # content farms / low-effort SEO
  "answers.com",
  "ehow.com",
  "wikihow.com",
  "ask.com",

  # forums / crowd-sourced, not authoritative for factual queries
  "quora.com",
  "pinterest.com",

  # clickbait / listicle aggregators
  "buzzfeed.com",
  "thefactsite.com",

  # PR wires — companies talking about themselves, not journalism
  "prnewswire.com",
  "businesswire.com",
  "globenewswire.com",
  "einpresswire.com",

  # link-farm / content-mill domains common in Tavily noise
  "scoop.it",
  "issuu.com",
  "slideshare.net",
]

AUTO_TRIGGER_SEVERITIES = {"error", "critical"}   # severities that will automatically trigger the sentry loop graph to run the investigation
COOLDOWN_MINUTES = 20 # no repeat trigger for the same error or log in the 20 minutes window
SENTRYLOOP_INVOKE_URL = "https://sentryloop-backend.vercel.app/api/investigate"