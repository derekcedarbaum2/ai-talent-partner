---
name: accomplishment-interview
description: Builds or enriches the user's accomplishment bank, the single source of truth every tailored resume and cover letter draws from. Seeds from the user's real material (resume, LinkedIn, portfolio, GitHub), drafts a bank, then interviews to fill gaps and quantify outcomes into did-X / resulting-in-Y / outcome-Z, tagged for per-job retrieval. Trigger phrases include "accomplishment interview", "build my bank", "accomplishment bank", "/accomplishment-interview", or being invoked by the setup skill.
---

# Accomplishment Interview

You build your about-me.md (the accomplishment bank in your workspace; path = config key accomplishment_bank): the canonical, tagged list of the user's accomplishments
that the resume and cover-letter skills select from per job. Quality here sets the ceiling on every
downstream artifact. The core principle: seed from real material first, interrogate for gaps second.
Never interview from a blank page, and never invent.

## Step 1 : Ingest the source material (seed)
Gather and read everything available: existing resume(s), cover letter(s), LinkedIn (URL or screenshot
or exported PDF), portfolio / personal site, and GitHub (READMEs of pinned repos are good project proof).
The setup skill usually passes these in; if not, ask for them. Extract a first-draft list of accomplishments
straight from this material. This draft is what you interrogate, so the user reacts instead of recalling cold.

## Step 2 : Draft entries in the standard shape
For each accomplishment, draft an entry with these fields:

- title: a short handle for the accomplishment.
- x: what the user did (the action, their real contribution, "co-" honest if it was a team effort).
- y: the direct result.
- z: the outcome, quantified wherever a number exists (revenue, %, time, scale, count, dollars).
- contribution: what THEY did versus the team, so the resume can avoid borrowed-credit claims.
- tags: facets the resume customizer selects on. Include competency (for example 0-to-1, growth, platform, GTM, technical, leadership, AI), domain/industry, scope (team size, budget, dollar impact, number of stakeholders), and the source role/company.
- confidence: verified, estimate, or unverified. Mark estimates as estimates; never present them as measured.

## Step 3 : Interrogate for gaps and numbers (the interview)
Walk the draft and find the holes: claims with no number, vague scope, missing contribution, thin areas.
Then ask targeted questions. Use AskUserQuestion in Claude Code (or inline questions in Codex), and follow
two rules that make recall easy and honest:

- Give the user something to react to. Offer concrete buckets (for example "cut failures ~50% / ~75% / ~90%+")
  plus an "I have the exact figure" option, rather than a blank "what was the number?". People recall against
  options far better than from nothing.
- Force the quantified Z, but allow "no defensible number, keep qualitative". The quantified outcome is the one
  thing that cannot be reconstructed later, so prioritize extracting it now. When a number is a rough estimate,
  record it and label it an estimate.

Also probe scope (team size, budget, timeline, stakeholders) because it is easy to forget verbally and resumes
need it. And ask about breadth beyond the obvious one or two roles (side projects, consulting, open-source,
earlier career) if those matter for the user's target roles.

## Step 4 : Write the bank
Write your about-me.md (the accomplishment bank in your workspace; path = config key accomplishment_bank). Open with the rules: this is a superset (more than fits on one page,
tailoring means selecting and reweighting, never inventing); every entry carries the real contribution and a
number where one exists; mark estimates as estimates; keep sensitive material vague. Group entries by theme
(for example a "spine" theme for the user's strongest throughline, then GTM, leadership, technical, AI, and so on).
End with a "Fixed facts" block (education, contact, clearances, anything that never changes) and an
"Open facts to collect" block listing the numbers still missing, so a future run knows exactly what to chase.

## Step 5 : Make it re-runnable
This skill appends over time. On later runs, read the existing bank, add new accomplishments, and resolve
open facts rather than rewriting from scratch. Encourage the user to re-run it after a notable win.

## Rules
- Never fabricate accomplishments, titles, dates, or metrics. Everything traces to source material or the user's answers.
- One canonical bank. Do not create competing copies; the resume and cover-letter skills read this exact file.
- Estimates are labeled estimates. Quantified-if-possible must never become quantified-if-invented.
- Keep the user's voice and keep sensitive material (employer IP, confidential work) at a safe altitude.
