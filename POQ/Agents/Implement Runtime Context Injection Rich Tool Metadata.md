  # Plan: Implement Runtime Context Injection + Rich Tool Metadata

  ## Summary

  Implement both items together by making the server the source of operational truth and the agent tools
  the carrier of that truth.

  - Add a reusable backend metadata layer that computes freshness/coverage summaries per domain from
    PostgreSQL.
  - Use that layer in two places:
      - server injects a short runtime context block into every agent request.
      - /internal/* endpoints return structured metadata alongside data so agent tools can stop inventing
        freshness notes.
  - Remove the remaining hardcoded dataset note logic in agent tool transport and make prompts/tool
    responses consistently derive freshness from runtime metadata.

  ## Key Changes

  ### 1. Backend runtime context injector

  Implement a server-side context builder used by server/app/services/agent_proxy.py before calling ADK.

  - Add a new service helper, e.g. server/app/services/runtime_context.py, that returns a compact
    snapshot:
      - generated_at
      - per-domain available_from
      - per-domain available_to
      - per-domain location_count or location_sample
      - optional flags like has_data
  - Domains covered:
      - weather
      - aqi
      - lakes
      - floods
      - outages
      - traffic
  - Build the snapshot from DB queries against the existing tables; do not hardcode dates, counts, or
    inventories.
  - In get_chat_response(), prepend a machine-readable context preamble to the message sent to ADK:
      - clearly marked as system/runtime context, not user-authored text
      - compact JSON or YAML-like block
      - includes explicit instruction: “use this only as availability/freshness context; tool outputs
        remain authoritative”
  - Persist and display the original user message exactly as today; only the ADK-bound message is
    augmented.
  - Keep this injection internal to the backend; no frontend or public API shape changes.

  ### 2. Rich metadata on internal tool responses

  Upgrade /internal/* endpoints from raw arrays/objects to a consistent envelope.

  - New internal response shape:
      - data: existing payload
      - meta:
          - ok
          - domain
          - dataset_note
          - available_from
          - available_to
          - last_updated_at
          - record_count_returned
          - resolved_location when applicable
  - Implement shared metadata builders in server/app/services/data_service.py or a dedicated helper module
    so every internal endpoint uses the same logic.
  - dataset_note must be generated from actual DB values, not constants.
  - Keep public browser APIs unchanged; only /internal/* changes.
  - Update agents/metrosense_agent/tools/backend_client.py to expect the envelope and map it into
    ToolResult:
      - data should come from payload data
      - meta.dataset_note should come from payload meta.dataset_note
      - extend tool meta typing to include available_from, available_to, last_updated_at,
        record_count_returned, and resolved_location
  - Delete the hardcoded _DATASET_COVERAGE = "Jan 2023 – Dec 2023" path and the heuristic note builder.
  - Keep failure handling as-is, but on success preserve backend metadata verbatim.

  ### 3. Contract alignment

  Make the prompt/runtime/tool contracts line up so the agent sees one coherent story.

  - Update the internal tool contract comments/types in agents/metrosense_agent/tools/types.py to reflect
    the richer metadata.
  - Ensure the chat/subagent instructions continue to refer to meta.dataset_note as authoritative, now
    backed by real runtime values.
  - Normalize data_freshness_summary assembly in parsing code only if needed; do not change frontend
    response schema.

  ## Interfaces and Compatibility

  Internal interface changes only:

  - /internal/weather/*, /internal/aqi/*, /internal/lakes, /internal/floods, /internal/outages, /internal/
    traffic/*, /internal/locations/*, /internal/ward/profile
      - from: raw list/object
      - to: { "data": ..., "meta": ... }
  - Agent tool result type:
      - extend ToolMeta with backend freshness fields listed above
  - Public /api/chat request/response stays unchanged.

  Defaults:

  - dataset_note format should be short and deterministic, e.g. “Coverage in result domain: 2025-01-01 to
    2026-03-10. Latest available record: 2026-03-10T12:00:00Z.”
  - For empty datasets, set:
      - ok: true
      - record_count_returned: 0
      - available_from: null
      - available_to: null
      - last_updated_at: null
      - dataset_note explaining no records were found for that query/domain

  ## Test Plan

  Add or update tests for both backend and agents.

  - Backend unit tests:
      - internal routes now return {data, meta}
      - metadata fields are present and correctly populated for non-empty results
      - empty-result queries still return valid metadata
      - runtime context builder returns all six domain summaries
      - agent_proxy.get_chat_response() sends an augmented ADK message containing runtime context and the
        original user prompt
  - Agent tool tests:
      - backend_client maps internal envelope into ToolResult
      - success path preserves dataset_note, last_updated_at, and coverage fields
      - missing backend config and HTTP failures still return the existing failure contract
  - Regression tests:
      - server/tests/unit/test_chat_api.py remains green without response-shape changes
      - any tests asserting raw /internal/* payloads must be updated to the new envelope
  - Optional integration check:
      - one end-to-end stubbed chat request confirming the runtime context preamble reaches ADK and that
        returned freshness is sourced from tool metadata, not a hardcoded string

  ## Assumptions

  - “1 and 2” refers to:
      - runtime context injection
      - richer tool metadata/freshness handling
  - We will change internal backend-agent contracts freely, because /internal/* is not a browser-facing
    API.
  - Runtime context will be injected by the backend as an augmented ADK message, not via ADK session
    state/callback APIs, because the current integration already sends plain newMessage.text and this is
    the lowest-risk implementation.
  - No frontend work is required for this plan.
