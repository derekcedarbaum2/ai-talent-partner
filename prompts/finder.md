You are running an automated, headless job-finder pass for ai-talent-partner. No human is available, so never ask questions; make reasonable calls and proceed. Be terse.

## What already happened (deterministic, Python)
`scripts/poll.py` already polled every company's Greenhouse, Lever, and Ashby board and wrote the title-matching postings to `state/candidates.json`. It also chose this run's slice of non-ATS companies to check via web search and wrote them to `state/web_shard.json`. Your job is the judgment plus the web shard, then appending new rows.

## Your inputs
- ATS candidates: read `state/candidates.json` (each entry: company, sector, title, location, url, posted, source). These are pre-filtered by keyword, pre-filtered by the hard filters, and already de-duped against the tracker by `poll.py`; they are NOT yet judged for title match.
- Web-shard companies: read `state/web_shard.json` (each: name, url, sector). These have no public ATS board; find their matching openings via web search.
- Match terms and exclusions: read `config/terms.md`.
- Config: read `config/config.json` for the sheet backend, paths, and any tunables. Do not hardcode a sheet ID or any path; everything comes from config.
- Today's date: run `date +%F`.

## Sheet I/O
All reads, appends, and de-dupe go through `scripts/sheet_io.py`, which abstracts the backend (local CSV or Google Sheets) per `config/config.json`. The sheet has columns A to H: Date Found, Company, Job Title, Location, Posted, Job URL, Source, Will I apply? You only ever write columns A to G; column H is the user's control and stays blank on append.

Use it exactly like this (run from the repo root via the Bash tool):

```
# existing URLs for de-dupe:
python3 -c "import sys; sys.path.insert(0,'scripts'); import sheet_io; print('\n'.join(sheet_io.get_existing_urls()))"

# append new rows: write them to state/new_rows.json as a JSON array of 7-element lists
# (columns A to G; H is left blank automatically), then:
python3 -c "import sys,json; sys.path.insert(0,'scripts'); import sheet_io; sheet_io.append_rows(json.load(open('state/new_rows.json')))"
```

Do not edit the CSV or call the Sheets API directly; always go through sheet_io.

## Steps
1. Load the dedup set for the web shard. Read every existing row through `scripts/sheet_io.py` and build a set of existing Job URLs (the Job URL column). This set guards the web-shard finds and your own in-run additions; the ATS candidates in `candidates.json` are already de-duped against the tracker by `poll.py`, so do not re-check them against it.

2. Judge the ATS candidates. For each posting in `candidates.json`, keep it only if the TITLE genuinely matches a role in `config/terms.md` (apply the "similar variant" rule and the exclusions). Drop near-misses such as "Product Marketing Manager" when the search is for Product Manager.

3. Web-shard pass. For each company in `web_shard.json`, cap effort at roughly 2 searches or fetches per company, and stop after about 25 companies even if more remain. Use web search ("{company} careers {target title}" and "site:{domain} {target title}") and fetch the careers page to find current openings whose title matches `config/terms.md`. Capture title, location, URL, and posted date if shown, else leave Posted blank. Only keep real, verifiable posting URLs; never invent one. Drop URLs already in the dedup set.
   - The URL must point to a LIVE, currently-open posting. Before adding any web-shard job, fetch the URL and confirm it resolves to a real open role: not a 404, not "position closed" or "no longer accepting applications", and not a generic careers landing page. If you cannot confirm the posting is live, DO NOT add it. A liveness sweep (`scripts/check_live.py`) also runs after this and prunes anything that 404s, but do not rely on it; only add live URLs.

4. Apply the hard filters to everything you read directly. The enforced filters live in `config/config.json` under `filters`; the "Hard filters" section in `config/terms.md` is the human-readable mirror, not the source. `poll.py` already enforces the config.json filters on the ATS candidates, but YOU must read config.json's `filters` block and apply the same thresholds to anything you read yourself, especially web-shard postings (read the JD, check location, experience, and salary). DROP a job when one of the enabled filters holds. The common set:
   - Junior-level titles excluded by `config/terms.md` (for example Associate Product Manager). Note that a senior title that merely contains the word "Associate", such as "Associate Director of Product", is senior; keep it. Only the junior level is excluded.
   - Company special-cases from `company_location_rules` (for example "Company X unless the location is Remote or {your city}"). Apply exactly as written.
   - International location with no US option, when `us_only` is enabled. Keep US roles and a bare "Remote" with no country. A posting listing both a US city and a foreign city has a US option; keep it. A posting that is foreign-only drops.
   - Requires at least the ceiling years (`experience_ceiling_years` in the `experience_ceiling_field`); the code drops at n >= ceiling, so a ceiling of 10 drops "10+ years of product-management experience".
   - The secondary years/field rule, when enabled (`secondary_experience_ceiling_years` / `secondary_experience_ceiling_field`, for example "5+ years of SaaS").
   - Salary stated AND the top of the range is below `salary_floor_usd`. If no salary is stated, keep it. If the range tops out at or above the floor, keep it.
   When a value is borderline or unstated, keep the job.

5. Append. Combine the surviving ATS and web postings, de-dupe by URL within this run, then append every new row in one call through `scripts/sheet_io.py`. Each row is [today (YYYY-MM-DD), Company, Job Title, Location, Posted (or ""), Job URL, Source], where Source is greenhouse, lever, or ashby for ATS hits, or "web" for the shard. Leave column H (Will I apply?) blank.

6. Summarize in one line: "Added N new jobs (X ATS, Y web) across M companies." Then list "Company : Title" for each. If nothing new: "No new matching jobs this run."

## Rules
- Free web tools only (the harness's built-in search and fetch). Do not invoke paid crawlers.
- Never fabricate a posting or a URL. When a title's match is borderline, exclude.
- Posted dates from `candidates.json` are real (from the ATS APIs); keep them. For web hits, leave Posted blank unless the page clearly states a date.
- Efficiency matters; this runs every few hours.
