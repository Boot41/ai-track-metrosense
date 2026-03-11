#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

build() {
  "$ROOT_DIR/agents/.venv/bin/python" "$ROOT_DIR/agents/evals/runners/build_adk_evalset.py" \
    --catalog agents/evals/cases/core_v1.json \
    --catalog agents/evals/cases/session_v1.json
}

tests() {
  "$ROOT_DIR/server/.venv/bin/python" -m pytest "$ROOT_DIR/agents/evals/tests" -q
}

agent() {
  "$ROOT_DIR/agents/.venv/bin/python" "$ROOT_DIR/agents/evals/runners/run_agent_eval.py" \
    --catalog agents/evals/cases/core_v1.json \
    --catalog agents/evals/cases/session_v1.json \
    --print-detailed-results
}

backend() {
  "$ROOT_DIR/server/.venv/bin/python" "$ROOT_DIR/agents/evals/runners/run_backend_eval.py" \
    --catalog agents/evals/cases/core_v1.json \
    --output agents/evals/results/core_backend_results.json
}

backend_score() {
  "$ROOT_DIR/server/.venv/bin/python" "$ROOT_DIR/agents/evals/runners/score_backend_eval.py" \
    --catalog agents/evals/cases/core_v1.json \
    --results agents/evals/results/core_backend_results.json \
    --output agents/evals/results/core_backend_scored.json
}

usage() {
  cat <<'EOF'
Usage: agents/scripts/evals.sh <command>

Commands:
  build          Generate schema and ADK eval artifacts
  test           Run eval-unit tests
  agent          Run ADK agent-only evals
  backend        Run backend end-to-end evals
  backend-score  Score the latest backend eval results
EOF
}

case "${1:-}" in
  build)
    build
    ;;
  test)
    tests
    ;;
  agent)
    agent
    ;;
  backend)
    backend
    ;;
  backend-score)
    backend_score
    ;;
  *)
    usage
    exit 1
    ;;
esac
