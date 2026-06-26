from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
import json
import re

def conflicts_analysis_agent(state: AgentsState):
  """Compare the extracted evidences to find conflicts between sources."""

  original_query = state['original_query']
  extracted_evidence = state['evidence_extracted']

  json_schema = """
{
  "topics": [
    {
      "topic": "",
      "summary": "",
      "evidence": [
        {
          "source_index": 1,
          "statement": "",
          "supporting_details": [],
          "statistics": [
            {
              "metric": "",
              "value": "",
              "unit": "",
              "date": "",
              "context": ""
            }
          ],
          "events": [
            {
              "date": "",
              "event": ""
            }
          ]
        }
      ]
    }
  ],

  "conflicts": [
    {
      "subject": "",
      "metric": "",
      "description": "",
      "reported_values": [
        {
          "source_index": 1,
          "value": "",
          "date": "",
          "context": ""
        }
      ],
      "possible_reason": ""
    }
  ],

  "consensus": [
    {
      "subject": "",
      "finding": "",
      "supporting_sources": [],
      "supporting_evidence": []
    }
  ],

  "complementary_information": [
    {
      "subject": "",
      "description": "",
      "source_index": "",
      "related_to": ""
    }
  ],

  "chronology": [
    {
      "date": "",
      "event": "",
      "source_index": ""
    }
  ],

  "missing_information": [
    ""
  ]
}
"""

  conflict_detector_prompt = f"""
You are a Conflict Detection Agent.

Your only responsibility is to analyze structured evidence extracted from multiple sources.

Do not summarize, write a report, rewrite evidence, remove evidence, infer new facts or decide which source is correct.

ORIGINAL USER QUERY
{original_query}

STRUCTURED EVIDENCE
{extracted_evidence}

TASK

Analyze every evidence object and classify it into one or more of the following:

- conflicts
- consistent_information
- complementary_information
- unique_information
- missing_information

RULES

- A conflict exists only when multiple sources report different values or statements about the same subject, metric or event during the same timeframe.
- Differences caused by different reporting dates, historical values or additional context are not conflicts unless they directly contradict one another.
- If multiple sources report the same information, group them under consistent_information.
- If one source adds new details that do not contradict other sources, classify them as complementary_information.
- If information appears in only one source and neither agrees nor conflicts with another source, classify it as unique_information.
- Do not discard any evidence.
- Every evidence object must appear in at least one category.
- If the user's query requires information that is absent from all extracted evidence, list it under missing_information.

SELF CHECK

Before returning verify:

✓ Every evidence object has been classified.
✓ Every genuine conflict has been preserved.
✓ No historical values were treated as conflicts solely because they differ from newer values.
✓ No complementary information was labeled as conflicting.
✓ No evidence has been omitted.

OUTPUT FORMAT

Return ONLY valid JSON.

Use the following schema exactly:

{json_schema}

Return ONLY JSON.
No markdown.
No explanations.
No additional text.
"""

  response = llm.invoke([HumanMessage(content=conflict_detector_prompt)])
  raw_content = response.content.strip()
  raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.MULTILINE)

  try:
    json.loads(raw_content)
    parse_failed = False
  except:
    parse_failed = True

  conflicts_analysis = raw_content

  evidence_source_count = (
      len(extracted_evidence) if isinstance(extracted_evidence, list) else 0
  )

  agent_message = f"""
  ⚖️ Conflict Detector completed {"with PARSE FAILURE — malformed JSON forwarded" if parse_failed else "successfully"}.

  Evidence Sources: {evidence_source_count}
  Next Agent → Report Writer
  """

  return {
    "messages": [AIMessage(content=agent_message)],
    "conflicts_analysis": conflicts_analysis,
    "next_agent": "report_writer"
  }

