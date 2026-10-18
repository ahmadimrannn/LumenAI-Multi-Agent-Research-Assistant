from agents.agents_state import AgentsState
from config.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
from event_logger import log_event
import json
import re

def query_classifier_agent(state: AgentsState):
  """
    Single LLM call: checks query validity and sensitivity before any
    research is performed, to avoid burning the full pipeline on malformed
    or unsafe input. Also handles basic conversational greetings and questions
    directly and quickly without running the whole pipeline.
  """

  query = state.get('query') or state.get('original_query') or ""
  query = query.strip() if query else None

  # Empty or whitespace
  if not query:
    log_event(
      service="lumen", event_type="query_classifier_invalid", severity="info",
      node_or_route="query_classifier",
      message="Query rejected as empty.",
      context={"query": query},
    )
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
    log_event(
      service="lumen", event_type="query_classifier_invalid", severity="info",
      node_or_route="query_classifier",
      message="Query rejected because it contains only punctuation or symbols.",
      context={"query": query},
    )
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
    log_event(
      service="lumen", event_type="query_classifier_invalid", severity="info",
      node_or_route="query_classifier",
      message="Query rejected because it contains repeated characters only.",
      context={"query": query},
    )
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
    log_event(
      service="lumen", event_type="query_classifier_invalid", severity="info",
      node_or_route="query_classifier",
      message="Query rejected because it appears to be random keyboard input.",
      context={"query": query},
    )
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

  # Fast path for common basic conversational greetings and questions
  clean_query = query.lower().strip("?!., \t\n\r")
  FAST_GREETINGS = [
      (
          r"^(hi|hello|hey|greetings|howdy|hi\s+there|hello\s+there|hey\s+there)$",
          "Hello! I am Lumen, your research assistant. I can investigate complex topics, analyze sources, and write detailed reports. What would you like to explore today?",
      ),
      (
          r"^(how\s+are\s+you|how\s+are\s+you\s+doing|how's\s+it\s+going|how\s+is\s+it\s+going|how's\s+everything|how\s+are\s+things)$",
          "I'm doing well, thank you for asking! I'm ready to help you with any research, deep dives, or analysis. What topic is on your mind?",
      ),
      (
          r"^(who\s+are\s+you|what\s+are\s+you|what\s+is\s+lumen|tell\s+me\s+about\s+yourself)$",
          "I am Lumen, an AI-powered multi-agent research assistant. I synthesize evidence from multiple sources, detect potential conflicts or bias, and produce structured, comprehensive research reports.",
      ),
      (
          r"^(what\s+can\s+you\s+do|how\s+can\s+you\s+help(\s+me)?|what\s+do\s+you\s+do|help(\s+me)?)$",
          "I can assist you with comprehensive research across scientific, technical, market, and general topics. Just ask a question or propose a subject, and I will investigate it, verify facts, and prepare a structured report.",
      ),
      (
          r"^(good\s+morning|good\s+afternoon|good\s+evening)$",
          "Good day! How can I assist you with your research today?",
      ),
      (
          r"^(thank\s+you|thanks|thanks\s+a\s+lot|thank\s+you\s+very\s+much)$",
          "You're very welcome! Let me know whenever you'd like to investigate another topic.",
      ),
  ]

  for pattern, reply in FAST_GREETINGS:
    if re.match(pattern, clean_query):
      agent_message = f"""
        🚦 Query Classifier completed successfully (conversational fast path).

        Valid: True
        Requires Approval: False
        Requires External Research: False
        Reason: Conversational greeting or basic inquiry.
        Next → end
      """
      log_event(
        service="lumen", event_type="query_classifier_conversational", severity="info",
        node_or_route="query_classifier",
        message="Query identified as basic greeting or conversational question.",
        context={"query": query, "route": "end"},
      )
      return {
        "messages": [AIMessage(content=agent_message)],
        "is_valid": True,
        "termination_reason": "",
        "requires_approval": False,
        "requires_external_research": False,
        "classifier_reason": "Conversational greeting or basic question.",
        "route": "end",
        "findings": reply,
        "knowledge_source": "internal_knowledge"
      }

  query_classifier_prompt = f"""
    You are a Query Intake Classifier for a research assistant named Lumen.

    Your job is to determine:

    1. Whether the query is valid or conversational.
    2. Whether it requires human approval.
    3. Whether it requires a full external research workflow.

    QUERY

    {query}

    ------------------------------------------------------------
    ASSESSMENT 1 — VALIDITY & CONVERSATIONAL CHECK
    ------------------------------------------------------------

    Determine whether this input is:
    A) A conversational greeting, pleasantry, or basic general question (e.g. "hello", "hi", "how are you", "who are you", "what can you do", "nice to meet you").
    B) A valid research or knowledge inquiry (e.g. "what is machine learning", "latest news on Mars rover", "explain recursion").
    C) Truly invalid input (e.g. empty, pure gibberish like "asdfghjkl", random symbols, keyboard mash).

    IMPORTANT RULES FOR CONVERSATIONAL INQUIRIES:
    • Conversational greetings and basic polite questions ARE VALID (is_valid=true).
    • If the query is a conversational greeting, pleasantry, or general question about yourself/Lumen without an in-depth research topic, set is_conversational=true and provide a helpful, friendly, natural, and concise reply in direct_response. Set requires_external_research=false.
    • If the query contains a greeting ALONG WITH an actual research question (e.g. "Hello! What are the latest breakthroughs in fusion energy?"), set is_conversational=false and evaluate the research question normally.
    • Only mark is_valid=false if the input is actual nonsense, gibberish, or completely indecipherable noise.

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

    • The query is a conversational greeting/question (is_conversational=true), OR:
    • The answer is based on stable, well-established knowledge.
    • The answer is primarily explanatory or educational.
    • The answer does NOT require current information.
    • External verification is unnecessary.
    • No web search is needed.
    • No citations or evidence are expected.

    Examples NOT requiring research:

    • Hello / how are you / what can you do
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

    Never rewrite the user's research query.
    Never infer missing intent for research topics.
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
        "is_conversational": false,
        "direct_response": "",
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
    is_conversational = bool(verdict.get('is_conversational', False))
    direct_response = verdict.get('direct_response', '').strip()
    requires_approval = bool(verdict.get("requires_approval", False))
    requires_external_research = bool(verdict.get("requires_external_research", True))
    classifier_reason = verdict.get("classifier_reason", "")
    parse_failed = False
  except Exception:
    is_valid, is_conversational, direct_response, requires_approval, requires_external_research, classifier_reason = True, False, "", False, True, ""
    parse_failed = True

  findings = ""
  if not is_valid:
    next_step = "end"
    termination_reason = "Query is incomplete or malformed. Please provide a clearer research request."
  elif is_conversational and direct_response:
    next_step = "end"
    termination_reason = ""
    findings = direct_response
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
    Query Classifier completed {"with PARSE FAILURE - defaulted to proceed" if parse_failed else "successfully"}.

    Valid: {is_valid}
    Conversational: {is_conversational}
    Requires Approval: {requires_approval}
    Requires External Research: {requires_external_research}
    Reason: {classifier_reason}
    Next -> {next_step}
  """

  print("Query Classifier Done")
  log_event(
    service="lumen", event_type="query_classifier_decision", severity="info",
    node_or_route="query_classifier",
    message="Query classification completed.",
    context={
      "is_valid": is_valid,
      "is_conversational": is_conversational,
      "requires_approval": requires_approval,
      "requires_external_research": requires_external_research,
      "route": next_step,
      "classifier_reason": classifier_reason,
    },
  )
  
  result = {
    "messages": [AIMessage(content=agent_message)],
    "is_valid": is_valid,
    "termination_reason": termination_reason,
    "requires_approval": requires_approval,
    "requires_external_research": requires_external_research,
    "classifier_reason": classifier_reason,
    "route": next_step
  }

  if findings:
    result["findings"] = findings
    result["knowledge_source"] = "internal_knowledge"

  return result
