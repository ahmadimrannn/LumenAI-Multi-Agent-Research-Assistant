from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
import json
import re

def source_critic_agent(state: AgentsState):
  """Judges raw tavily search results for substantive content vs. spam/low-value sources BEFORE evidence_extraction. Filters search_results down to filtered_search_results."""

  original_query = state.get('original_query', "")
  search_results = state['search_results']

  source_critic_prompt = f"""
    You are a Source Quality Critic.

    Your ONLY job is to judge whether each source below is substantive enough to be
    worth extracting evidence from for the user's query. You are NOT extracting facts.
    You are NOT summarizing. You are making a keep/discard judgment per source.

    ORIGINAL USER QUERY
    {original_query}

    SOURCES
    {search_results}

    WHAT MAKES A SOURCE LOW QUALITY (discard candidates)
    - Content is mostly navigation, ads, listicle filler, or boilerplate with little
      substantive information relevant to the query.
    - Content is a press release or marketing copy about a company describing itself,
      with no independent reporting or data.
    - Content is generic/templated and could have been written without any research
      (e.g. a forum thread, a SEO-farmed "top 10" page with no real data).
    - Content's relevance score is high but the actual text has almost no concrete facts,
      numbers, or claims related to the specific query — score and substance disagree.
    - Content is severely outdated relative to what the query is asking about, AND
      no other context suggests historical data was intentionally requested.

    WHAT DOES NOT MAKE A SOURCE LOW QUALITY (do not discard for these reasons alone)
    - The source is short but contains a specific, relevant, well-attributed fact.
    - The source disagrees with another source. Disagreement is not low quality —
      that is a job for the conflict detector downstream, not you.
    - The source is old but explicitly historical/foundational context relevant to the query.
    - The source's relevance score from the search engine is mediocre but the content
      is substantive on inspection.

    RULES
    - Judge content substance directly. Do not defer to the source's search relevance score.
    - When in doubt, KEEP the source. False negatives (discarding a usable source) are worse
      than false positives (keeping a slightly weak one) — downstream agents can still
      identify a weak source's limits, but a wrongly discarded source is gone forever.
    - Discard only sources you are confident add no usable signal.
    - Every source must receive a verdict. Do not skip any.

    OUTPUT
    Return ONLY valid JSON, no markdown, no explanation, in this exact schema:

    [
      {{
        "source_index": 0,
        "url": "",
        "keep": true,
        "reason": "one concise sentence explaining the keep/discard decision"
      }}
    ]
  """

  response = llm.invoke([HumanMessage(content=source_critic_prompt)])
  raw_content = response.content[0]['text'].strip()
  raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.MULTILINE)

  try:
    verdicts = json.loads(raw_content)
    parse_failed = not isinstance(verdicts, list)
  except:
    verdicts = []
    parse_failed = True

  # Fail-open: if the critic itself breaks, don't silently lose all sources —
  # that would be a worse failure than skipping critique entirely.
  if parse_failed or len(verdicts) == 0:
    filtered_search_results = search_results
    kept_count = len(search_results)
    discarded_count = 0
    critic_failed = True
  else:
    verdict_by_index = {v.get("source_index"): v for v in verdicts if isinstance(v, dict)}
    filtered_search_results = []
    discarded = [] 

    for i, source in enumerate(search_results):
      verdict = verdict_by_index.get(i)
      if verdict is None:
          # No verdict returned for this index — fail open on THIS source, not the whole batch
          filtered_search_results.append(source)
          continue
      if verdict.get("keep", True):
          filtered_search_results.append(source)
      else:
          discarded.append({"url": source.get("url", ""), "reason": verdict.get("reason", "")})

      kept_count = len(filtered_search_results)
      discarded_count = len(discarded)
      critic_failed = False
  
  agent_message = f"""
    🧪 Source Critic completed {"with PARSE FAILURE — all sources passed through unfiltered" if critic_failed else "successfully"}.

    Sources In: {len(search_results)}
    Sources Kept: {kept_count}
    Sources Discarded: {discarded_count}
    Next Agent → Evidence Extractor
    """
  
  print("Source Critic Done ✅")

  
  return {
     "messages": [AIMessage(content=agent_message)],
     "raw_search_results": search_results,
     "search_results": filtered_search_results,
     "next_agent": "evidence_extractor"
  }