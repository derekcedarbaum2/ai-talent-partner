---
name: resume-customizer
description: Tailor your resume to a specific job by selecting and reweighting accomplishments from your bank, aligning to the JD and ATS, then stress-testing with a 3-persona panel before a diff-approval gate and a rendered PDF. Reads the job title and job description, picks the most relevant bullets (never invents), matches the headline to the exact title. Trigger phrases include "customize my resume", "tailor my resume", "resume for [company/role]", "/resume-customizer", "ATS-optimize my resume".
---

# Resume Customizer

Tailor the resume to one job. Tailoring means selecting, reweighting, and truthfully rephrasing accomplishments from the bank to match the JD and pass ATS. It is never invention. A resume lie is fireable, so a truthfulness gate and a diff-approval checkpoint are mandatory.

## Operating principles

- Source of truth is the bank: your about-me.md (the accomplishment bank in your workspace; path = config key accomplishment_bank). Every bullet on the tailored resume traces to a bank entry. If a tailored bullet has no bank source, it is fabrication. Cut it, or ask the user to add the fact to the bank first.
- Moderate tailoring: reorder and reweight bullets, align keywords to the JD, and truthfully rephrase bullets and the summary to mirror JD language. The headline matches the exact job title. Do not heavily rewrite into claims the bank does not support, and do not leave the resume untouched.
- Fixed facts never change: companies, dates, titles held, education, clearance, contact. Tailoring touches emphasis, ordering, summary, skills, and bullet phrasing, not history.
- Voice and hard gates live in `references/resume-writing-rules.md`. No em-dashes. No fabricated metrics. Quantified outcomes over responsibilities.
- One page unless the role clearly warrants two. Cut the weakest-fit bullets first.

## Architecture

The orchestrator does selection and tailoring because it holds the bank plus the JD. The 3-persona panel runs as parallel sandboxed subagents so their reasoning stays out of the orchestrator's context. Fixes apply on convergence, meaning two or more personas agree, bounded to 3 rounds. The diff-approval gate is the resume-specific addition: no PDF until the user signs off on what changed and why. This mirrors the `cover-letter` skill's pattern.

## Pipeline

### Step 0 : Load
1. Job title and job description. Standing intake: read `applications/<Company> - <Role>/jd.md`. If the user names an existing application folder, use its `jd.md`. If they paste text or give a URL, scaffold the folder and save `jd.md` first, then proceed. Outputs are written back into this same packet folder, which is shared with `/cover-letter` so one JD drives both.
2. Accomplishment bank: your about-me.md (the accomplishment bank in your workspace; path = config key accomplishment_bank).
3. Base resume template: `templates/resume.html`. The HTML is the render source. Preserve its structure and styling; you are filling it, not redesigning it.
4. Personas: see Step 4. Use whatever reader-persona reference your harness provides, or assemble the default panel below from the JD itself.
5. Rules: `references/ats-rules.md`, `references/resume-writing-rules.md`.

### Step 1 : Analyze the JD
Extract the exact job title (for the headline), the role's core competencies ranked, the must-have keywords and skills (for ATS), seniority, domain, and any explicit bets. Build a JD-competency to bank-entry map: for each top competency, list which bank accomplishments prove it.

### Step 2 : Interview the user (AskUserQuestion, only when there is a real gap)
If the JD needs a fact the bank flags as open (for example a number), or positioning is ambiguous, ask: which accomplishments to lead with, target-title preference, any emphasis or de-emphasis, and any missing number. Add new facts to the bank, not just to this resume. Skip this step if the bank already covers the JD cleanly. In a headless run, make the reasonable call and proceed; never invent a number to fill a gap.

### Step 3 : Tailor
- Headline: set it to the exact job title from the posting.
- Summary: rewrite the "About" to foreground the JD's core competencies, truthfully, in the user's voice.
- Bullet selection: choose the highest-relevance bank entries per competency. Cut weak-fit bullets to hold one page. Order each role's bullets by JD relevance, strongest first.
- Keyword alignment: weave must-have JD terms into bullets where truthful, mirroring the JD's words for the same thing the user actually did. Reorder the Skills section to surface JD-matched skills first.
- Edit a copy of `templates/resume.html`. Keep the single-column, ATS-safe structure and the white background.
- Run the em-dash, AI-tells, and one-page sweep.

### Step 4 : Panel (parallel, sandboxed) plus ATS check
Spawn the 3 personas in one message. Default panel: a recruiter or ATS screen, a technical-leader archetype (overclaim and credibility detector), and a product-or-domain-craft archetype (outcome versus activity). Borrow recognizable industry standards for the lens diversity. Each returns a verdict, a scorecard, and top fixes. Separately, run a mechanical ATS keyword-coverage check: list the JD's must-have terms and mark whether each appears truthfully on the resume.

### Step 5 : Synthesize, fix, re-panel
Apply fixes where two or more personas agree. Single-persona flags are judgment calls. Fixes that need a fact you lack go back to the user; never invent. Re-panel if a convergent blocker remains, 3 rounds maximum.

### Step 6 : Diff-approval gate (MANDATORY, no PDF before this)
Show the user a clear before-to-after diff: every change versus the base, grouped (headline, summary, reordered bullets, rephrased bullets, dropped bullets, skills), each with a one-line why and the bank entry it traces to. Include a truthfulness attestation: every bullet traces to the bank, nothing invented. Wait for explicit approval, then apply any edits the user asks for. In a headless run with no human, skip the wait but still emit the diff and attestation to the output folder, and mark the file an auto-generated draft for review.

### Step 7 : Render and file
1. Render the PDF from the tailored HTML via headless Chrome (white background).
2. File into the application packet folder `applications/<Company> - <Role>/` as `resume.html` plus `resume.pdf` plus `resume.md`, alongside the JD and the cover letter for that job.
3. Report the panel scorecard, the ATS coverage, and the diff summary.

## Anti-patterns (do not ship)
- A bullet with no bank source, which is fabrication.
- Changing dates, titles, or companies to fit the JD.
- Keyword-stuffing untruthfully, or stacking every bullet with the same opener verb.
- Responsibilities instead of quantified outcomes.
- Skipping the diff-approval gate when a human is available.
- Em-dashes, AI-tell vocabulary, or multi-column and table layouts that break ATS parsers.
