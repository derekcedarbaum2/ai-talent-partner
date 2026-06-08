# Setup

The fastest path is to open the repo with Claude Code or Codex and run the setup skill (say "set up"
or `/setup`). It does everything below for you. This doc is the manual reference and the auth details.

## Prerequisites
- Python 3 (no third-party packages required; the scripts use only the standard library).
- A coding agent: Claude Code, or Codex / another agent following `AGENTS.md`.
- A scheduler: macOS `launchd` (examples in `launchd/`) or Linux `cron`.
- Optional: a Google account, only if you choose the Google Sheets backend.

## 1. Config
Copy the examples and edit:

```
cp config/config.example.json config/config.json
cp config/companies.example.txt config/companies.txt
cp config/terms.example.md      config/terms.md
cp config/profile.example.md    config/profile.md
```

Build `config/accomplishment-bank.md` with the accomplishment-interview skill (do not write it by hand).
Set `backend` in `config.json` to `csv` or `google_sheets`, and adjust the `filters` block to your search.

## 2. Spreadsheet backend

### CSV / Excel (zero auth, the default)
Create `data/jobs.csv` with this header row:

```
Date Found,Company,Job Title,Location,Posted,Job URL,Source,Will I apply?
```

Open it in Excel, Numbers, or Google Sheets to curate. You mark "Yes" in the last column. That is all.

### Google Sheets (shareable, one-time auth)
1. Create a sheet and add the same header row. Copy its ID from the URL (the long string between `/d/` and `/edit`) into `google_sheet_id` in `config.json`.
2. Create an OAuth token file at the path in `config.json` (`google_token_path`, default `~/.config/ai-talent-partner/google_token.json`) with this shape:

```json
{
  "client_id": "YOUR_OAUTH_CLIENT_ID",
  "client_secret": "YOUR_OAUTH_CLIENT_SECRET",
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

To get those: create an OAuth client (Desktop type) in Google Cloud Console with the Google Sheets API
enabled, then run the standard installed-app consent flow once to obtain a refresh token with the
`https://www.googleapis.com/auth/spreadsheets` scope. `scripts/sheet_io.py` uses the refresh token to mint
access tokens on each run, so you only authorize once. If you use Claude Code with a connected Google
Sheets MCP, the setup skill can do the sheet creation and writes through that instead, and you can skip
the token file.

## 3. First run
```
python3 scripts/resolve_ats.py     # detect which companies have pollable ATS boards
python3 scripts/poll.py            # phase A: gather + filter candidates
zsh scripts/run_finder.sh          # full finder run (adds rows to your sheet)
```

## 4. Schedule it

### macOS (launchd)
Edit the two files in `launchd/`, replacing `REPO_PATH` with your clone's absolute path, then:

```
cp launchd/com.user.ai-talent-partner-finder.plist.example ~/Library/LaunchAgents/com.user.ai-talent-partner-finder.plist
cp launchd/com.user.ai-talent-partner-apply.plist.example  ~/Library/LaunchAgents/com.user.ai-talent-partner-apply.plist
launchctl load ~/Library/LaunchAgents/com.user.ai-talent-partner-finder.plist
launchctl load ~/Library/LaunchAgents/com.user.ai-talent-partner-apply.plist
```

### Linux (cron)
Add these lines with `crontab -e` (replace REPO_PATH):

```
17 */4 * * * cd REPO_PATH && /bin/bash scripts/run_finder.sh >> finder.log 2>&1
7 9,14,19 * * * cd REPO_PATH && /bin/bash scripts/run_apply.sh >> apply.log 2>&1
```

## 5. The loop
The finder fills your sheet every few hours. Mark "Yes" on the jobs you want. The generator writes a
tailored resume, cover letter, and `application-questions.md` into `applications/<Company> - <Role>/` for
each Yes row that does not have materials yet. Review and send. Nothing is auto-submitted.

## Notes
- Schedulers fire only while the machine is awake. A missed run is harmless; de-dupe means nothing is lost.
- The generated materials are review-ready first drafts, not send-ready. Always read them before sending.
- Your real `config/*` files and `data/` are gitignored. Only the `.example` files are committed.
