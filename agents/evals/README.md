# MetroSense Evals

MetroSense agent evals are ADK-native `.test.json` files executed by the ADK
`AgentEvaluator`. Each file is one runnable eval that drives a single
`eval_case` — a conversation consisting of one or more user↔agent turns.
The evaluator replays the conversation against the live agent and scores each
turn based on the criteria in `test_config.json`.

## Eval format

Every `.test.json` follows the canonical ADK eval-set schema. A minimal
single-turn file looks like:

```json
{
  "eval_set_id": "get_aqi_current_koramangala",
  "name": "adk/tools/get_aqi_current_koramangala.test.json",
  "description": "Current AQI lookup for Koramangala.",
  "eval_cases": [
    {
      "eval_id": "get_aqi_current_koramangala",
      "conversation": [
        {
          "invocation_id": "...",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "video_metadata": null, "thought": null, "inline_data": null,
                "code_execution_result": null, "executable_code": null,
                "file_data": null, "function_call": null,
                "function_response": null,
                "text": "What is AQI in Koramangala now?"
              }
            ]
          },
          "final_response": {
            "role": null,
            "parts": [{ "...(same null fields)...", "text": "<expected output>" }]
          },
          "intermediate_data": {
            "tool_uses": [{ "name": "get_aqi_current", "args": { "location_id": "Koramangala", "limit": 1 } }],
            "intermediate_responses": []
          },
          "creation_timestamp": 1740000010.0
        }
      ],
      "session_input": {
        "app_name": "metrosense_agent",
        "user_id": "metrosense-eval-user",
        "state": {}
      },
      "creation_timestamp": 1740000010.0
    }
  ],
  "creation_timestamp": 1740000010.0
}
```

Key rules:
- `user_content.parts` and `final_response.parts` must include all null fields
  (`video_metadata`, `thought`, `inline_data`, `code_execution_result`,
  `executable_code`, `file_data`, `function_call`, `function_response`, `text`).
- `final_response.role` is always `null` (the ADK evaluator ignores this field).
- `intermediate_data` contains only `tool_uses` and `intermediate_responses` —
  there is no `tool_responses` field.
- For **multi-turn conversations** add more objects to the `conversation` array:
  each object is one (user, agent) exchange evaluated in sequence.
- `final_response.parts[].text` is the **reference output** used by
  `response_match_score`. For tool-level evals it should be a representative
  structured JSON string; for subagent/root evals it should describe what a
  correct response contains in plain English.

## Agent output and level-1 parsing

The MetroSense subagents (`chat_agent` and its four domain subagents) return
structured JSON according to `response_contract.build_level2_response()`.  The
ADK `AgentEvaluator` receives the raw agent output (the "level-1" or SDK-level
response) and compares it against `final_response.parts[].text` using semantic
scoring.  The backend's `agent_proxy.py` level-2 parsing is a separate
production-only step and is not exercised by these evals.

## Structure

- `adk/tools/`: one eval file per tool behaviour (16 files)
- `adk/subagents/`: one eval file per subagent behaviour (9 files)
- `adk/root/`: one eval file per root-agent / conversation-flow behaviour (7 files)
- `tests_adk/`: live `pytest` entrypoints backed by `AgentEvaluator.evaluate(...)`
- `tests/`: non-live validation tests for asset shape and registry consistency

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

## Conversation-flow evals

Multi-turn evals live under `adk/root/` and have more than one entry in the
`conversation` array. The evaluator replays each turn in order within the same
ADK session, so later turns can reference context from earlier ones. Example:

- `root_agent_flood_to_traffic_conversation` — user asks about Bellandur flood
  risk, then follows up asking about ORR traffic delay under flood conditions.

To add new multi-turn flows: add additional objects to the `conversation` array
in the same `.test.json` file, each with its own `invocation_id`,
`user_content`, `final_response`, and `intermediate_data`.
