#!/usr/bin/env bash
# Finder entry point. Runs on a schedule (default every 4h). Two deterministic Python phases
# bracket one model-driven step:
#   A) poll.py        hit each company's Greenhouse/Lever/Ashby board, filter titles + hard
#                     filters, write state/candidates.json + state/web_shard.json
#   B) model step     judge candidates, run the web-search shard for non-ATS companies, de-dupe
#                     against the tracker, append new rows via sheet_io
#   then: check_live.py --apply (drop dead postings), backfill_dates.py --apply, sort_sheet.py
#
# The model step runs through config "agent_command" (default "claude -p"). For Codex or another
# CLI, set agent_command to your headless invocation; the prompt is piped on stdin. If no headless
# agent is available, phase B is skipped and the prompt is printed for you to run. See AGENTS.md.

set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPTS")"
PY="${PYTHON:-python3}"
LOG="$ROOT/runs.log"

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
AGENT_CMD="$(read_cfg agent_command)"; AGENT_CMD="${AGENT_CMD:-claude -p}"
AGENT_BIN="${AGENT_CMD%% *}"
PROMPT_FILE="$ROOT/prompts/finder.md"

{
  echo ""
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') FINDER START ====="

  # Phase A: deterministic poll.
  "$PY" "$SCRIPTS/poll.py"

  # Phase B: model judgment + web shard + append.
  cd "$ROOT"
  if [ -f "$PROMPT_FILE" ] && [ "$AGENT_BIN" = "claude" ] && command -v claude >/dev/null 2>&1; then
    claude -p "$(cat "$PROMPT_FILE")" \
      --model "$MODEL" \
      --permission-mode acceptEdits \
      --allowedTools "Read WebFetch WebSearch Glob Grep Bash(date:*) Bash(python3:*)" \
      --disallowedTools "Bash(rm:*) Bash(git:*)"
  elif [ -f "$PROMPT_FILE" ] && [ "$AGENT_BIN" != "claude" ] && command -v "$AGENT_BIN" >/dev/null 2>&1; then
    cat "$PROMPT_FILE" | $AGENT_CMD
  else
    echo "No headless agent available (agent_command=$AGENT_CMD): skipping the model step."
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
