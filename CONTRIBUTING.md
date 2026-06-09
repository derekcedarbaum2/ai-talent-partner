# Contributing

Thanks for wanting to improve ai-talent-partner. This is a "build your own" project, so most people will
fork it and adapt it to their own search. Contributions that help everyone are very welcome.

## Good first contributions
- ATS coverage: add a liveness/board check for an applicant tracking system not yet handled (Rippling, Comeet, Gem, Workable, and so on). The pattern is in `scripts/check_live.py` and `scripts/ats_lib.py`.
- More seed company lists for other industries (healthcare, fintech, biotech, climate, gaming). Drop a `config/seed-companies/<industry>.txt` in the same format.
- A non-Chrome PDF path in `scripts/render_pdf.py` for users who do not have Chrome.
- Better portability: a cleaner runner for Codex or another agent CLI in `scripts/run_finder.sh` / `scripts/run_apply.sh`.
- Docs and examples, especially a real demo screenshot or gif for the README.

## Ground rules
- No personal data in the repo. Keep examples fictional (the sample person is "Jordan Avery"). Real config and workspace data are gitignored; never commit them.
- Keep the deterministic-versus-model split. Fetching, filtering, de-duping, and liveness belong in Python. The model is for judgment and writing only. That split is what keeps it affordable to run.
- The agent never invents accomplishments. Anything that generates resume or cover-letter content must trace to the user's accomplishment bank.
- Standard library only in `scripts/` where possible. Avoid adding dependencies unless there is a strong reason.
- Writing style in markdown files: plain prose, no em-dashes, no emoji, and avoid bullets that start with bold. Keep it readable.

## Workflow
- Fork, branch, open a pull request with a clear description of the problem and the change.
- Keep pull requests focused. One concern per PR is easier to review.
- If you change behavior, update the relevant doc (`README.md`, `AGENTS.md`, or files under `docs/`).

## Scope
This project finds jobs and drafts tailored materials. It does not, and will not, auto-submit
applications or do anything that pressures a person to send something they have not read. Contributions
that cross that line will not be merged.
