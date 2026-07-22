# Lumen - Multi Agent Research Assistant

A multi-agent research assistant built on LangGraph. It classifies a query, decides whether it needs external research or can be answered from internal knowledge, pauses for human approval on sensitive requests, and produces a cited, confidence-aware report — with all of that verified by an actual test suite, not just a demo run.

---

## What Lumen does

You ask a question. Lumen:

1. **Classifies it** — is this simple, does it need external research, or is it sensitive enough to need a human in the loop?
2. **Routes accordingly** — answers directly from internal knowledge, kicks off external research, or pauses and asks a human to approve, reject, or edit the query before continuing.
3. **Researches, critiques, and extracts** — gathers sources, filters weak ones, pulls structured evidence out of what's left.
4. **Detects conflicts** — if sources disagree, that disagreement is surfaced, not silently resolved in favor of whichever source got read last.
5. **Writes the report** — cited, and honest about what it doesn't know. If the evidence is thin or contradictory, the report says so instead of presenting a confident answer built on shaky ground.

---

## Architecture

```
START
  │
  ▼
Query Classifier ──┬──▶ Direct Knowledge Agent ──▶ Report Writer ──▶ END
                    │                                    ▲
                    ├──▶ Human Approval ──▶ (approve/edit/reject)
                    │         │
                    │         ├─ approve ──▶ Researcher
                    │         ├─ edit ─────▶ Query Classifier (re-runs, fresh)
                    │         └─ reject ───▶ END
                    │
                    └──▶ Researcher
                              │
                              ▼
                          Supervisor ──▶ (loop back to Researcher if evidence is weak)
                              │
                              ▼
                        Source Critic
                              │
                              ▼
                     Evidence Extractor ──▶ Conflict Detector ──▶ Report Writer ──▶ END
```

Six core nodes — Query Classifier, Researcher, Source Critic, Evidence Extractor, Conflict Detector, Report Writer — plus a Human Approval node that sits in front of anything sensitive, and a Supervisor that can send weak research back for another pass instead of letting it through.

State persists via a checkpointer (SqliteSaver locally, Postgres-ready), so an interrupted run — whether from a human approval pause or an actual process restart — resumes from exactly where it left off, not from scratch.

---

## What actually differentiates this from a tutorial clone

Most agentic AI tutorials build a linear chain, run it once, and call it done. Lumen was built the same way at first — and every one of the differentiators below exists because a version of this system failed in exactly the way a tutorial clone would, and got fixed.

**State survives a real process death, not just a happy path.**
Verified by pulling the actual checkpoint database mid-run and confirming state fields flip correctly across an interrupt boundary — not by watching a terminal print something that looked fine.

**Human approval has three real branches, and edit actually re-evaluates.**
Approve and reject are easy. Edit is the one most systems fake: a user rewrites a flagged query mid-flow, and the classifier has to genuinely re-run on the new text, not just swap a string and continue on stale reasoning. Verified by pulling the classifier's reasoning text before and after an edit and confirming it actually changed.

**Degraded evidence changes what the report says, not just a flag it sets.**
When sources are thin, missing, or contradictory, the report shifts into disclosure — presenting conflicting figures side by side and explaining why they diverge, instead of picking one and asserting it as settled fact.

**It resists being told what to conclude.**
Tested against adversarial inputs — fake system overrides, "ignore previous instructions," text planted specifically to force a verbatim output. None of it changed routing, approval decisions, or leaked into the final report.

**Every claim above is backed by an eval harness, not a demo run.**
28 test cases across five categories (direct knowledge, research-required, human-approval, adversarial, degraded-evidence), asserting against real state fields and message content — not eyeballed output. Caught and fixed a real production bug during the process (a `.strip()` call breaking on list-formatted model output from certain Gemini models).

---

## What's actually hard to copy here

For a project this size, "moat" isn't the right word — there's no defensibility in the startup sense. What's genuinely harder to replicate than the code itself:

- **The habit of testing until something breaks, then reading the failure instead of assuming the system is wrong.** Several eval "failures" turned out to be incorrect test assumptions, not bugs — the discipline was in checking which before touching either.
- **Treating "it ran once and looked fine" as unverified, always.** Most of the real bugs in this project's history (silent pipeline bypass on extraction failure, false confidence despite a degraded flag, leaked instruction text, cross-request state contamination from a hardcoded thread ID) survived exactly because a single clean-looking run was mistaken for proof.
- **Choosing to show the failures, not hide them.** This README documents bugs that were found and fixed rather than presenting the system as having always worked.

---

## Lessons (the real bug log)

These are documented, not implied — each one was a real defect, found and closed:

- **Silent pipeline bypass**: extraction failures let conflict detection run on zero evidence while the final report still looked polished and confident.
- **False confidence despite `degraded=True`**: the flag was set correctly, but the report writer's language didn't reflect it — an internal state signal that never reached the user.
- **Leaked instruction text**: routing/system text occasionally surfaced in the user-facing report.
- **Unset `max_tokens` default**: caused systematic truncation; root cause of most extraction failures traced to this, not input size. Fixed at 8192.
- **Hardcoded `thread_id=1`**: created a cross-request state contamination risk — two concurrent users could have collided on the same thread.
- **In-memory state loss on restart**: fixed by adding a real checkpointer (SqliteSaver/PostgresSaver) in place of in-memory state.
- **`.strip()` on list-formatted content**: certain Gemini models return `message.content` as a list of parts rather than a plain string; code assuming a string broke silently until the eval harness's automated runs surfaced it.

---

## Tech stack

- **Orchestration**: LangGraph (multi-node graph, conditional routing, native `interrupt()`/`Command(resume=...)` for human-in-the-loop)
- **Persistence**: SqliteSaver (Postgres-ready checkpointer)
- **API layer**: FastAPI (`/research`, `/research/resume`)
- **LLM providers**: Groq, Gemini
- **Deployment**: Railway (backend)

---

## Testing

Lumen ships with a 28-case eval harness (`eval_runner`) covering:

| Category | What it checks |
|---|---|
| Direct knowledge | Correct internal routing, no leaked instructions, no unnecessary "degraded" flags |
| Research required | Correct external routing, degraded-evidence handling matches the actual evidence quality |
| Human approval | Interrupt fires correctly; approve/reject/edit all verified, including that edit triggers real re-classification |
| Adversarial | Prompt injection, fake overrides, and instruction-hijack attempts — none succeed |
| Degraded evidence | Genuinely unanswerable or sensitive queries are either flagged, hedged honestly, or routed to human approval — never answered with false confidence |

Every check asserts against actual state fields, checkpoint data, or message content — not output that merely "looks right."

---

## Setup

```bash
git clone <repo-url>
cd lumen/backend
uv add -r requirements.txt
# set GROQ_API_KEY, GEMINI_API_KEY, and DB connection details in .env
python executor.py        # interactive CLI run
uvicorn main:app --reload # API server
```

Run the eval suite:

```bash
python eval_runner.py --category direct_knowledge   # or omit --category to run everything
```

---

## Roadmap

- [ ] Frontend: live status tracker, in-UI human-approval card, visible confidence/degraded flag, source citations
- [ ] Rate-limit-aware request queue for public demo use
- [ ] Full 28-case eval run logged with before/after numbers for each major fix
- [ ] Multi-tenant support (currently single-user, single-thread-per-request)

---

## Things worth adding that aren't here yet

A few honest gaps, worth naming rather than leaving implicit:

- **No CI**: the eval harness runs manually. Wiring it into a GitHub Action so every push gets a pass-rate check would turn "I ran the eval once" back into the exact failure mode this project was built to move away from.
- **No cost tracking**: token usage and per-run cost aren't logged anywhere. Worth adding before treating this as production-grade — it directly matters once a real user is running unmetered queries against it.
- **No versioned eval results**: the CSV outputs from each run aren't checked into the repo. Committing them (or at least the summary numbers) per major change would make "the pass rate went from X to Y after this fix" a verifiable claim instead of a remembered one.
- **Single-provider fragility**: currently dependent on Groq/Gemini free-tier rate limits, which already caused real failures during eval runs. A fallback or a paid tier is a prerequisite for showing this live to anyone, not a nice-to-have.

---