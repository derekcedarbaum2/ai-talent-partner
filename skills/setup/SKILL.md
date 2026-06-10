---
name: setup
description: First-run onboarding for ai-talent-partner, and the master orchestrator for the whole setup flow. Runs when someone clones the repo and opens it with Claude Code or Codex. Interviews the user, builds their config, company list, and match terms, sets up the spreadsheet, runs the accomplishment-interview skill (about-me.md) and the positioning skill (profile.md narrative plus master-resume.html), installs the schedulers, and explains the Yes/No loop. Each sub-skill can also be run standalone later. Trigger phrases include "set up", "setup", "get started", "onboard", "/setup", "initialize", or opening a freshly cloned repo.
---

# ai-talent-partner : Setup

You are onboarding a new user of `ai-talent-partner`, a self-hosted AI job-search agent.
By the end they have: a configured tracker that finds matching jobs on a schedule, a spreadsheet
they curate, and an auto-generator that writes a tailored resume, cover letter, and application
answers for any job they mark "Yes". Be efficient and concrete. Do real work, not just explanation.

## This skill is the master orchestrator

Setup is the conductor for the whole onboarding. Running it runs the entire flow in order, calling
the sub-skills at the right step. Each sub-skill also stands alone: the user can re-run any of them
later (after a new win, a pivot, a restyle) without re-running all of setup. The order is:

1. Orient on the schema (Step 0).
2. Choose and scaffold the workspace (Step 0.5).
3. Gather raw material and preferences, the interview (Step 1).
4. Build config, companies, and terms (Step 2).
5. Set up the spreadsheet (Step 3).
6. Run the accomplishment-interview skill, which builds about-me.md (Step 4).
7. Run the positioning skill, which builds profile.md (the narrative) and master-resume.html (Step 5).
8. First run and install the schedulers (Step 6).
9. Explain the Yes/No loop (Step 7).

Run them in this order. The accomplishment bank feeds positioning, and both feed the first generation
pass, so do not skip ahead.

If you are running in Claude Code, use the AskUserQuestion tool for the structured choices below.
If you are in Codex or another agent without that tool, ask the same questions inline, one cluster
at a time, and wait for answers.

## Step 0 : Orient
Read `README.md`, `config/config.example.json`, `docs/WORKSPACE.md`, and the three `config/*.example.md`
files so you know the schema you are filling. Confirm `python3` and (for Claude Code) the `claude` CLI exist.

## Step 0.5 : Choose and scaffold the workspace
Ask the user where they want their personal job-search folder to live (default `~/job-search`). This is
separate from the repo: it holds their data, not the code. Create the structure from `docs/WORKSPACE.md`:
`about-me.md`, `profile.md`, an `applications/` folder, and `jobs.csv` if they pick the CSV backend.
Set `workspace_root` in `config/config.json` and point `accomplishment_bank` (to `about-me.md`),
`profile_file`, `applications_dir`, and `csv_path` inside it. Never write personal data into the repo.

## Step 1 : Interview the user, gathering raw material first
Ask for source material up front, because everything downstream is better when seeded from real
documents instead of cold recall. Read or fetch everything they provide; it seeds the bank.

1. Existing resume(s): ask for the file path(s) or pasted text. Accept PDF, docx, md, txt.
2. Existing cover letter(s), if any: path or paste.
3. LinkedIn: the profile URL, or a screenshot / exported PDF if the profile is private.
4. Portfolio / personal site / GitHub: URLs. For GitHub, ask whether to scan pinned repos for project proof.

Then the structured preferences (AskUserQuestion clusters):

- Spreadsheet backend: Google Sheets (shareable, needs Google auth once) versus local CSV/Excel (zero auth). See Step 3.
- Target roles / titles: the exact titles they would take. Push for SPECIFIC real titles, not "any PM role", but do NOT over-constrain. Include obvious variants and adjacent titles so good roles are not missed. A good list is roughly 6 to 15 titles plus a short exclusions list.
- Target industries: the sectors to build the company list from.
- Target geographies and remote preference: metros, regions, "US-only", "remote ok".
- Hard constraints: salary floor, seniority ceiling (for example "nothing requiring 10+ years"), companies to special-case, anything to exclude.

When helping with titles and keywords, coach them. Too narrow ("Director of AI Product Management, Defense")
misses real matches; too broad ("Manager") drowns them in noise. Aim for the middle and let the filters do the rest.

## Step 2 : Build the config artifacts
Write these into `config/` (the real files, not the `.example` ones):

- The workspace `profile.md` was stubbed in Step 0.5. Capture the raw preferences from the interview into it now (titles, industries, geographies, constraints); the positioning skill in Step 5 rewrites it into a polished narrative. Do not create a second profile in the repo.
- `config/terms.md`: the title list, exclusions, and a human-readable "Hard filters" section mirroring the filters below. Mirror the format in `config/terms.example.md`. This section is documentation only; the enforced filters live in config.json.
- The `filters` block in `config/config.json`: this is the single enforced source of hard filters (`scripts/poll.py` reads only this), so write it explicitly from the interview answers. Set `experience_ceiling_years` plus `experience_ceiling_field` from the seniority ceiling (and the secondary years/field pair if they gave a domain floor like "5+ years SaaS", else null both), `salary_floor_usd` from the salary floor (null if none), `us_only` from the geography answer, and `company_location_rules` from any company special-cases. Null out or remove every unused example rule, including the ExampleCorp placeholder; never ship a filter the user did not choose. Write the terms.md "Hard filters" mirror in this same step so the two never drift.
- `config/companies.txt`: build the list. Starter lists ship in `config/seed-companies/` (defense, robotics, ai). These seed lists are broad on purpose: they serve many professions, not just one. Software engineers, mechanical engineers, hardware engineers, and other roles all hire across these same defense, robotics, and AI companies, so a wide list is a feature, not noise. Do NOT push the user to trim. Tell them the seed lists exist and that they can keep them in full and let the title-match terms plus the hard filters (location, experience ceiling, salary floor) do the work of finding signal, or trim if they prefer a tighter set. Either is fine. Make clear they can add any industry they want. For industries the seed lists do not cover, use web search to find companies in their target industries and geographies, prioritizing actively-hiring firms. For each company, prefer the `ats:provider:token` form by checking for a Greenhouse/Lever/Ashby board; fall back to the homepage URL. Aim for a real starter set (50 to a few hundred). Tell the user the count and that they can edit the file anytime.
- `about-me.md` (the accomplishment bank, in the workspace): hand off to the accomplishment-interview skill in Step 4. Do not build it inline.
- `config/config.json`, from `config/config.example.json`, with backend, paths, schedules, and applications_dir set.

## Step 3 : Set up the spreadsheet
The tracker writes one row per found job with these columns, A to H:

`Date Found | Company | Job Title | Location | Posted | Job URL | Source | Will I apply?`

Column H ("Will I apply?") is the control. The user marks Yes and the generator builds their materials.

- CSV/Excel backend: create `jobs.csv` in the workspace (the `csv_path` you set) with that header row. Done.
- Google Sheets backend: create a new sheet (or use one they provide), set the header row, and put its ID in `config.json`. This needs Google auth once. In Claude Code, use a connected Google Drive/Sheets MCP if present, otherwise walk them through creating a sheet, pasting the ID, and the one-time OAuth that `scripts/sheet_io.py` uses. See `docs/SETUP.md`.

## Step 4 : Build the accomplishment bank
Invoke the accomplishment-interview skill. It ingests the resume, LinkedIn, and portfolio from Step 1,
drafts a bank, then interviews the user to fill gaps and quantify outcomes (did X, resulting in Y,
outcome Z). This is the single highest-leverage artifact: every tailored resume and cover letter draws
from it. Do not skip it.

## Step 5 : Build the positioning narrative and master resume
Invoke the positioning skill. It runs after the accomplishment bank exists and reads about-me.md as its
source. It interviews the user briefly for the throughline of their career, the kind of problem they own,
and their wedge, then writes two artifacts into the workspace: profile.md (config key profile_file), which
holds the positioning statement, a short bio, and the resume "About" line, and master-resume.html, the full
superset base resume styled from templates/resume.html. master-resume.html is what the resume-customizer
skill later trims and tailors per job. The positioning skill runs sense-of-style on the narrative so the
materials read like a person. Do not build these inline; hand off to the skill.

## Step 6 : First run and scheduling
- Resolve ATS boards: `python3 scripts/resolve_ats.py`, then report how many companies are on pollable boards versus the web path.
- Do one finder run now: `python3 scripts/poll.py` then the generation/append step, so the user sees rows appear.
- Install the schedulers. On macOS, copy the example plists in `launchd/` (filling in the repo path) and load them with `launchctl load`. On Linux, add the two cron lines from `docs/SETUP.md`. Explain that the finder runs every ~4h and the generator a few times a day.

## Step 7 : Explain the Yes/No loop (the core workflow)
Tell the user plainly: every few hours the finder adds new matching jobs to their sheet. They open it,
skim, and in the "Will I apply?" column type Yes for any they want to pursue (blank or No otherwise).
The next time the generator runs, it produces a tailored resume, cover letter, and answers to the
posting's substantive questions for every Yes row, into `<applications_dir>/<Company> - <Role>/` in their workspace. Review,
finalize, send. Point them at README.md for the same instructions and at `config/` for everything they can tune.

## Rules
- Never invent the user's accomplishments or numbers. Everything traces to their source material or their answers.
- Keep their real `config/*` files local (gitignored). Only `.example` files are committed.
- If a tool is missing (no Google MCP, no headless model), degrade gracefully and explain the manual step.
- Be concrete and finish the job. By the end, a finder run has produced rows and the user knows the loop.
