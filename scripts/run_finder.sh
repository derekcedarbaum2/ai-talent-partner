#!/usr/bin/env bash
# Finder entry point. Runs on a schedule (default every 4h). Two deterministic Python phases
# bracket one model-driven step:
#   A) poll.py        hit each company's Greenhouse/Lever/Ashby board, filter titles + hard
#                     filters, write state/candidates.json + state/web_shard.json
#   B) prompts/finder.md   the model judges candidates, runs the web-search shard for non-ATS
#                     companies, de-dupes against the tracker, and appends new rows via sheet_io
#   then: check_live.py --apply (drop dead postings), backfill_dates.py --apply, sort_sheet.py
#
# Claude Code path: the model step runs headless via the `claude` CLI below.
# Portable / Codex path: if `claude` is not installed, phase B is skipped and the prompt is
#   printed for you to run yourself. Read prompts/finder.md, run it against state/candidates.json
#   and state/web_shard.json, then append the results through scripts/sheet_io.py. See AGENTS.md.

set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPTS")"
PY="${PYTHON:-python3}"
LOG="$ROOT/runs.log"

# Read model + finder prompt path from config.json (falls back to the example pre-setup).
read_cfg() { "$PY" - "$1" <<'PYEOF'
import json, os, sys
root = os.environ["ROOT"]
real = os.path.join(root, "config", "config.json")
path = real if os.path.exists(real) else os.path.join(root, "config", "config.example.json")
cfg = {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}
print(cfg.get(sys.argv[1], ""))
PYEOF
}
export ROOT
MODEL="$(read_cfg model)"; MODEL="${MODEL:-sonnet}"
PROMPT_FILE="$ROOT/prompts/finder.md"

{
  echo ""
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') FINDER START ====="

  # Phase A: deterministic poll.
  "$PY" "$SCRIPTS/poll.py"

  # Phase B: model judgment + web shard + append.
  if command -v claude >/dev/null 2>&1 && [ -f "$PROMPT_FILE" ]; then
    cd "$ROOT"
    claude -p "$(cat "$PROMPT_FILE")" \
      --model "$MODEL" \
      --permission-mode acceptEdits \
      --allowedTools "Read WebFetch WebSearch Glob Grep Bash(date:*) Bash(python3:*)" \
      --disallowedTools "Bash(rm:*) Bash(git:*)"
  else
    echo "claude CLI not found (or prompt missing): skipping the model step."
    echo "Run prompts/finder.md yourself against state/candidates.json + state/web_shard.json,"
    echo "then append results through scripts/sheet_io.py. See AGENTS.md."
  fi

  # Post-passes: drop dead rows, backfill dates, sort newest-first.
  "$PY" "$SCRIPTS/check_live.py" --apply
  "$PY" "$SCRIPTS/backfill_dates.py" --apply
  "$PY" "$SCRIPTS/sort_sheet.py"

  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') FINDER END ====="
} >> "$LOG" 2>&1

tail -n 3000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
