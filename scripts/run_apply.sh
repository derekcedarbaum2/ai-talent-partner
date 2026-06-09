#!/usr/bin/env bash
# Generator entry point. Runs a few times a day. Scans the tracker for "Will I apply? = Yes"
# rows that lack materials, then for each one the model writes a tailored resume, a tailored
# cover letter, and an application-questions.md answering the posting's substantive questions,
# plus filled resume.html / cover-letter.html that render_pdf.py turns into PDFs.
# Output goes to config[applications_dir]/<Company> - <Role>/. Nothing is submitted.
#
#   1) apply_scan.py     find Yes rows lacking materials -> state/apply_queue.json
#   2) model step        generate the documents per queued job (each writing pass runs sense-of-style)
#   3) render_pdf.py     turn the filled HTML into PDFs
#   4) apply_mark.py     mark jobs whose files now exist as done (so they never regenerate)
#
# The model step runs through config "agent_command" (default "claude -p"). For Codex or another
# CLI, set agent_command to your headless invocation; the prompt is piped on stdin. If no headless
# agent is available, the step is skipped and the prompt is printed for you to run. See AGENTS.md.

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
PROMPT_FILE="$ROOT/prompts/apply.md"

{
  echo ""
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') APPLY START ====="

  "$PY" "$SCRIPTS/apply_scan.py"

  COUNT="$("$PY" -c "import json;print(len(json.load(open('$ROOT/state/apply_queue.json'))))" 2>/dev/null || echo 0)"
  if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    cd "$ROOT"
    if [ -f "$PROMPT_FILE" ] && [ "$AGENT_BIN" = "claude" ] && command -v claude >/dev/null 2>&1; then
      # Claude Code path. acceptEdits auto-approves the file writes (drafts into applications/).
      claude -p "$(cat "$PROMPT_FILE")" \
        --model "$MODEL" \
        --permission-mode acceptEdits \
        --allowedTools "Read Write Edit WebFetch WebSearch Glob Grep Task Bash(date:*) Bash(mkdir:*)" \
        --disallowedTools "Bash(rm:*) Bash(git:*) Bash(curl:*)"
    elif [ -f "$PROMPT_FILE" ] && [ "$AGENT_BIN" != "claude" ] && command -v "$AGENT_BIN" >/dev/null 2>&1; then
      # Portable path: pipe the prompt to whatever headless agent the user configured.
      cat "$PROMPT_FILE" | $AGENT_CMD
    else
      echo "No headless agent available (agent_command=$AGENT_CMD): skipping generation."
      echo "Run prompts/apply.md yourself against state/apply_queue.json. See AGENTS.md."
    fi
    # Turn the filled HTML into PDFs (no-op if render.engine=none or Chrome is absent).
    "$PY" "$SCRIPTS/render_pdf.py" --all || true
    "$PY" "$SCRIPTS/apply_mark.py"
  else
    echo "apply: queue empty, skipping generation"
  fi

  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') APPLY END ====="
} >> "$LOG" 2>&1

tail -n 2000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
