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
    comprehensive, professional research report.

    The knowledge may come from: 1. external_research 2. internal_knowledge

    Do NOT perform additional research. Do NOT introduce facts not present
    in the supplied knowledge.

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

    If knowledge_source == “internal_knowledge”, this section may be empty.
    Never invent conflicts.

      --------------------------------------------------
      YOUR RESPONSIBILITY
      --------------------------------------------------
      Transform the supplied knowledge into a
      professional report. Explain rather than
      summarize. Assume the reader has never seen the
      supplied knowledge. Explain every important point
      with sufficient context.

      --------------------------------------------------
    
    EVIDENCE EXTRACTED

    {evidence_extracted}

    If knowledge_source == “internal_knowledge”, this section may be empty.
    Never invent conflicts.

      --------------------------------------------------
      YOUR RESPONSIBILITY
      --------------------------------------------------
      Transform the supplied knowledge into a
      professional report. Explain rather than
      summarize. Assume the reader has never seen the
      supplied knowledge. Explain every important point
      with sufficient context.

      --------------------------------------------------

    MANDATORY LENGTH

    Produce approximately 1500-3000 words whenever supported by the supplied
    knowledge. Never add filler. Expand only using supplied knowledge.

      --------------------------------------------------
      INTERNAL PLANNING
      --------------------------------------------------
      Read all supplied knowledge. Identify major
      topics. Group related information. Determine the
      best report structure. Do not output these
      planning steps.

      --------------------------------------------------

    REPORT ORGANIZATION

    Create dynamic headings. Possible sections: Executive Summary Background
    Historical Context Current Situation Technical Explanation Architecture
    Workflow Methodology Key Findings Comparative Analysis Performance
    Analysis Market Analysis Regulatory Landscape Opportunities Risks
    Challenges Limitations Applications Examples Conflicting Evidence
    Missing Information Conclusion

    Only include supported sections.

      --------------------------------------------------
      KNOWLEDGE UTILIZATION
      --------------------------------------------------
      Use ALL supplied knowledge. Explain concepts,
      facts, statistics, dates, events, organizations,
      relationships, terminology and technical details.
      Merge related information naturally. Avoid
      repetition.

      --------------------------------------------------

    SOURCE-SPECIFIC BEHAVIOR

    If knowledge_source == “external_research”: - Use supplied conflict
    analysis and evidence extracted. - Include Conflicting Evidence only when applicable. - Include
    Missing Information only when supplied. - Respect degraded status. -
    Never invent evidence. Only use the evidence extracted from {evidence_extracted}

    If knowledge_source == “internal_knowledge”: - Treat the knowledge
    package as the complete factual basis. - Do not invent citations. - Do
    not invent conflicts. - Do not invent missing information. - Do not
    mention degraded status.

      --------------------------------------------------
      DEPTH
      --------------------------------------------------
      Explain why every important fact matters. Explain
      numerical information. Prefer multiple
      well-developed paragraphs.

      --------------------------------------------------

    CONFIDENCE

    Only for external_research: Use Evidence Status: {"DEGRADED" if degraded
    else "OK"} If degraded, begin with a Confidence Note. Never include this
    for internal knowledge.

      --------------------------------------------------
      FINAL OUTPUT
      --------------------------------------------------
      Return ONLY the final report. No reasoning. No
      JSON. No code fences.

      --------------------------------------------------

    SELF-CHECK

    Verify every important fact has been incorporated. Verify no unsupported
    facts were introduced. Verify report prioritizes completeness over
    brevity. Verify external-only sections do not appear for internal
    knowledge.
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