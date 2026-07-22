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
  query = query.strip() if query else None

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
    You are a Query Intake Classifier for a research assistant.

    You NEVER answer the user's query.

    Your job is ONLY to determine:

    1. Whether the query is valid.
    2. Whether it requires human approval.
    3. Whether it requires a full external research workflow.

    QUERY

    {query}

    ------------------------------------------------------------
    ASSESSMENT 1 — VALIDITY
    ------------------------------------------------------------

    Determine whether this input is sufficiently complete and meaningful to process.

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

    Do NOT rewrite the query.

    Do NOT infer the user's intended meaning.

    Do NOT invent missing information.

    If you are uncertain whether the query is complete, classify it as INVALID.

    ------------------------------------------------------------
    ASSESSMENT 2 — APPROVAL REQUIREMENT
    ------------------------------------------------------------

    Determine whether answering this request with a research report could reasonably
    be relied upon as authoritative legal, medical, or financial advice for a real
    decision, OR whether the request could be defamatory toward a real identifiable
    person.

    Broad educational questions do NOT require approval.

    Examples requiring approval:

    • Should I stop taking my heart medication?
    • How should I invest my retirement savings?
    • Can I sue my employer over this situation?
    • Prove John Smith committed fraud.

    Examples NOT requiring approval:

    • Explain insulin.
    • Explain copyright law.
    • Explain mortgages.
    • Explain GDPR.

    Default to requires_approval=false unless there is a concrete reason.

    ------------------------------------------------------------
    ASSESSMENT 3 — EXTERNAL RESEARCH REQUIREMENT
    ------------------------------------------------------------

    Determine whether answering this query requires gathering or verifying information
    from external sources.

    Return requires_research=true whenever ANY of the following apply:

    • Current or recent information is needed.
    • The answer depends on facts that may have changed over time.
    • Web search would improve accuracy.
    • Multiple external sources should be compared.
    • Evidence or citations are expected.
    • Company, market, product, industry, government, regulatory, or financial research is requested.
    • Academic literature review is requested.
    • Trend analysis is requested.
    • Fact verification is needed.
    • Statistics are requested.
    • Comparative analysis requires external evidence.
    • You are uncertain whether internal knowledge alone is sufficient.

    Examples requiring research:

    • Latest NVIDIA earnings
    • Compare GPT-5.5 with Claude
    • Current AI startup landscape
    • Research semiconductor industry trends
    • Recent advances in agentic AI
    • Analyze Apple's financial performance
    • Compare cloud providers in 2026

    Return requires_research=false ONLY when ALL of the following are true:

    • The answer is based on stable, well-established knowledge.
    • The answer is primarily explanatory or educational.
    • The answer does NOT require current information.
    • External verification is unnecessary.
    • No web search is needed.
    • No citations or evidence are expected.

    Examples NOT requiring research:

    • What is machine learning?
    • Explain recursion.
    • What is TCP/IP?
    • Explain LangGraph.
    • What is reinforcement learning?
    • Explain binary search trees.
    • Explain operating systems.
    • What is the CAP theorem?

    When uncertain, choose requires_research=true.

    ------------------------------------------------------------
    CRITICAL RULES
    ------------------------------------------------------------

    Never answer the user's query.

    Never rewrite it.

    Never improve it.

    Never infer missing intent.

    Never invent missing information.

    Optimize for preventing unnecessary research while NEVER skipping research when external evidence could improve correctness.

    ------------------------------------------------------------
    OUTPUT
    ------------------------------------------------------------

    Return ONLY valid JSON.

    Do NOT use markdown.

    Do NOT include explanations outside the JSON.

    Return exactly this schema:

    {{
        "is_valid": true,
        "requires_approval": false,
        "requires_external_research": true,
        "classifier_reason": "A concise explanation of the classification."
    }}
  """
  
  response = llm.invoke([HumanMessage(content=query_classifier_prompt)])
  raw_content = response.content[0]['text'].strip()
  raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.MULTILINE)

  try:
    verdict = json.loads(raw_content)
    is_valid = bool(verdict.get('is_valid', True))
    requires_approval = bool(verdict.get("requires_approval", False))
    requires_external_research = bool(verdict.get("requires_external_research", True))
    classifier_reason = verdict.get("classifier_reason")
    parse_failed = False
  except:
    is_valid, requires_approval, requires_external_research, classifier_reason = True, False, True, ""
    parse_failed = True


  if not is_valid:
    next_step = "end"
    termination_reason = "Query is incomplete or malformed. Please provide a clearer research request."
  elif requires_approval:
    next_step = "human_approval"
    termination_reason = ""
  elif not requires_external_research:
    next_step = "direct_knowledge_agent"
    termination_reason = ""
  else:
    next_step = "researcher"
    termination_reason = ""

  agent_message = f"""
    🚦 Query Classifier completed {"with PARSE FAILURE — defaulted to proceed" if parse_failed else "successfully"}.

    Valid: {is_valid}
    Requires Approval: {requires_approval}
    Requires External Research: {requires_external_research}
    Reason: {classifier_reason}
    Next → {next_step}
  """

  print("Query Classifier Done ✅")
  
  return {
    "messages": [AIMessage(content=agent_message)],
    "is_valid": is_valid,
    "termination_reason": termination_reason,
    "requires_approval": requires_approval,
    "requires_external_research": requires_external_research,
    "classifier_reason": classifier_reason,
    "route": next_step
  }
  
