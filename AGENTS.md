# AGENTS.md

Instructions for running `ai-talent-partner` from Codex, Cursor, or any agent that is not Claude Code.
Everything here is plain files. The "skills" in `skills/` are markdown playbooks; read the relevant one
and follow it. There is no Claude-Code-only magic. Where a step says "use AskUserQuestion", just ask the
user the same questions inline and wait for answers.

## Orientation
Read `README.md` first, then `config/config.example.json` and the `config/*.example.md` files. The user's
real config lives in `config/config.json`, `config/companies.txt`, and `config/terms.md`; their profile.md
(config key `profile_file`) and about-me.md (the accomplishment bank; config key `accomplishment_bank`)
live in the workspace, not the repo. All of it is gitignored and personal; the `.example` versions are the schema.

## The workspace (create this during setup)
This repo is code. The user's personal data lives in a separate workspace folder they choose. During
setup you MUST ask where they want it (default `~/job-search`), set `workspace_root` in config.json,
and scaffold this structure (full details in `docs/WORKSPACE.md`):

```
<workspace_root>/
  about-me.md          the accomplishment bank: every accomplishment, tagged, source of truth for all materials
  profile.md           who they are and what they want
  master-resume.html   base resume, styled from templates/resume.html, filled from about-me.md
  jobs.csv             the tracker sheet (CSV backend only)
  applications/<Company> - <Role>/   jd.md, resume.md, cover-letter.md, application-questions.md
```

Point the config keys `accomplishment_bank`, `profile_file`, `applications_dir`, and `csv_path` inside
this folder. Never write the user's personal data into the repo. Starter company lists are in
`config/seed-companies/` (defense, robotics, ai); offer them and note the user can add any industry.

## First-time setup
Follow `skills/setup/SKILL.md` end to end. It tells you what to ask, what files to write, how to create the
spreadsheet (Google Sheets or local CSV), and how to install the schedulers. Step 4 hands off to
`skills/accomplishment-interview/SKILL.md`, which builds the accomplishment bank. Do that one carefully; it is
the source of truth for every resume and cover letter.

## The finder (runs on a schedule)
`scripts/run_finder.sh` is the entry point. (Board detection happens earlier: `scripts/resolve_ats.py`
runs at setup and caches to `state/companies.resolved.json`; re-run it when companies are added.) It:
1. runs `scripts/poll.py` (hits each company's Greenhouse/Lever/Ashby board, filters by `config/terms.md` and the config.json `filters` block, drops already-tracked URLs, writes candidates),
2. runs the generation pass that judges candidates, does the web-search shard for non-ATS companies, de-dupes against the sheet, and appends new rows,
3. runs `scripts/check_live.py` to drop closed/dead postings (removed rows are tombstoned to `state/removed.json` first),
4. runs `scripts/backfill_dates.py` to fill missing post dates,
5. sorts the sheet by post date.

The model-driven step (judging + web shard + writing rows) is defined as a plain prompt in
`prompts/finder.md`. The runner invokes it through the config key `agent_command` (default `claude -p`).
For Codex or another CLI, set `agent_command` to your headless invocation and the prompt is piped to it on
stdin. If your tool has no headless mode, leave the schedulers off and run the prompt yourself against the
candidate files, then append results through `scripts/sheet_io.py`.

## The generator (runs a few times a day)
`scripts/run_apply.sh` is the entry point. It:
1. runs `scripts/apply_scan.py` to find sheet rows marked "Yes" that have no materials yet,
2. for each, runs the prompt in `prompts/apply.md`: it produces a tailored resume (from `skills/resume-customizer`),
   a cover letter (from `skills/cover-letter`), and an `application-questions.md` answering the posting's
   substantive free-text questions. Each writing pass runs the `skills/sense-of-style` check at least once.
3. runs `scripts/apply_mark.py` to mark fully-generated jobs done.

Output goes to `<workspace applications_dir>/<Company> - <Role>/`. Nothing is submitted.

## The Yes/No loop
Tell the user: the finder fills the sheet; they type "Yes" in the "Will I apply?" column for jobs they want;
the generator writes materials for those. It only generates once per job, tracked by URL in
`state/generated.json`. This is the core workflow.

## Sheet I/O
`scripts/sheet_io.py` abstracts the backend. With `backend: csv` it reads/writes the workspace `jobs.csv` (config `csv_path`). With
`backend: google_sheets` it uses the Google Sheets API (see `docs/SETUP.md` for the one-time auth). Use it for
all reads/writes/appends/deletes so the rest of the code does not care which backend is active.

## Hard rules
- Never invent the user's accomplishments or numbers. Trace everything to their bank or their answers.
- Never auto-submit an application.
- Keep the user's real `config/*` files local; never commit them.
