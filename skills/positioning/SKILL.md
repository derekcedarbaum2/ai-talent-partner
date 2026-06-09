---
name: positioning
description: Builds the user's positioning narrative and master resume after the accomplishment bank exists. Interviews briefly for the career throughline, the kind of problem they own, and their wedge, then writes profile.md (positioning statement, short bio, resume "About" line) and fills templates/resume.html into master-resume.html as the full superset base resume. Trigger phrases include "positioning", "build my bio", "master resume", "positioning narrative", "/positioning", or being invoked by the setup skill after the accomplishment interview.
---

# Positioning and Master Resume

You make the user's materials sound like a person, then build the base resume every tailored
version starts from. This runs AFTER the accomplishment-interview skill has produced the workspace
about-me.md (the accomplishment bank; path = config key accomplishment_bank). That file is your
primary source. Read it in full before you ask anything. Never invent: every claim, number, and
detail you write traces back to about-me.md or to the user's direct answers in this session.

You produce two artifacts:
1. profile.md in the workspace (path = config key profile_file): the positioning narrative.
2. master-resume.html in the workspace: the full superset base resume, styled from templates/resume.html.

If you are running in Claude Code, use the AskUserQuestion tool for the structured questions below.
In Codex or another agent without that tool, ask the same questions inline, one cluster at a time,
and wait for answers.

## Step 0 : Read the source

Read the workspace about-me.md end to end. Note the strongest throughline (the "spine" theme the
accomplishment interview usually marks), the recurring kind of problem the user is hired to solve,
the biggest quantified outcomes, and the "Fixed facts" block (education, contact, clearances).
Also read the workspace profile.md if one already exists, and config/terms.md if present, so the
positioning matches the target titles and industries the user chose at setup. Do not interview from
a blank page. Come in with a draft thesis the user can react to.

## Step 1 : The positioning interview (brief)

Keep this tight. You already have the raw material; you are confirming the frame, not re-collecting
facts. Ask three things, each with a draft answer pulled from about-me.md so the user reacts instead
of recalling cold:

1. Throughline. State the career throughline you read from the bank in one sentence, and ask if it
   lands. Offer two or three candidate framings if the bank supports more than one. Example shape:
   "I read your spine as: you take 0-to-1 products from prototype to a real revenue line. Is that the
   story, or is it more the platform-scaling story?"
2. The problem they own. Name the specific kind of problem they get hired to solve, drawn from the
   most repeated theme in the bank, and confirm or correct it.
3. The wedge. The thing that makes them the obvious pick for their target roles versus a generic
   candidate. Propose one from the strongest differentiated accomplishments and let them sharpen it.

Ask at most one or two follow-ups to resolve a contradiction or a thin spot. Then stop. This is a
short interview by design.

## Step 2 : Draft the positioning narrative

Write three pieces, all in the user's voice (match the voice/tone notes in about-me.md or profile.md
if present):

- Positioning statement: one paragraph. The throughline, the problem they own, the wedge, and a
  proof point or two with real numbers from the bank. This is the spine of every cover letter opener.
- Short bio: three to five sentences. A human, readable version usable on LinkedIn, a portfolio, or
  an intro email. Same facts, looser register.
- Resume "About" line: one to three sentences, dense, number-forward. This becomes the About section
  on the resume. Model the density on the sample About paragraph in templates/resume.html.

Everything here must trace to about-me.md or the interview. No new claims, no rounded-up numbers.

## Step 3 : Run sense-of-style on the narrative (at least once)

Run the sense-of-style skill on the positioning narrative (at minimum the positioning statement and
the About line) before you write the file. Apply its rewrites. This is mandatory: the whole point of
this skill is that the materials read like a person, and sense-of-style is the check for that. Run it
again if the first pass still reads soft.

## Step 4 : Write profile.md

Write the workspace profile.md (config key profile_file). Use config/profile.example.md as the
schema: Identity, What you want, Positioning (one paragraph), Notes for the writer. Fill Identity and
What you want from about-me.md plus config/terms.md. Put the polished positioning statement in the
Positioning section. Add the short bio and the resume "About" line as their own labeled blocks so the
downstream resume-customizer and cover-letter skills can pull them directly. Keep voice/tone notes
and anything sensitive-to-keep-vague in Notes for the writer.

## Step 5 : Build master-resume.html

Build the workspace master-resume.html by filling templates/resume.html.

- Keep the entire head and the CSS verbatim. Do not touch the `<style>` block, fonts, or `:root`
  tokens. The user can restyle later; your job is content, not design.
- Replace the body content with the user's FULL resume, drawn from about-me.md and profile.md. This
  is the master: a superset that the resume-customizer skill later trims and tailors per job. Include
  more than fits on one page if the bank supports it. Breadth here is the point.
- Map the bank into the template structure: the resume "About" line into the About section; each role
  as a role block with company, location, dates, a one-line lede, and the role's accomplishments as
  did-X, resulting-in-Y, outcome-Z bullets with the key numbers in `<strong>`; a Skills block grouped
  by competency; and Education plus Fixed facts from the bank.
- Preserve the writing style the template demonstrates: every bullet is an action with a result and a
  quantified outcome, numbers bolded, no filler. Label estimates as estimates if the bank does.
- Never invent. If a role, number, or fact is not in about-me.md, it does not go in the resume. If the
  bank flags open facts still to collect, leave those out rather than guessing.

## Rules

- Source of truth is about-me.md. Everything traces to it or to the user's answers this session.
- Run sense-of-style on the narrative at least once and apply the fixes.
- Keep the template head and CSS verbatim; only the body content changes.
- Write to the workspace, never into the repo. profile.md and master-resume.html both live in the
  workspace folder (config keys profile_file and workspace_root). Personal data never gets committed.
- Keep the user's voice, and keep sensitive material (employer IP, confidential work) at a safe altitude.
- This skill is re-runnable. On a later run, re-read about-me.md, refresh the narrative, and rebuild
  master-resume.html so it reflects new accomplishments.
