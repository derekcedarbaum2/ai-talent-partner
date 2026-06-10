# How it works

The design principle: push the deterministic work into plain Python and use the model only for
judgment and writing. About 85% of every run is code (fetch, filter, de-dupe, liveness, sheet I/O),
which keeps it fast and cheap to run on a schedule.

## The finder (scripts/run_finder.sh)

One step runs at setup, not per run: resolve_ats.py detects, per company, whether it hosts jobs on
Greenhouse, Lever, or Ashby, and caches the board token to state/companies.resolved.json. Most
startups do; those get polled directly. Re-run it whenever you add companies to companies.txt.

Each scheduled run then does:
1. poll.py hits each pollable board's free JSON API, keeps titles that match config/terms.md, applies the hard filters from config.json's `filters` block (location, experience ceiling, salary floor, per-company rules), drops URLs already tracked in the sheet, and writes the survivors to state/candidates.json. It also rotates a slice of the non-ATS companies into state/web_shard.json.
2. The model step (prompts/finder.md) judges the candidates, runs a capped web search for the web-shard companies, verifies each web URL is a live posting, de-dupes against the sheet, and appends new rows through scripts/sheet_io.py.
3. check_live.py removes rows whose posting has closed, tombstoning each removed row to state/removed.json before deleting it. It checks at the source: Greenhouse and Lever single-job APIs return 404 on dead jobs; Ashby is a single-page app that serves a 200 for expired jobs, so it is checked through Ashby's GraphQL endpoint (a null jobPosting means dead); Workday serves a 200 shell too, so it is checked through the CXS API. Custom sites are checked for a hard 404.
4. backfill_dates.py fills in missing post dates for rows that landed without one.
5. sort_sheet.py sorts by post date, newest first.

## State files (state/, gitignored)
- state/candidates.json : filtered candidates from the latest poll, input to the model step.
- state/web_shard.json : this run's slice of non-ATS companies for the capped web search.
- state/shard_idx : rotation cursor for the web shard.
- state/apply_queue.json : Yes rows awaiting generation, written by apply_scan.py.
- state/generated.json : URLs of jobs already generated. Delete a URL here plus its folder to force a regen.
- state/companies.resolved.json : the ATS cache. Delete it and re-run resolve_ats.py to refresh.
- state/removed.json : tombstones of rows check_live deleted, in case you want one back.

## The generator (scripts/run_apply.sh)
1. apply_scan.py reads the sheet, finds rows marked "Yes" that have no materials yet, and writes a queue.
2. The model step (prompts/apply.md) builds, per job: a tailored resume (skills/resume-customizer), a cover letter (skills/cover-letter), and application-questions.md answering the posting's substantive questions. Each writing pass runs skills/sense-of-style at least once. Everything traces to your about-me.md (the accomplishment bank in your workspace); nothing is invented.
3. apply_mark.py marks a job done once all three files exist, by recording its URL in state/generated.json, so it is never regenerated.

## Why the spreadsheet is the interface
The sheet is the one surface a human touches. The finder writes to it, you mark "Yes", the generator reads
it. Keeping the control in a spreadsheet means you can curate from your phone, share it, and never have to
learn the internals. sheet_io.py makes the backend (CSV or Google Sheets) invisible to the rest of the code.

## What the model is and is not used for
Used for: judging whether a fuzzy title or borderline posting really matches, the web-search shard, and
writing the application materials. Not used for: the bulk fetch, filtering, de-dupe, liveness, or sheet
writes. That split is what makes a six-times-a-day schedule affordable.
