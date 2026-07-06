import json
import re
from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage


def _chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def _extract_chunk(original_query, source_chunk, start_index):
    """Run extraction on one chunk of sources, returns (evidence_list, parse_failed: bool)."""

    evidence_extractor_prompt = f"""
You are an Evidence Extraction Agent.

Your only responsibility is to transform search results into structured evidence.

The Report Writer will NEVER see the original search results. Every relevant detail omitted here is permanently lost.

Goal: LOSSLESS EVIDENCE EXTRACTION.

ORIGINAL USER QUERY
{original_query}

SEARCH RESULTS (sources indexed starting at {start_index})
{source_chunk}

RULES
- Extract evidence only. Never summarize, compare sources, detect conflicts, explain, conclude or infer.
- Treat every source independently. Never merge information from different sources.
- Preserve wording whenever practical. Never normalize numbers, dates or financial figures.
- Prefer extracting too much rather than too little.
- If one paragraph contains multiple independent facts, extract every one.
- If information is unavailable, return null.

OUTPUT
Return ONLY valid JSON, an array of source objects, exactly this schema:

[
  {{
    "source_index": {start_index},
    "source_url": "",
    "title": "",
    "publication_date": "",
    "organization": "",
    "entities": {{"companies": [], "people": [], "products": [], "technologies": [], "countries": []}},
    "evidence": [
      {{
        "type": "fact | statistic | event | claim | quote | limitation | methodology | risk",
        "subject": "",
        "statement": "",
        "supporting_details": [""],
        "numbers": [{{"metric": "", "value": "", "unit": "", "date": "", "context": ""}}],
        "related_entities": [],
        "source_sentence": ""
      }}
    ]
  }}
]

Return ONLY JSON. No markdown. No explanations.
"""

    response = llm.invoke([HumanMessage(content=evidence_extractor_prompt)])
    raw_content = response.content.strip()
    raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.MULTILINE)

    try:
      parsed = json.loads(raw_content)
      if not isinstance(parsed, list):
        return [], True
      return parsed, False
    except json.JSONDecodeError as e:
      print(f"--- CHUNK PARSE FAILURE (start_index={start_index}) ---")
      print(f"Error: {e}")
      print(f"Raw content length: {len(raw_content)} chars")
      print(f"Last 300 chars: {raw_content[-300:]}")
      print(f"First 300 chars: {raw_content[:300]}")
      print("--- END ---")
      return [], True


def evidence_extractor_agent(state: AgentsState):
    """Extracts structured evidence from search results, in chunks to stay under
    per-message token limits."""

    original_query = state.get("original_query", "")
    search_results = state.get("search_results", [])

    CHUNK_SIZE = 5
    all_evidence = []
    any_chunk_failed = False

    for i, chunk in enumerate(_chunk(search_results, CHUNK_SIZE)):
        start_index = i * CHUNK_SIZE
        chunk_evidence, chunk_failed = _extract_chunk(original_query, chunk, start_index)
        if chunk_failed:
            any_chunk_failed = True
        else:
            all_evidence.extend(chunk_evidence)

    evidence_count = len(all_evidence)

    agent_message = f"""
    🔍 Evidence Extractor completed {"with PARTIAL FAILURE — one or more chunks failed to parse" if any_chunk_failed else "successfully"}.

    Original Sources: {len(search_results)}
    Chunks Processed: {len(list(_chunk(search_results, CHUNK_SIZE)))}
    Evidence Objects Extracted: {evidence_count}
    Next Agent → Conflict Detector
    """

    print("Evidence Extractor Done ✅")

    return {
        "messages": [AIMessage(content=agent_message)],
        "evidence_extracted": all_evidence,
        "extraction_failed": any_chunk_failed,
        "next_agent": "conflict_detector",
    }