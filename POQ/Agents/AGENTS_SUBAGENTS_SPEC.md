  ## Phase 4 Plan (Revised): Agent Build With Strict File Structure, Config, and Prompt Organization

  ### Summary

  Implement Phase 4 with a production-oriented metrosense_agent layout where config, prompts/instructions,
  orchestration, and domain logic are clearly separated.
  This phase delivers a usable ADK graph (root_agent -> chat_agent -> 4 domain agents) plus backend integration to
  canonical Level-2 responses.

  ### File Structure (Locked)

  Use this structure and keep responsibilities strict:

  - agents/metrosense_agent/agent.py
      - defines/export root_agent only.
  - agents/metrosense_agent/config.py
      - env loading/validation for AGENT_MODEL, BACKEND_INTERNAL_URL, AGENT_INTERNAL_TOKEN, DOCUMENTS_PATH.
      - typed config object used by agents/tools.
  - agents/metrosense_agent/prompts/
      - root.py, chat.py, flood.py, heat.py, infra.py, logistics.py
      - each file contains only instruction strings + guardrail constants.
      - prompts/__init__.py exports instruction constants.
  - agents/metrosense_agent/subagents/
      - chat_agent.py, flood_agent.py, heat_agent.py, infra_agent.py, logistics_agent.py
      - each file: ADK agent object + tool registration only (no long prompt text inline).
  - agents/metrosense_agent/orchestration/
      - routing.py (intent/domain mapping, scorecard trigger rules)
      - response_contract.py (Level-1/Level-2 shaping helpers used by chat/root)
  - agents/metrosense_agent/tools/
      - keep current shared/domain tool modules
      - keep backend-envelope/raw-doc hybrid contract as already decided.
  - agents/metrosense_agent/tests/
      - split by test_agents_graph.py, test_routing.py, test_guardrails.py, test_l2_mapping.py.

  ### Implementation Changes

  - Agent graph + behavior:
      - root_agent delegates only to chat_agent; never user-facing.
      - chat_agent owns input guardrails, location resolution, domain fan-out, and final user response synthesis.
      - Domain agents own domain reasoning and return strict Level-1 payloads.
  - Prompt/instruction discipline:
      - all refusal strings, routing constraints, citation/freshness rules in prompt modules, not agent files.
      - add explicit prompt rules for hybrid tool contract:
          - backend tools: read result.data and inspect result.meta
          - document tools: consume raw section/index output.
  - Config discipline:
      - fail-fast validation on missing required env for runtime-critical values.
      - one config source imported everywhere; no duplicated os.getenv scattered across agents.
  - Backend integration:
      - set server config agent_app_name="metrosense_agent".
      - update agent_proxy to map ADK output to canonical Level-2 fields.
      - retain existing persistence flow.

  ### Test Plan

  - Structure/config tests:
      - config validation success/failure paths.
      - agent modules import without circular dependencies.
  - Agent behavior tests:
      - off-domain refusal, location-not-found, no-data/degraded-data behavior.
      - routing correctness (single-domain, multi-domain, scorecard trigger).
  - Contract tests:
      - each domain returns valid Level-1 required fields.
      - backend returns canonical Level-2 shape with nullable risk_card/artifact.
  - Integration checks:
      - adk api_server loads metrosense_agent.
      - backend /api/chat works end-to-end with proxy + ADK + persistence.

  ### Assumptions and Defaults

  - metrosense_agent + root_agent is the canonical app identity.
  - No streaming/SSE in this phase.
  - Structured outputs remain nullable unless explicitly requested and supported.
  - Prompt/config/file-ownership rules are mandatory to prevent drift and keep future phases maintainable.





  ## Add Greeting Self-Introduction Behavior (Greeting-Only Trigger)

  ### Summary

  Implement a deterministic greeting flow so when the user sends a greeting-only message, the chat agent responds
  with:

  1. a short self-introduction, and
  2. 2–3 example questions.
     If the message includes a real query after greeting (e.g., “Hi, flood risk in Bellandur?”), skip greeting-mode
     and proceed with normal domain routing/fan-out (“spin up agents”) immediately.

  ### Key Changes

  - Add greeting detection utilities in orchestration logic:
      - normalize message and detect greeting-only utterances (hi, hello, hey, good morning, etc.).
      - add is_greeting_only(message) helper and keep existing intent routing untouched.
  - Add prompt-level guardrail in chat instructions:
      - explicit rule: greeting-only => self-intro + examples.
      - greeting + question => treat as normal query; do not stop at greeting response.
  - Add a reusable greeting template constant (identity + examples) so response text is consistent:
      - “I’m MetroSense, your Bengaluru climate and infrastructure intelligence assistant…”
      - example queries for flood, AQI/heat, outage/infra, traffic/logistics.
  - Keep response contract unchanged:
      - return canonical Level-2 fields for greeting responses as response_mode="text", risk_card/artifact=null.

  ### Interfaces / Behavior Rules

  - New behavior decision:
      - greeting_only == true:
          - return greeting intro response only, no domain fan-out.
      - greeting_only == false:
          - run standard flow (location resolution, intent classification, domain agents).
  - No API schema changes required for /api/chat.
  - No tool signature changes required.

  ### Test Plan

  - Add routing unit tests:
      - pure greeting triggers is_greeting_only=True.
      - greeting + query triggers is_greeting_only=False.
  - Add guardrail/prompt tests:
      - chat instruction contains explicit greeting-only and greeting+query rules.
  - Add response-shaping test:
      - greeting-only returns Level-2 text response with nullable structured blocks.
  - Regression checks:
      - existing scorecard trigger and multi-domain routing tests still pass.

  ### Assumptions and Defaults

  - Greeting behavior applies only to short salutation-only inputs.
  - For mixed input (greeting + real question), agent prioritizes task execution immediately.
  - Intro style locked to “Intro + examples” per your preference; examples remain concise and Bengaluru-domain
    specific.
