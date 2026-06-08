#!/usr/bin/env bash
# Generator entry point. Runs a few times a day. Scans the tracker for "Will I apply? = Yes"
# rows that lack materials, then for each one the model writes a tailored resume, a tailored
# cover letter, and an application-questions.md answering the posting's substantive questions.
# Output goes to config[applications_dir]/<Company> - <Role>/. Nothing is submitted.
#
#   1) apply_scan.py     find Yes rows lacking materials -> state/apply_queue.json
#   2) prompts/apply.md  the model generates the three documents per queued job (each writing
#                        pass runs the sense-of-style check at least once)
#   3) apply_mark.py     mark jobs whose three files now exist as done (so they never regenerate)
#
# Claude Code path: the model step runs headless via the `claude` CLI below.
# Portable / Codex path: if `claude` is not installed, the generation step is skipped and the
#   prompt is printed for you to run yourself against state/apply_queue.json. See AGENTS.md.

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
PROMPT_FILE="$ROOT/prompts/apply.md"

{
  echo ""
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') APPLY START ====="

  "$PY" "$SCRIPTS/apply_scan.py"

  COUNT="$("$PY" -c "import json;print(len(json.load(open('$ROOT/state/apply_queue.json'))))" 2>/dev/null || echo 0)"
  if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    if command -v claude >/dev/null 2>&1 && [ -f "$PROMPT_FILE" ]; then
      cd "$ROOT"
      # acceptEdits auto-approves the file writes (drafts into applications/).
      claude -p "$(cat "$PROMPT_FILE")" \
        --model "$MODEL" \
        --permission-mode acceptEdits \
        --allowedTools "Read Write Edit WebFetch WebSearch Glob Grep Task Bash(date:*) Bash(mkdir:*)" \
        --disallowedTools "Bash(rm:*) Bash(git:*) Bash(curl:*)"
    else
      echo "claude CLI not found (or prompt missing): skipping generation."
      echo "Run prompts/apply.md yourself against state/apply_queue.json. See AGENTS.md."
    fi
    "$PY" "$SCRIPTS/apply_mark.py"
  else
    echo "apply: queue empty, skipping generation"
  fi

  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') APPLY END ====="
} >> "$LOG" 2>&1

tail -n 2000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
