from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
import json
import re


def evidence_extractor_agent(state: AgentsState):
  """Extracts structured evidence from the search results."""

  original_query = state["original_query"]
  search_results = state["search_results"]

  evidence_extractor_prompt = f"""
You are an Evidence Extraction Agent.

Your only responsibility is to transform search results into structured evidence.

The Report Writer will NEVER see the original search results. Every relevant detail omitted here is permanently lost.

Goal: LOSSLESS EVIDENCE EXTRACTION.

ORIGINAL USER QUERY
{original_query}

SEARCH RESULTS
{search_results}

RULES

- Extract evidence only.
- Never summarize, compare sources, detect conflicts, explain, conclude or infer.
- Treat every source independently.
- Never merge information from different sources.
- Preserve wording whenever practical.
- Never normalize numbers, dates or financial figures.
- Prefer extracting too much rather than too little.
- If one paragraph contains multiple independent facts, extract every one.
- If two sources disagree, preserve both exactly.
- If information is unavailable, return null.

WHAT TO EXTRACT

For every source extract every piece of evidence relevant to answering the user's query, including:

- source metadata
- entities
- factual statements
- statistics
- financial metrics
- events
- claims
- quotations
- methodology
- assumptions
- limitations
- risks

Every independent piece of evidence must become its own evidence object.

Each evidence object should preserve:

- the main statement
- supporting context
- related entities
- dates
- numbers
- surrounding details necessary for interpretation

Never compress several independent facts into one evidence object.

SELF CHECK

Before returning verify:

✓ Every relevant paragraph has been processed.
✓ Every statistic has been extracted.
✓ Every factual statement has been extracted.
✓ Every event has been extracted.
✓ Every important supporting detail has been preserved.
✓ No evidence was discarded because it seemed less important.

OUTPUT

Return ONLY valid JSON.

[
  {{
    "source_index": 1,
    "source_url": "",
    "title": "",
    "publication_date": "",
    "organization": "",

    "entities": {{
      "companies": [],
      "people": [],
      "products": [],
      "technologies": [],
      "countries": []
    }},

    "evidence": [
      {{
        "type": "fact | statistic | event | claim | quote | limitation | methodology | risk",

        "subject": "",

        "statement": "",

        "supporting_details": [
          ""
        ],

        "numbers": [
          {{
            "metric": "",
            "value": "",
            "unit": "",
            "date": "",
            "context": ""
          }}
        ],

        "related_entities": [],

        "source_sentence": ""
      }}
    ]
  }}
]

Return ONLY JSON.
No markdown.
No explanations.
No introductory text.
"""

  response = llm.invoke([HumanMessage(content=evidence_extractor_prompt)])
  raw_content = response.content.strip()

  # Strip markdown code fences if the model added them anyway
  raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.MULTILINE)

  try:
      extracted_evidence = json.loads(raw_content)
      evidence_count = len(extracted_evidence) if isinstance(extracted_evidence, list) else 0
      parse_failed = False
  except json.JSONDecodeError:
      extracted_evidence = raw_content
      evidence_count = 0
      parse_failed = True

  agent_message = f"""
    🔍 Evidence Extractor completed {"with PARSE FAILURE — raw text passed forward" if parse_failed else "successfully"}.

    Original Sources: {len(search_results)}
    Evidence Objects Extracted: {evidence_count}
    Next Agent → Conflict Detector
  """

  return {
    "messages": [AIMessage(content=agent_message)],
    "evidence_extracted": extracted_evidence,
    "next_agent": "conflict_detector",
  }