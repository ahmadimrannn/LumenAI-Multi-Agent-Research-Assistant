from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
import json
import re

def query_classifier_agent(state: AgentsState):
  """
    Single LLM call: checks query validity and sensitivity before any
    research is performed, to avoid burning the full pipeline on malformed
    or unsafe input.
  """

  query = state['query']
  query = query.strip()

# Empty or whitespace
  if not query:
    return {
      "messages": [
          AIMessage(content="❌ Query rejected: Empty query.")
      ],
      "is_valid": False,
      "requires_approval": False,
      "classifier_reason": "The query is empty.",
      "route": "end",
      "termination_reason": "Query is incomplete or malformed. Please provide a clearer research request."
    }

# Only punctuation / symbols
  if re.fullmatch(r"[\W_]+", query):
    return {
      "messages": [
          AIMessage(content="❌ Query rejected: Only punctuation or symbols.")
      ],
      "is_valid": False,
      "requires_approval": False,
      "classifier_reason": "The query contains only punctuation or symbols.",
      "route": "end",
      "termination_reason": "Query is incomplete or malformed. Please provide a clearer research request."
    }

# Extremely short repeated characters
# e.g. aaaaa, !!!!!, ......
  if re.fullmatch(r"(.)\1{4,}", query):
    return {
      "messages": [
          AIMessage(content="❌ Query rejected: Repeated characters.")
      ],
      "is_valid": False,
      "requires_approval": False,
      "classifier_reason": "The query contains only repeated characters.",
      "route": "end",
      "termination_reason": "Query is incomplete or malformed. Please provide a clearer research request."
    }

  # Looks like random keyboard smashing
  letters = re.sub(r"[^A-Za-z]", "", query)

  if (
    len(letters) >= 8
    and " " not in query
    and not re.search(r"[aeiouAEIOU]", letters)
  ):
    return {
      "messages": [
          AIMessage(content="❌ Query rejected: Appears to be random keyboard input.")
      ],
      "is_valid": False,
      "requires_approval": False,
      "classifier_reason": "The query appears to be random keyboard input.",
      "route": "end",
      "termination_reason": "Query is incomplete or malformed. Please provide a clearer research request."
    }

  query_classifier_prompt = f"""
    You are a Query Intake Classifier for a research assistant. You do not answer
    the query. You only assess it before research begins.

    QUERY
    {query}

    ASSESS TWO THINGS:

    1. VALIDITY: Is this query complete and well-formed enough to research?
        Determine whether this input is sufficiently complete and meaningful to begin a research pipeline.
      An INVALID query includes (but is not limited to):

      • Empty input
      • Only whitespace
      • Only punctuation
      • Only emojis
      • Random keyboard smashing
      • Gibberish
      • Random characters
      • Repeated symbols
      • Truncated thoughts
      • Extremely ambiguous fragments
      • A single unrelated word
      • Inputs requiring you to guess the user's intent

      Examples of INVALID input:
      .....
      ...
      ???
      !!!!
      ,,,,,
      ------
      _____
      akljdflkaieuriueroeri
      jdkjfe9893>?>jikfdfjh>?<>
      😀😀😀😀😀
      apple
      because...
      what are
      tell me about
      something
      continue
      asdf
      lkj
      .....

      Do NOT attempt to rewrite or improve these.

      Do NOT invent a topic.

      Return is_valid=false.

      Valid examples: any complete question or research request, even if broad,
      informal, or imperfectly phrased — completeness of thought matters, not
      grammar or formality.

    2. APPROVAL REQUIREMENT: Would a well-evidenced research report answering this
      query, if taken at face value by the user, risk being relied upon as
      authoritative legal, medical, or financial advice for a real decision —
      OR could the answer be defamatory or harmful to a real, identifiable person?
      This is not about topic area (a query about GDPR fines or drug interactions
      is NOT automatically high-risk) — it's about whether a confident-sounding
      but potentially wrong answer could cause real harm if acted on directly,
      or harm a real person's reputation.

    RULES
    - Default to requires_approval=false unless there's a concrete, specific reason.
    - Broad informational queries about legal/medical/financial topics are NOT
      automatically high-risk — only flag when the answer would plausibly be
      used as a substitute for professional advice on a specific personal
      situation, or names/targets a real identifiable individual.

    CRITICAL RULE

    - Never "helpfully" complete an incomplete query.
    - Never infer what the user probably intended.
    - Never rewrite invalid input into a valid research question.
    If the user did not explicitly communicate a research intent, classify it as INVALID.

    - When uncertain whether a query is valid, classify it as INVALID.
    - Do not optimize for helpfulness.
    - Optimize for preventing wasted research calls.

    OUTPUT
    Return ONLY valid JSON, no markdown, no explanation:

    {{
      "is_valid": true,
      "requires_approval": false,
      "classifier_reason": "classifier_reason should explain exactly WHY the query is invalid or why approval is required.

      Examples:
      "The query contains only punctuation."
      "The input is random gibberish."
      "The request is incomplete."
      "The request seeks individualized legal advice."
      "The request appears defamatory toward a real person.""
    }}
  """
  
  response = llm.invoke([HumanMessage(content=query_classifier_prompt)])
  raw_content = response.content.strip()
  raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.MULTILINE)

  try:
    verdict = json.loads(raw_content)
    is_valid = bool(verdict.get('is_valid', True))
    requires_approval = bool(verdict.get("requires_approval", False))
    classifier_reason = verdict.get("classifier_reason")
    parse_failed = False
  except:
    is_valid, requires_approval, classifier_reason = True, False, ""
    parse_failed = True


  if not is_valid:
    next_step = "end"
    termination_reason = "Query is incomplete or malformed. Please provide a clearer research request."
  elif requires_approval:
    next_step = "human_approval"
    termination_reason = ""
  else:
    next_step = "researcher"
    termination_reason = ""

  agent_message = f"""
    🚦 Query Classifier completed {"with PARSE FAILURE — defaulted to proceed" if parse_failed else "successfully"}.

    Valid: {is_valid}
    Requires Approval: {requires_approval}
    Reason: {classifier_reason}
    Next → {next_step}
  """
  
  return {
    "messages": [AIMessage(content=agent_message)],
    "is_valid": is_valid,
    "termination_reason": termination_reason,
    "requires_approval": requires_approval,
    "classifier_reason": classifier_reason,
    "route": next_step
  }
  
