from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage

def conflicts_analysis_agent(state: AgentsState):
  """Compare the extracted evidences to find conflicts between sources."""

  original_query = state['original_query']
  extracted_evidence = state['evidence_extracted']

  json_schema = """
    {
      "conflicts": [
        {
          "subject": "",
          "metric": "",
          "sources": [
            {
              "source_index": "",
              "value": "",
              "date": "",
              "context": ""
            }
          ],
          "possible_reason": ""
        }
      ],

      "consistent_information": [
        {
          "subject": "",
          "metric": "",
          "value": "",
          "supporting_sources": []
        }
      ],

      "complementary_information": [
        {
          "subject": "",
          "description": "",
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

    Your ONLY responsibility is to compare structured evidence extracted from multiple sources.

    DO NOT summarize.
    DO NOT write a report.
    DO NOT determine which source is correct.
    DO NOT remove conflicting information.
    DO NOT rewrite evidence.
    DO NOT infer facts that are not explicitly present.

    Original User Query:
    {original_query}

    Structured Evidence:
    {extracted_evidence}

    --------------------------------------------------
    TASK
    --------------------------------------------------

    Analyze the structured evidence and identify:

    1. Conflicting information
    2. Consistent information
    3. Complementary information
    4. Missing information

    --------------------------------------------------
    CONFLICT RULES
    --------------------------------------------------

    A conflict exists when two or more sources report different values for the same subject and metric.

    Examples:

    Anthropic valuation
    Source A → $183B
    Source B → $350B

    OpenAI funding
    Source A → $62B
    Source B → $57B

    Interest Rate
    Source A → 4.25%
    Source B → 4.50%

    Do NOT attempt to decide which value is correct.

    Store every reported value.

    --------------------------------------------------
    CONSISTENCY RULES
    --------------------------------------------------

    If multiple independent sources report essentially the same information,
    mark it as CONSISTENT.

    Example

    OpenAI raised $40B in March 2025

    reported by

    Source 2
    Source 5
    Source 8

    --------------------------------------------------
    COMPLEMENTARY INFORMATION
    --------------------------------------------------

    Some sources may provide additional information without contradicting others.

    Example

    Source A
    Anthropic valuation

    Source B
    Anthropic revenue

    These are complementary.

    Do NOT label these as conflicts.

    --------------------------------------------------
    MISSING INFORMATION
    --------------------------------------------------

    If the user's query asks for information that does not appear in any extracted evidence,
    list it under missing_information.

    Example

    Query asks

    "Average Series A funding"

    No source reports it.

    Return it as missing_information.

    --------------------------------------------------
    OUTPUT FORMAT
    --------------------------------------------------

    Return ONLY valid JSON.

    Use the following schema exactly:

    {json_schema}

    Return ONLY JSON.

    No markdown.

    No explanations.

    No additional text.
  """

  response = llm.invoke([HumanMessage(content=conflict_detector_prompt)])
  conflicts_analysis = response.content

  agent_message = f"""
    ⚖️ Conflict Detector completed successfully.

    Evidence Sources: {len(extracted_evidence)}

    Conflict analysis generated successfully.

    Next Agent → Report Writer
  """

  return {
    "messages": [AIMessage(content=agent_message)],
    "conflicts_analysis": conflicts_analysis,
    "next_agent": "report_writer"
  }

