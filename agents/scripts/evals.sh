#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENTS_SITE_PACKAGES="$ROOT_DIR/agents/.venv/lib/python3.12/site-packages"

run_live_pytest() {
  PYTHONPATH="$AGENTS_SITE_PACKAGES:$ROOT_DIR/agents${PYTHONPATH:+:$PYTHONPATH}" \
    "$ROOT_DIR/server/.venv/bin/python" -m pytest "$@"
}

run_agent_pytest() {
  local filter="${1:-}"
  if [[ -n "$filter" ]]; then
    METROSENSE_EVAL_FILE="$filter" \
      run_live_pytest "$ROOT_DIR/agents/evals/tests_adk" -q
    return
  fi

  run_live_pytest "$ROOT_DIR/agents/evals/tests_adk" -q
}

agent_tools() {
  run_live_pytest "$ROOT_DIR/agents/evals/tests_adk/test_tools.py" -q
}

agent_subagents() {
  run_live_pytest "$ROOT_DIR/agents/evals/tests_adk/test_subagents.py" -q
}

agent_root() {
  run_live_pytest "$ROOT_DIR/agents/evals/tests_adk/test_root.py" -q
}

agent_all() {
  run_agent_pytest
}

agent_file() {
  local relative_path="${1:-}"
  if [[ -z "$relative_path" ]]; then
    echo "Usage: agents/scripts/evals.sh agent-file <relative-path-or-case-id>" >&2
    exit 1
  fi

  run_agent_pytest "$relative_path"
}

tests() {
  "$ROOT_DIR/server/.venv/bin/python" -m pytest "$ROOT_DIR/agents/evals/tests" -q
}

usage() {
  cat <<'EOF'
Usage: agents/scripts/evals.sh <command>

Commands:
  test            Run non-live eval asset/unit tests
  agent           Run all ADK evals
  agent-tools     Run tool-level ADK evals
  agent-subagents Run subagent-level ADK evals
  agent-root      Run root-agent ADK evals
  agent-file      Run one ADK eval by relative path or case id
EOF
}

case "${1:-}" in
  test)
    tests
    ;;
  agent)
    agent_all
    ;;
  agent-tools)
    agent_tools
    ;;
  agent-subagents)
    agent_subagents
    ;;
  agent-root)
    agent_root
    ;;
  agent-file)
    shift
    agent_file "${1:-}"
    ;;
  *)
    usage
    exit 1
    ;;
esac
