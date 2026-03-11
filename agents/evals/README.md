# MetroSense Evals

This directory contains the curated MetroSense eval system for both:

- `agent_only`: Google ADK-native evals run against `agents/metrosense_agent`
- `backend_e2e`: end-to-end evals run through `server /api/chat`

## Structure

- `cases/`: canonical MetroSense eval catalogs
- `schema/`: JSON schema for the canonical catalog format
- `rubrics/`: MetroSense-specific rubric text used in ADK judge config
- `runners/`: scripts to build, run, and score evals
- `fixtures/`: replay inputs for cases that should not depend on live runtime behavior
- `results/`: local run outputs

## Canonical Catalog

MetroSense uses a repo-specific canonical catalog JSON format. Each case defines:

- one or more conversation turns
- per-turn expectations
- backend deterministic assertions
- tier targets (`agent_only`, `backend_e2e`)

The canonical catalog is compiled into Google ADK `.evalset.json` and `.evalconfig.json` files.

## Build ADK Eval Artifacts

```bash
cd /home/dell/ai-track-metrosense
agents/.venv/bin/python agents/evals/runners/build_adk_evalset.py \
  --catalog agents/evals/cases/core_v1.json \
  --catalog agents/evals/cases/session_v1.json
```

Shortcut:

```bash
make evals-build
# or
agents/scripts/evals.sh build
```

## Run Agent-Only ADK Evals

Prerequisites:

- `agents/.venv` exists
- model credentials required by ADK are configured

```bash
cd /home/dell/ai-track-metrosense
agents/.venv/bin/python agents/evals/runners/run_agent_eval.py \
  --catalog agents/evals/cases/core_v1.json \
  --catalog agents/evals/cases/session_v1.json \
  --print-detailed-results
```

Shortcut:

```bash
make evals-agent
# or
agents/scripts/evals.sh agent
```

## Run Backend End-to-End Evals

Prerequisites:

- PostgreSQL seeded with MetroSense data
- `server` running on `http://127.0.0.1:8010`
- `agents` running and reachable from the backend

Run the backend harness:

```bash
cd /home/dell/ai-track-metrosense
server/.venv/bin/python agents/evals/runners/run_backend_eval.py \
  --catalog agents/evals/cases/core_v1.json \
  --output agents/evals/results/core_backend_results.json
```

Shortcut:

```bash
make evals-backend
# or
agents/scripts/evals.sh backend
```

Then score the results:

```bash
cd /home/dell/ai-track-metrosense
server/.venv/bin/python agents/evals/runners/score_backend_eval.py \
  --catalog agents/evals/cases/core_v1.json \
  --results agents/evals/results/core_backend_results.json \
  --output agents/evals/results/core_backend_scored.json
```

Shortcut:

```bash
make evals-backend-score
# or
agents/scripts/evals.sh backend-score
```

## Run Eval Tests

```bash
make evals-test
# or
agents/scripts/evals.sh test
```

## Notes

- The overflow retry case is fixture-backed in v1 because token overflow is not deterministic enough for a normal live eval run.
- User simulation is intentionally deferred; v1 focuses on curated fixed-reference evals.
- The backend scorer emphasizes deterministic contract checks. ADK judge-based quality scoring lives in the agent-only tier.
