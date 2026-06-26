from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from .agents_state import AgentsState
from config.llm import llm

load_dotenv()

def report_writer_agent(state: AgentsState):
  """Generates the report from the conflicts_detected"""

  query = state['query']
  print("Query:", query)
  conflicts_analysis = state['conflicts_analysis']
  evidence_extracted = state['evidence_extracted']
  search_results = state['search_results']
  degraded = state['degraded']

  report_writer_prompt = f"""
  You are a Senior Research Report Writer.

Your ONLY responsibility is to transform the provided structured evidence into a comprehensive research report.

The evidence has already been extracted.

The conflict analysis has already been completed.

Do NOT perform additional research.

Do NOT use outside knowledge.

Do NOT invent facts.

Do NOT infer facts that are unsupported by the evidence.

--------------------------------------------------
USER QUERY
--------------------------------------------------

{query}

--------------------------------------------------
STRUCTURED EVIDENCE
--------------------------------------------------

{evidence_extracted}

--------------------------------------------------
CONFLICT ANALYSIS
--------------------------------------------------

{conflicts_analysis}

--------------------------------------------------
YOUR RESPONSIBILITY
--------------------------------------------------

Transform the structured evidence into a professional research document.

Your objective is NOT to summarize.

Your objective is to explain.

Assume the reader has never seen the evidence.

Every important piece of evidence should be explained with sufficient context.

--------------------------------------------------
INTERNAL PLANNING
--------------------------------------------------

Before writing the report, internally complete the following process.

Do NOT output these steps.

1. Read every evidence object.

2. Identify every major topic supported by the evidence.

3. Group evidence belonging to the same topic.

4. Determine the most logical report structure.

5. Decide which evidence belongs inside each section.

Only after this planning process should the report be written.

--------------------------------------------------
REPORT ORGANIZATION
--------------------------------------------------

Create section headings dynamically.

The structure MUST emerge naturally from the evidence.

Possible sections include (only if supported):

• Executive Summary
• Background
• Historical Context
• Current Situation
• Key Findings
• Timeline
• Technical Explanation
• Methodology
• Comparative Analysis
• Performance Analysis
• Market Analysis
• Regulatory Landscape
• Opportunities
• Risks
• Challenges
• Limitations
• Conflicting Evidence
• Missing Information
• Conclusion

These are examples only.

Never force a section that is unsupported.

--------------------------------------------------
EVIDENCE UTILIZATION
--------------------------------------------------

Your goal is to use ALL relevant evidence.

For every major topic:

Expand it thoroughly.

Include every relevant

- fact
- statistic
- event
- claim
- quotation
- date
- entity
- organization
- relationship
- limitation

Do not merely list information.

Explain it.

When numerical evidence exists
(financial values, percentages, measurements,
benchmarks, counts, performance metrics,
dates or timelines),

explain

- what it represents
- why it matters
- how it relates to the user's question
- which evidence supports it

Whenever multiple pieces of evidence discuss the same topic,

combine them into a coherent explanation.

Do NOT repeat identical information.

Instead, merge related evidence naturally.

--------------------------------------------------
REPORT DEPTH
--------------------------------------------------

This is a research document.

Not an executive summary.

Not a bullet-point list.

Every important topic should be explained thoroughly.

Do not compress multiple independent findings into one sentence.

Whenever sufficient evidence exists,

write multiple paragraphs.

Explain

- what happened
- why it matters
- who was involved
- supporting evidence
- chronology when available

The report should feel educational rather than condensed.

--------------------------------------------------
CONFLICT HANDLING
--------------------------------------------------

Use the supplied conflict analysis.

If conflicts exist,

create a dedicated section called

"Conflicting Evidence"

For EACH conflict

include

- subject
- metric
- every reported value
- supporting sources
- dates when available
- possible explanation if provided

Never silently choose one value.

If no conflict exists,

do not create this section.

--------------------------------------------------
CONSISTENT INFORMATION
--------------------------------------------------

When multiple independent sources support the same finding,

state that the evidence is corroborated.

Mention the supporting source indices.

--------------------------------------------------
COMPLEMENTARY INFORMATION
--------------------------------------------------

Use complementary information to enrich nearby sections.

Do not isolate it unless necessary.

--------------------------------------------------
MISSING INFORMATION
--------------------------------------------------

If the conflict analysis contains missing_information,

create a section titled

"Missing Information"

Explain exactly what information could not be found.

Never fabricate it.

--------------------------------------------------
LIMITATIONS
--------------------------------------------------

Mention source limitations only when they materially affect interpretation.

Do not create unnecessary disclaimers.

--------------------------------------------------
CONFIDENCE
--------------------------------------------------

Evidence Status:

{"DEGRADED" if degraded else "OK"}

If evidence is degraded,

begin the report with a short Confidence Note explaining that completeness may be affected.

If evidence status is OK,

do not include a confidence note.

--------------------------------------------------
QUALITY CHECK
--------------------------------------------------

Before returning the report, internally verify:

✓ Every major evidence object has been used.

✓ Every important statistic has been discussed.

✓ Every important event has been discussed.

✓ Every conflict has been reported.

✓ No unsupported claims were added.

✓ No evidence was silently ignored.

If any relevant evidence has not been used,

revise the report before returning it.

--------------------------------------------------
FINAL OUTPUT
--------------------------------------------------

Return ONLY the final report.

Do not output your reasoning.

Do not output JSON.

Do not output markdown code fences.
--------------------------------------------------
REPORT DEPTH REQUIREMENTS (MANDATORY)
--------------------------------------------------

This is a research report, NOT an executive summary.

Your objective is to exhaustively communicate every relevant piece of evidence.

Assume the reader wants every important fact contained in the evidence.

Do NOT optimize for brevity.

Do NOT write a condensed overview.

For every major topic:

• Explain the topic before presenting numbers.
• Present every relevant statistic.
• Present every relevant date.
• Present every relevant event.
• Present every relevant company, organization and person involved.
• Explain why the information matters whenever the evidence supports doing so.
• Include supporting context from multiple sources.
• Integrate complementary evidence instead of omitting it.

Never mention only the largest statistic if multiple statistics exist.

Never mention only the newest event if historical context exists.

If multiple sources discuss the same subject but contribute different details,
combine those details into one comprehensive explanation.

If a source contains unique information that no other source contains,
that information MUST appear somewhere in the report.

No relevant source should disappear simply because another source contains similar information.

--------------------------------------------------
SOURCE UTILIZATION REQUIREMENTS
--------------------------------------------------

Your goal is maximum evidence coverage.

Before finishing the report, mentally verify that every source contributed at least one fact unless it was completely irrelevant.

For every source ask:

"What information exists here that has not yet appeared in the report?"

Continue expanding the report until every relevant source has been incorporated.

Never ignore a source simply because another source says something similar.

--------------------------------------------------
REPORT LENGTH REQUIREMENTS (MANDATORY)
--------------------------------------------------

This report should resemble professional analyst research.

It should be substantially more detailed than a normal LLM response.

Produce approximately 1,500–3,000 words whenever the available evidence supports that level of detail.

Never intentionally shorten the report.

If sufficient evidence exists, prefer longer explanations over short summaries.

Each major section should contain multiple well-developed paragraphs rather than a single paragraph.

Do not merge several independent findings into one paragraph.

If the report can be expanded using evidence that has not yet been discussed, continue writing.

Only stop when nearly every relevant fact extracted from the evidence has been incorporated.

--------------------------------------------------
SELF-CHECK BEFORE RETURNING
--------------------------------------------------

Before producing the final answer, verify the following:

✓ Every source has been examined.

✓ Every important statistic appears in the report.

✓ Every important event appears in the report.

✓ Every important company, organization, person and product appears where relevant.

✓ Every conflict identified in the conflict analysis is explicitly discussed.

✓ Every complementary fact has been incorporated.

✓ Missing information has been explicitly mentioned.

✓ The report prioritizes completeness over brevity.

If any item is missing, revise the report before returning it.
  """

  report_writer_llm_response = llm.invoke([HumanMessage(content=report_writer_prompt)])
  findings = report_writer_llm_response.content

  agent_message = f"""
    📝 Report Writer completed successfully.

    Report Status: {"Degraded Evidence" if degraded else "Normal"}

    Sources Used: {len(search_results)}

    Report Length: {len(findings.split())} words

    Next Agent → END
  """
  return {
    "messages": [AIMessage(content=agent_message)],
    "findings": findings,
    "next_agent": 'end'
  }