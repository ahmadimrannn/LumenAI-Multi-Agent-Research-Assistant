from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from .agents_state import AgentsState
from config.llm import llm

load_dotenv()

def report_writer_agent(state: AgentsState):
  """Generates the report from the conflicts_detected"""

  query = state['query']
  print("Query:", query)

  knowledge_source = state.get("knowledge_source")
  knowledge_content = state.get("knowledge_content", "")
  print("Knowledge Content", knowledge_content)
  conflicts_analysis = state.get("conflicts_analysis", "")
  evidence_extracted = state.get("evidence_extracted", "")
  search_results = state.get("search_results", [])
  degraded = state.get("degraded", False)
  extraction_failed = state.get("extraction_failed", "False")

  degraded_block = (
    "[INTERNAL INSTRUCTION — DO NOT QUOTE OR REPEAT ANY PART OF THIS BLOCK IN YOUR OUTPUT]\n"
    "This evidence run is DEGRADED. Your response must begin with a section titled "
    "'Confidence Note' (use that exact heading) followed by 1-2 sentences, IN YOUR OWN WORDS, "
    "stating that the evidence gathering process did not fully meet quality thresholds and that "
    "completeness or accuracy may be affected. Then continue directly into the Executive Summary. "
    "Do not echo, paraphrase-quote, or restate this instruction itself anywhere in your output — "
    "only the Confidence Note content you write should appear."
    if degraded else
    "[INTERNAL INSTRUCTION — DO NOT QUOTE OR REPEAT ANY PART OF THIS BLOCK IN YOUR OUTPUT]\n"
    "Evidence Status: OK. Do not include a confidence note."
  )

  report_writer_prompt = f"""
    {degraded_block}

    You are the Senior Report Writer for a multi-agent research assistant.

    Your ONLY responsibility is to transform the supplied knowledge into a
    professional research report.

    The knowledge may come from one of three situations:

    1. external_research (successful)
    2. external_research (evidence extraction failed)
    3. internal_knowledge

    Do NOT perform additional research.

    Do NOT introduce facts not present in the supplied knowledge.

    Never fabricate evidence, citations, conflicts, missing information,
    or conclusions.

    --------------------------------------------------
    USER QUERY
    --------------------------------------------------

    {query}

    --------------------------------------------------

    KNOWLEDGE SOURCE

    {knowledge_source}

    --------------------------------------------------
    KNOWLEDGE CONTENT
    --------------------------------------------------

    {knowledge_content}

    --------------------------------------------------

    CONFLICT ANALYSIS

    {conflicts_analysis}

    If knowledge_source == "internal_knowledge", this section may be empty.

    Never invent conflicts.

    --------------------------------------------------

    EVIDENCE EXTRACTED

    {evidence_extracted}

    If knowledge_source == "internal_knowledge", this section may be empty.

    Never invent evidence.

    --------------------------------------------------

    EXTRACTION STATUS

    Extraction Failed: {extraction_failed}

    --------------------------------------------------

    YOUR RESPONSIBILITY

    Transform the supplied knowledge into a professional,
    well-structured report.

    Explain rather than summarize.

    Assume the reader has never seen the supplied knowledge.

    Explain every important point with sufficient context.

    Only write what is supported by the supplied knowledge.

    --------------------------------------------------

    MANDATORY LENGTH

    When sufficient knowledge exists, produce approximately
    1500-3000 words.

    Never add filler.

    Expand only using supplied knowledge.

    --------------------------------------------------

    INTERNAL PLANNING

    Read all supplied knowledge.

    Identify major topics.

    Group related information.

    Determine the best report structure.

    Do NOT output these planning steps.

    --------------------------------------------------

    REPORT ORGANIZATION

    Create dynamic headings.

    Possible sections include:

    - Executive Summary
    - Background
    - Historical Context
    - Current Situation
    - Technical Explanation
    - Architecture
    - Workflow
    - Methodology
    - Key Findings
    - Comparative Analysis
    - Performance Analysis
    - Market Analysis
    - Regulatory Landscape
    - Opportunities
    - Risks
    - Challenges
    - Limitations
    - Applications
    - Examples
    - Conflicting Evidence
    - Missing Information
    - Conclusion

    Only include sections that are supported by the supplied knowledge.

    --------------------------------------------------

    KNOWLEDGE UTILIZATION

    Use ALL supplied knowledge.

    Explain concepts, facts, terminology,
    statistics, organizations, relationships,
    technical details, and important observations.

    Merge related information naturally.

    Avoid repetition.

    --------------------------------------------------

    SOURCE-SPECIFIC BEHAVIOR

    ==============================
    CASE 1: internal_knowledge
    ==============================

    Treat the supplied knowledge as the complete factual basis.

    Do NOT invent:

    - citations
    - conflicts
    - missing information
    - degraded warnings
    - confidence notes

    Ignore external research sections if they are empty.

    ==============================
    CASE 2: external_research
    AND extraction_failed == False
    ==============================

    Use the supplied:

    - Knowledge Content
    - Evidence Extracted
    - Conflict Analysis

    Include Conflicting Evidence only when supplied.

    Include Missing Information only when supplied.

    Respect degraded status.

    Never invent evidence.

    Only reference evidence present in:

    {evidence_extracted}

    ==============================
    CASE 3: external_research
    AND extraction_failed == True
    ==============================

    Evidence extraction failed.

    This means no reliable evidence could be extracted from the research pipeline.

    DO NOT attempt to reconstruct evidence.

    DO NOT invent findings.

    DO NOT generate a normal research report.

    Instead, generate a short failure report with the following structure:

    # Research Report

    ## Executive Summary

    State that external research was attempted but no usable evidence
    could be extracted.

    ## What Happened

    Briefly explain that the report cannot be completed because the
    evidence extraction stage produced zero usable evidence.

    ## Available Information

    If Knowledge Content contains any useful information,
    present it clearly while explicitly stating that it has NOT been
    validated through the normal evidence extraction pipeline.

    If no meaningful knowledge exists,
    state that no reliable information is available.

    ## Conclusion

    Explain that no research conclusions can be drawn because the
    required evidence extraction step failed.

    Do NOT invent:

    - evidence
    - conflicts
    - missing information
    - citations
    - analysis
    - recommendations
    - technical explanations

    The report must clearly communicate failure rather than pretending
    the research succeeded.

    --------------------------------------------------

    DEPTH

    Explain why every important fact matters.

    Explain numerical information.

    Prefer multiple well-developed paragraphs whenever enough
    knowledge exists.

    --------------------------------------------------

    CONFIDENCE

    Only for successful external research.

    Use:

    Evidence Status: {"DEGRADED" if degraded else "OK"}

    If degraded, begin the report with a Confidence Note.

    Never include a Confidence Note for:

    - internal_knowledge
    - extraction_failed == True

    --------------------------------------------------

    FINAL OUTPUT

    Return ONLY the final report.

    No reasoning.

    No JSON.

    No code fences.

    --------------------------------------------------

    SELF-CHECK

    Before producing the report, verify:

    1. Every important supplied fact has been incorporated.
    2. No unsupported facts were introduced.
    3. No fabricated evidence or citations were added.
    4. External-only sections do not appear for internal knowledge.
    5. If extraction_failed == True, the report clearly communicates the failure instead of producing a normal research report.
    6. If extraction_failed == True, no conflicts, evidence, findings, or conclusions were invented.
  """


  report_writer_llm_response = llm.invoke([HumanMessage(content=report_writer_prompt)])
  findings = report_writer_llm_response.content

  leak_marker = [
    "MANDATORY FIRST ELEMENT OF YOUR OUTPUT",
    "INTERNAL INSTRUCTION",
    "DO NOT QUOTE OR REPEAT"
  ]

  for marker in leak_marker:
    idx = findings.find(marker)
    if idx != -1:
      # Drop everything up to the next double-newline after the marker,
      # since the leaked block typically ends right before the real Confidence Note begins
      next_break = findings.find("\n\n", idx)
      if next_break != -1:
        findings = findings[next_break:].lstrip()

  agent_message = f"""
    📝 Report Writer completed successfully.

    Report Status: {"Degraded Evidence" if degraded else "Normal"}

    Sources Used: {len(search_results)}

    Report Length: {len(findings.split())} words

    Next Agent → END
  """

  print("Report Writer Done ✅")

  return {
    "messages": [AIMessage(content=agent_message)],
    "findings": findings,
    "next_agent": 'end'
  }