---
name: cover-letter
description: Write a cover letter for a specific job by treating it like a product aimed at its readers. Reads the job description, the accomplishment bank, and prior cover letters; interviews the user for the "why" via AskUserQuestion; drafts; stress-tests with a 3-persona adversarial panel (parallel, sandboxed); applies convergent fixes; re-reviews; runs sense-of-style; files the result. Trigger phrases include "cover letter", "write a cover letter", "/cover-letter", "apply to [company]", "draft a cover letter for [role]".
---

# Cover Letter

Write a cover letter as a product with users. The letter has distinct readers (recruiter, hiring manager, peer, exec), each screening for different things. The job is to clear all of them. This skill runs the loop that produces a panel-validated letter: load context, interview for the why, draft, adversarial panel, fix, re-panel, style pass, file.

## Operating principles

- Voice is the candidate's. Direct, first-principles, punchy. No corporate tone, no hedging, no AI-writing tells. Load `references/writing-rules.md` and obey it, and read `config/profile.md` for the candidate's stated voice and tone.
- Hard rule: no em-dashes. Use commas, colons, periods.
- Specific beats generic, always. Numbers, names, dollar figures, the candidate's actual contribution. A letter that could be sent to any company is a failed letter.
- Do not fabricate. Every claim traces to the accomplishment bank, a prior letter, or the user's interview answers. When a claim needs a fact you do not have, ask (Step 2); never invent a metric. If the user cannot supply one, describe the mechanism instead of faking a number.
- Length: 250 to 400 words, 3 to 5 short paragraphs, one page. Going long is the default failure; cut before you add.

## Architecture (read once, then execute)

A sequential pipeline with one parallel fan-out at each review. Why it is built this way (do not "simplify" it):

- Reviews are sandboxed subagents run in parallel. Each persona review burns a lot of reasoning tokens. Spawning them as subagents keeps that reasoning out of the orchestrator's context; running the 3 in one message is faster and they are independent. The orchestrator ingests only the short structured reports.
- Writing stays in the orchestrator. The writer needs the full context (JD plus bank plus interview answers plus personas) that the orchestrator already holds. A writer subagent would just re-pay that cost. Write here.
- The fix pass adopts a fresh-writer mindset. When revising, do not defend the prior draft. Treat convergent findings as correct and rewrite the offending parts cleanly.
- Bounded convergence loop. Apply a fix only when two or more personas independently flag the same thing. Re-review. If a convergent blocker survives, do one more fix pass. Cap at 3 rounds total, then ship with a note on any residual single-persona concerns.

## Pipeline

### Step 0 : Load context
Read, in this order:
1. The job description. Standing intake: `applications/<Company> - <Role>/jd.md`. If the user names an application whose folder exists, read its `jd.md`. If they paste JD text or give a URL instead, scaffold that folder and save the JD to `jd.md` first (fetch the URL into the file), then proceed. This folder is the packet home: the JD lives here and the finished letter is written back here.
2. Accomplishment bank (primary fact source): your about-me.md (the accomplishment bank in your workspace; path = config key accomplishment_bank), the canonical superset of the candidate's wins with numbers and their real contribution. Pick the stories most relevant to this JD from here.
3. Prior cover letters from this skill's `examples/` and from any letters already filed under `applications/`. Read 1 to 3 for voice, structure, and reusable framings.
4. Personas: see Step 1. Use whatever reader-persona reference your harness provides, or assemble the default panel below from the JD itself.
5. Best practices and writing rules: `references/best-practices.md` and `references/writing-rules.md`. Candidate voice: `config/profile.md`.

Extract from the JD: the role, the product or team, the company, the 3 to 5 things the JD most wants, the explicit bets (for example "this role bets on AI"), and the company's culture (especially mission-driven shops; note them for the authenticity test).

### Step 1 : Pick the panel
Choose the 3 readers who will most determine this hire. Default panel: the target company's recruiter or head of TA (screen plus authenticity), a hard technical-leader archetype (overclaim and build-vs-hover detector), and a product-or-domain-craft archetype (decisions-vs-activity, user insight). Borrow recognizable company standards for the second and third to maximize lens diversity. State the chosen panel before drafting.

### Step 2 : Interview the user for the "why" (AskUserQuestion, MANDATORY GATE)
After reading the JD and before writing, pull the details and motivation that make writing good. Do not skip this; it is the single biggest quality lever. Ask 2 to 4 questions tuned to this JD and the gaps between it and the bank. Cover:
- Why this company, role, and now: the genuine reason, in the candidate's words. This powers the closing paragraph; mission-driven shops screen hard for authenticity versus pandering.
- The one accomplishment most relevant to this JD's core ask, and the candidate's specific contribution to it, so you isolate their work, not the team's.
- A number or a cost: a metric, or the tradeoff and cost of a key decision, that the bank does not already state.
- Anything to avoid: over-claims to soften, sensitive or classified specifics to keep vague, level-fit framing.

Weave the answers into the draft. If an answer reveals a stronger story than the bank, lead with it. In a headless run with no human, make reasonable calls from the bank and the JD; never invent a number.

### Step 3 : Draft (orchestrator writes)
Write the letter per `references/writing-rules.md`:
- Open with a quantified credential or a sharp company-specific insight. Never "I am writing to apply".
- Spine equals the JD's core competency. Make the paragraph proving it the centerpiece, built on one challenge to action to result story.
- Mirror the JD enough to prove fit; never parrot it.
- Mission or why paragraph in the candidate's own words, backed by evidence. Never quote the company's tagline back at them.
- Close confident and forward, no throat-clearing.
- Run the em-dash and AI-tells self-check before saving.

### Step 4 : Adversarial panel (parallel, sandboxed), round 1
Spawn the 3 chosen personas in a single message. Use `references/persona-review-template.md` to build each prompt: full letter verbatim plus the persona's read-priorities plus required structured output (verdict, gut reaction, scorecard 1 to 10, red flags, top 2 to 3 fixes). Tell each to stay in character, be brutally honest, no flattery.

### Step 5 : Synthesize and fix
Collect the 3 reports. A fix is mandatory when two or more personas flag the same issue. Single-persona flags are judgment calls; apply only if you agree. For fixes needing a fact you lack, return to the user with a tight question; do not invent. Apply fixes with a fresh-writer mindset. Re-run the em-dash and tells check.

### Step 6 : Re-panel and converge
Re-spawn the 3 personas (parallel) on the revised letter. If a convergent (two or more) blocker remains, fix again and, if needed, do one final round, 3 total maximum. Then stop and report any residual single-persona concerns rather than looping forever.

### Step 7 : Style pass and finalize
1. Run the `sense-of-style` skill (or its rubric) on the final text. Target all dimensions at 8 of 10 or higher; fix what is cheap.
2. Final em-dash and AI-tells sweep.
3. File the finalized letter into the application packet folder `applications/<Company> - <Role>/` as `cover-letter.md`, alongside the JD and resume for that job. Offer to render a PDF from `templates/cover-letter.html`.
4. Drop a copy into this skill's `examples/` as `<company>-<role-slug>.md` and add a line to `examples/README.md` (the growing pattern bank).
5. Report the final scorecard delta across rounds.

## Anti-patterns (do not ship these)
- Restating the resume in prose. The reader already has it.
- Generic mission language ("I'm passionate about your mission"). Evidence or cut it.
- Coordination described as impact ("I coordinated across 5 teams"). Name a decision and its cost instead.
- Volume brags ("most aggressive AI user you'll find"). Show a built thing and its result.
- Fake metrics ("measurably improved"). A number, or describe the mechanism; never "measurably" with no measure.
- Em-dashes. Tricolons on autopilot. Bold lead-in bullets. Negative parallelism ("not X, but Y").
