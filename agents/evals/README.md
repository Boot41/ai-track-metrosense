# MetroSense Evals

MetroSense agent evals are authored directly as ADK-native single-case
`.test.json` files. Each file is one runnable eval for one tool behaviour, one
subagent behaviour, or one root-agent behaviour.

## Structure

- `adk/tools/`: one eval file per tool behaviour
- `adk/subagents/`: one eval file per subagent behaviour
- `adk/root/`: one eval file per root-agent behaviour
- `tests_adk/`: live `pytest` entrypoints backed by `AgentEvaluator.evaluate(...)`
- `tests/`: non-live validation tests for asset shape and scorer helpers
- `fixtures/`: backend replay fixtures kept for scorer utilities

Each ADK directory has a `test_config.json` that defines the evaluation
criteria used by `AgentEvaluator`.

## Run Live ADK Evals

Prerequisites:

- `agents/.venv` exists
- ADK model credentials are configured
- env for live tool calls such as `BACKEND_INTERNAL_URL` and
  `AGENT_INTERNAL_TOKEN` is configured when you want tool-backed runs
- `DOCUMENTS_PATH` points at the MetroSense documents directory
  (the live harness defaults this to `server/Documents_Metrosense`)

Run all live evals:

```bash
cd /home/dell/ai-track-metrosense
agents/scripts/evals.sh agent
```

Run one layer:

```bash
agents/scripts/evals.sh agent-tools
agents/scripts/evals.sh agent-subagents
agents/scripts/evals.sh agent-root
```

Run one specific file or case id:

```bash
agents/scripts/evals.sh agent-file adk/tools/get_aqi_current_koramangala.test.json
agents/scripts/evals.sh agent-file get_aqi_current_koramangala
```

Direct `pytest` entrypoints are also available:

```bash
agents/.venv/bin/python -m pytest agents/evals/tests_adk/test_tools.py -q
agents/.venv/bin/python -m pytest agents/evals/tests_adk/test_subagents.py -q
agents/.venv/bin/python -m pytest agents/evals/tests_adk/test_root.py -q
```

The default live run count is `1`. Override it with:

```bash
METROSENSE_EVAL_NUM_RUNS=3 agents/scripts/evals.sh agent-tools
```

## Run Non-Live Validation Tests

These tests validate the registry and ADK asset shape without calling a model.

```bash
agents/scripts/evals.sh test
```

## Notes

- The old grouped `core_v1` and `session_v1` agent catalogs are no longer the
  source of truth for live agent evals.
- Backend scorer helpers remain in the repo for deterministic contract tests,
  but the live agent workflow is now direct ADK file execution.
