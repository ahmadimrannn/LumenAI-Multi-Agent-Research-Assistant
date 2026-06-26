from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
import json


def evidence_extractor_agent(state: AgentsState):
  """Extracts structured evidence from the search results."""

  original_query = state["original_query"]
  search_results = state["search_results"]

  evidence_extractor_prompt = f"""
    You are an Evidence Extraction Agent.

    Your ONLY responsibility is to transform unstructured search results into structured evidence.

    You are NOT writing the final report.

    Another agent will write the report later.

    That agent will NEVER see the original search results.

    Therefore, EVERY relevant fact you fail to extract is permanently lost.

    Your goal is LOSSLESS EVIDENCE EXTRACTION.

    --------------------------------------------------
    ORIGINAL USER QUERY
    --------------------------------------------------

    {original_query}

    --------------------------------------------------
    SEARCH RESULTS
    --------------------------------------------------

    {search_results}

    --------------------------------------------------
    RULES
    --------------------------------------------------

    DO NOT summarize.

    DO NOT compare sources.

    DO NOT detect conflicts.

    DO NOT explain anything.

    DO NOT draw conclusions.

    DO NOT infer missing information.

    DO NOT normalize numbers.

    DO NOT rewrite facts into shorter versions.

    DO NOT merge multiple facts into one.

    Treat every search result independently.

    Never merge information across sources.

    Preserve wording whenever practical.

    Err on the side of extracting TOO MUCH rather than TOO LITTLE.

    Compression is considered FAILURE.

    --------------------------------------------------
    WHAT TO EXTRACT
    --------------------------------------------------

    For EVERY search result, extract every piece of information directly relevant to answering the user's query.

    This includes (when present):

    - source_url
    - title
    - publication_date
    - organization
    - author
    - companies
    - people
    - products
    - technologies
    - countries
    - facts
    - statistics
    - financial figures
    - percentages
    - valuations
    - funding rounds
    - investments
    - acquisitions
    - partnerships
    - launches
    - regulations
    - revenue
    - ARR
    - notable events
    - timelines
    - claims
    - quotations
    - methodology
    - assumptions
    - limitations
    - risks

    If a paragraph contains:

    - five facts → extract five facts

    - three statistics → extract three statistics

    - two events → extract two events

    Do NOT compress multiple pieces of evidence into one sentence.

    If two sources disagree, preserve BOTH exactly.

    Never attempt to resolve disagreements.

    If information is missing, return null.

    --------------------------------------------------
    SELF CHECK
    --------------------------------------------------

    Before returning your answer verify:

    ✓ Every relevant statistic has been extracted.

    ✓ Every relevant date has been extracted.

    ✓ Every relevant event has been extracted.

    ✓ Every relevant entity has been extracted.

    ✓ Every relevant claim has been extracted.

    ✓ Every relevant quote has been extracted.

    ✓ No relevant paragraph has been skipped.

    If any answer is NO, continue extracting before returning.

    --------------------------------------------------
    OUTPUT FORMAT
    --------------------------------------------------

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

            "facts": [],

            "statistics": [
                {{
                    "subject": "",
                    "metric": "",
                    "value": "",
                    "unit": "",
                    "date": "",
                    "context": "",
                    "source_sentence": ""
                }}
            ],

            "events": [
                {{
                    "date": "",
                    "event": ""
                }}
            ],

            "quotes": [],

            "limitations": [],

            "supporting_details": [],

            "raw_claims": []
        }}
    ]

    Return ONLY JSON.

    No markdown.

    No explanations.

    No introductory text.
  """

  response = llm.invoke([HumanMessage(content=evidence_extractor_prompt)])

  try:
    extracted_evidence = json.loads(response.content)
  except json.JSONDecodeError:
    extracted_evidence = response.content

    evidence_count = (
      len(extracted_evidence)
      if isinstance(extracted_evidence, list)
      else 0
    )

  agent_message = f"""
    🔍 Evidence Extractor completed successfully.

    Original Sources: {len(search_results)}

    Evidence Objects Extracted: {evidence_count}

    Next Agent → Conflict Detector
  """

  return {
    "messages": [AIMessage(content=agent_message)],
    "evidence_extracted": extracted_evidence,
    "next_agent": "conflict_detector",
  }