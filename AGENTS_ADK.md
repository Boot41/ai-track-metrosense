# MetroSense — Agents & ADK Reference
### Agent Design, Session, Context, Tools, Evals
---

## Table of Contents

1. ADK Runtime and Agent Hierarchy
2. Agent Responsibilities
3. Domain Agent Tool Design
4. Session and Context Management
5. JSON Output Contract
6. Agentic RAG — Document Intelligence
7. Guardrails
8. Evals Strategy
9. Open Design Gaps

---

## 1. ADK Runtime and Agent Hierarchy

### How ADK Runs the System

The ADK Runner is not a designed component — it is ADK infrastructure. It executes the Root Agent, manages the tool call event loop, and returns the final response. Configuration is a single line:

```python
runner = Runner(agent=root_agent, session_service=session_service)
runner.run(user_message)
```

### Agent Hierarchy

```
ADK Runner
    │
    ▼
Root Agent (Orchestrator)
    │   — Intent classification
    │   — Parallel dispatch via asyncio.gather()
    │   — Level-1 → Level-2 scorecard merge
    │   — Global guardrails
    │
    ▼
Chat Agent  ← only agent the user ever talks to
    │   — Input guardrails
    │   — Session memory read/write
    │   — Fan-out to domain sub-agents
    │   — NL synthesis with citations
    │   — Chart follow-up trigger
    │   — Scorecard mode trigger
    │
    ├── Flood Vulnerability Agent     (sub-agent)
    ├── Urban Heat & Health Agent     (sub-agent)
    ├── Infrastructure Stress Agent   (sub-agent)
    └── Logistics Disruption Agent    (sub-agent)
```

### Key Design Principles

**Runner is infrastructure, not an agent.** Do not design a runner agent — it is a one-line ADK configuration.

**Root Agent never talks to the user.** It routes, dispatches, and merges. The Chat Agent owns all user-facing communication.

**Chat Agent calls domain agents directly.** No round-trip back through Root Agent for domain queries. Chat Agent fans out directly, collects Level-1 payloads, and synthesises the NL response.

**Guardrails live at the Chat Agent.** Because Chat Agent is the actual entry point for user input, input filtering and injection detection live here — not assumed to be handled upstream.

**Sub-agents are registered under Chat Agent** and are pure domain reasoning units. They never receive user input directly.

### Sub-Agent Future-Proofing

Sub-agents are fully implemented for v1: `flood_vulnerability_agent`, `heat_health_agent`, `infrastructure_agent`, and `logistics_agent` are all wired under `chat_agent`. The signals to split further (e.g. per-domain sub-sub-agents) are:
- Any domain agent tool count exceeds 10-12 and LLM tool selection degrades
- Any agent file exceeds ~300-400 lines
- Tool logic is being copy-pasted across two domain agents

Tool files are pre-partitioned by concern inside each agent folder so further splitting is a mechanical refactor when the time comes.

---

## 2. Agent Responsibilities

### Root Agent (Orchestrator)

**Owns:**
- Intent classification — maps NL query to one or more domain intents
- Output mode determination — text / scorecard / chart follow-up
- Parallel dispatch — `asyncio.gather()` for multi-domain queries
- Level-1 payload collection and pure Python merge → Level-2 Unified Scorecard
- Global guardrails before final response

**State Bag:**
```python
{
  "query_id": "uuid",
  "intent": ["flood_vulnerability", "logistics_disruption"],
  "active_agents": ["flood", "logistics"],
  "partial_results": {},
  "session_history": [],
  "output_mode": "text | scorecard | chart",
  "data_freshness": {}
}
```

**Does not own:**
- Conversation with user
- Session memory
- NL synthesis

---

### Chat Agent

**Owns:**
- The only conversational interface — user input comes in here, NL response goes out here
- Input guardrails — domain relevance, injection detection, query length limits
- Session memory read and write
- Location resolution — maps "Bellandur" or "HSR Layout Sector 2" to `location_id` via `location_master`
- Fan-out to domain sub-agents directly
- NL response synthesis with citations
- Chart follow-up evaluation and prompt injection
- Scorecard mode trigger on NL keywords

**Routing examples:**
```
"If 60mm tonight, which underpasses?"         → Flood + Logistics (parallel)
"Compare AQI vs decade average this month"    → Heat Agent (historical mode)
"Tree-fall risk near MG Road?"                → Infra Agent (zone filter)
"Risk scorecard for Bellandur"                → All agents → Unified Scorecard
"Will ORR delay cross 1.5x tonight?"          → Logistics Agent only
```

**Chart follow-up behavior:**
After any trend or comparative answer, Chat Agent evaluates whether a chart would genuinely improve understanding. If yes it appends: *"Would you like to see this as a chart?"* Charts are never auto-generated — explicit user confirmation required.

**Scorecard trigger keywords:**
`risk`, `scorecard`, `vulnerability`, `assessment`, `how vulnerable is [place]`
Note: `summary` is explicitly excluded — too generic, used in non-scorecard contexts.

---

### Flood Vulnerability Agent

**Goal:** Identify flood black spots, predict inundation risk, recommend barricade locations.

**Postgres Tools:**
```
get_rainfall_current(location_id)
get_rainfall_historical(location_id, window_hours)
get_lake_hydrology(lake_id)
get_flood_incidents_historical(location_id)
```

**Document Tools:**
```
list_document_indexes(document_type="drainage_plan", ward_name)
list_document_indexes(document_type="flood_postmortem", ward_name)
list_document_indexes(document_type="imd_bulletin", ward_name)
fetch_document_section(document_id, section_id)
```

**Key reasoning logic:**
- `fill_percentage` + `overflow_status` + `surplus_flow_cusecs` from `lake_hydrology` drives backflow risk
- `rainfall_intensity_mm_hr` vs drainage capacity extracted from document sections is the flash flood trigger
- Barricade threshold values (mm/hr) come from drainage plan document sections, not hardcoded
- 2022 flood post-mortem sections provide calibration priors for black spot scoring
- Pre-seeded monitored zones: Sarjapur, Bellandur, Manyata Tech Park, Varthur, Hebbal, KR Puram, Koramangala, Silk Board

**Level-1 Output:**
```json
{
  "agent": "flood_vulnerability",
  "confidence": 0.87,
  "status": "ok",
  "data": {
    "zone_scores": [],
    "blackspots": [],
    "barricade_recommendations": [],
    "lake_status": {}
  },
  "citations": [],
  "data_freshness": {}
}
```

---

### Urban Heat & Health Agent

**Goal:** Generate neighbourhood-specific health advisories from AQI data and climate research documents.

**Postgres Tools:**
```
get_aqi_current(location_id)
get_aqi_historical(location_id, days)
get_weather_heat_metrics(location_id)
get_population_vulnerability(ward_id)     -- queries ward_profile table
```

**Document Tools:**
```
list_document_indexes(document_type="resilience_paper", ward_name)
list_document_indexes(document_type="imd_bulletin", ward_name)
fetch_document_section(document_id, section_id)
```

**Key reasoning logic:**
- `aqi_category` + `dominant_pollutant` generates specific advisory — not generic messaging
- `elderly_population_pct` + `children_population_pct` from `ward_profile` flags sensitive population zones
- `green_cover_pct` from `ward_profile` is the UHI intensity multiplier
- WHO AQI thresholds applied per pollutant type
- Temperature + humidity drives heat stress tier reasoning

**Level-1 Output:**
```json
{
  "agent": "heat_health",
  "confidence": 0.82,
  "status": "ok",
  "data": {
    "zone_aqi": [],
    "heat_stress_tier": "HIGH | MODERATE | LOW",
    "advisories": [],
    "population_risk_zones": []
  },
  "citations": [],
  "data_freshness": {}
}
```

---

### Infrastructure Stress Agent

**Goal:** Predict tree-fall likelihood and power grid failure probability from wind telemetry and document-extracted tree density and outage history.

**Postgres Tools:**
```
get_wind_current(location_id)
get_wind_historical(location_id, window_hours)
get_power_outage_events(location_id, window_days)
```

**Document Tools:**
```
list_document_indexes(document_type="tree_density_map", ward_name)
list_document_indexes(document_type="bescom_report", ward_name)
fetch_document_section(document_id, section_id)
```

**Key reasoning logic:**
- `wind_gust_kmh`, not average wind speed, is the primary tree-fall predictor
- Tree density and fall-prone species data comes from BBMP tree density map document sections
- `fault_type = treefall` in `power_outage_event` is the direct calibration signal for the scoring model
- `outage_type = planned` is excluded from risk scores — only unplanned outages are relevant
- Powerline proximity data extracted from BESCOM document sections

**Level-1 Output:**
```json
{
  "agent": "infrastructure",
  "confidence": 0.79,
  "status": "ok",
  "data": {
    "treefall_risk_by_zone": {},
    "power_outage_probability": {},
    "at_risk_corridors": [],
    "maintenance_alerts": []
  },
  "citations": [],
  "data_freshness": {}
}
```

---

### Logistics Disruption Agent

**Goal:** Estimate time-to-destination delay factor for key Bangalore corridors correlated with rainfall and waterlogging data.

**Postgres Tools:**
```
get_traffic_current(location_id)
get_traffic_historical(corridor_name, time_band)
get_waterlogging_incidents(location_id)
```

**Document Tools:**
```
list_document_indexes(document_type="flood_postmortem", ward_name)
fetch_document_section(document_id, section_id)
```

**Key reasoning logic:**
- `rainfall_mm_1h` + `corridor_name` + `time_band` + `weekday_weekend_flag` maps to delay factor — agent reasons over this, no regression at query time
- `waterlogging_flag` on traffic segments indicates immediate closure risk
- `heavy_vehicle_share` matters for ORR and Hosur Road — heavier corridors degrade faster in rain
- Flood post-mortem traffic sections provide historical calibration for corridor-specific thresholds

**Key monitored corridors:**
ORR, Sarjapur Road, Hosur Road, Bellary Road, Mysore Road, KR Puram

**Level-1 Output:**
```json
{
  "agent": "logistics",
  "confidence": 0.84,
  "status": "ok",
  "data": {
    "ttd_delay_factor_by_corridor": {},
    "blocked_routes": [],
    "alt_route_suggestions": [],
    "threshold_alerts": {}
  },
  "citations": [],
  "data_freshness": {}
}
```

---

## 3. Domain Agent Tool Design

### Shared vs Agent-Owned Tools

Weather data is consumed by multiple agents. Rather than each agent defining its own `get_weather_current()`, shared tools live in a common module:

```
adk_server/
├── tools/
│   └── shared/
│       ├── weather_tools.py       -- used by flood, heat, infra, logistics agents
│       ├── location_tools.py      -- used by all agents (ward_id resolution)
│       └── document_tools.py      -- used by all agents (index + section fetch)
```

Agent-specific Postgres tools live inside each agent's own tools folder:

```
agents/flood/tools/pg_tools.py     -- lake_hydrology, flood_incident queries
agents/heat/tools/pg_tools.py      -- aqi_observation, ward_profile queries
agents/infra/tools/pg_tools.py     -- power_outage_event queries
agents/logistics/tools/pg_tools.py -- traffic_segment_observation queries
```

### All Tools Must Be Async

All tool functions must be `async def` for `asyncio.gather()` parallel dispatch to work correctly. A synchronous tool in any agent will block the event loop and negate the parallelism benefit.

```python
# Correct
async def get_rainfall_current(location_id: str) -> dict:
    async with db_pool.acquire() as conn:
        ...

# Wrong — blocks event loop
def get_rainfall_current(location_id: str) -> dict:
    with db_pool.acquire() as conn:
        ...
```

---

## 4. Session and Context Management

### Session Flow

```
User sends message
        ↓
Backend loads session history from Postgres (conversation_history table)
        ↓
Backend sends { session_id, message, history[], user_role } to ADK server
        ↓
Chat Agent reads session context
        ↓
Agent processes and responds
        ↓
Backend saves updated turn to conversation_history
```

### Session History Format

The `history` array passed to the ADK server on each request contains the last N conversation turns:

```json
[
  { "role": "user", "content": "What is the flood risk in Bellandur tonight?" },
  { "role": "assistant", "content": "Based on current lake levels at 89%..." },
  { "role": "user", "content": "What about Koramangala?" }
]
```

The Chat Agent uses this history for context retention — "what about Koramangala?" resolves correctly because the previous turn established the flood risk context.

### Location Resolution

All domain agent tools take `location_id` as input, not freeform text. The Chat Agent resolves location references before calling any domain agent:

```
User: "Indiranagar 100ft Road" or "Bellandur" or "HSR Layout Sector 2"
        ↓
Chat Agent calls: resolve_location(text) → location_id from location_master
        ↓
location_id passed to all domain agent tool calls
```

The `location_master` table handles aliases — "Bellanduru", "Bellandur Lake area", "Bellandur ward" all resolve to the same `location_id`.

### Context Window Management

Each agent call receives:
- The resolved location context
- The current session turn (user message)
- Relevant session history (last N turns, not full history)
- Retrieved document sections (only the specific sections identified from the index)

Agents never load full documents into context. They load only the section text identified by navigating the JSON index. This keeps context predictable and within budget.

---

## 5. JSON Output Contract

### Level-1 — Per Agent Payload Envelope

Every domain agent returns this shape, enforced by Pydantic v2 strict mode:

```json
{
  "agent": "flood_vulnerability",
  "query_id": "uuid-xyz",
  "timestamp": "2024-07-15T18:30:00+05:30",
  "confidence": 0.87,
  "status": "ok | partial | error",
  "data": {},
  "citations": [
    {
      "type": "database",
      "table": "lake_hydrology",
      "record_id": "lake_003",
      "field": "fill_percentage"
    },
    {
      "type": "document",
      "document_id": "drainage_plan_bbmp_2019",
      "section_id": "s4_2",
      "section_title": "ORR Culvert Capacity Analysis",
      "page": 84
    }
  ],
  "data_freshness": {
    "telemetry_lag_seconds": 42,
    "last_pg_query_at": "2024-07-15T18:29:58+05:30",
    "stale_sources": []
  },
  "errors": []
}
```

**Status values:**
- `ok` — all tools returned data, confidence above threshold
- `partial` — some tools returned data, some failed or returned low confidence. Never silently dropped — always surfaced to user with a warning
- `error` — agent could not complete reasoning. User receives explicit "insufficient data" message

### Level-2 — Unified Risk Scorecard

The Root Agent runs a pure Python merge function over all Level-1 payloads. No LLM call in this step — deterministic.

```json
{
  "scorecard_id": "uuid-abc",
  "generated_at": "2024-07-15T18:30:05+05:30",
  "query_context": "Risk scorecard for Bellandur",
  "neighborhoods": [
    {
      "name": "Bellandur",
      "ward_id": "ward_042",
      "flood_probability": 0.91,
      "flood_risk_tier": "CRITICAL",
      "power_outage_risk": 0.62,
      "traffic_delay_index": 2.4,
      "heat_health_risk": 0.22,
      "treefall_risk": 0.38,
      "barricade_recommended": true,
      "barricade_locations": ["ORR underpass km 14", "Agara underpass"]
    }
  ],
  "key_drivers": [],
  "global_summary": {
    "critical_zones": 2,
    "high_risk_zones": 4,
    "overall_emergency_posture": "ELEVATED"
  },
  "data_freshness": {}
}
```

---

## 6. Agentic RAG — Document Intelligence

### Approach

No vector database. Documents are converted to structured text and indexed with a JSON Table of Contents. Agents navigate like a human expert — read the index, identify the relevant section, fetch only that section.

### JSON Index Structure

```json
{
  "document_id": "drainage_plan_bbmp_2019",
  "title": "BBMP Stormwater Drainage Master Plan",
  "agency": "BBMP",
  "document_type": "drainage_plan",
  "published_at": "2019-03",
  "wards_covered": ["Bellandur", "Sarjapur", "Koramangala"],
  "total_pages": 210,
  "table_of_contents": [
    {
      "section_id": "s4_2",
      "title": "ORR Corridor Culvert Capacity Analysis",
      "page_start": 82,
      "page_end": 89,
      "summary": "Capacity ratings and failure thresholds for underpasses on ORR",
      "wards_mentioned": ["Bellandur", "Koramangala"],
      "contains_thresholds": true,
      "contains_recommendations": true,
      "text_file": "drainage_plan_bbmp_2019_s4_2.txt"
    }
  ]
}
```

### Agent Document Tools

Two tools shared across all agents:

```python
async def list_document_indexes(
    document_type: str,
    ward_name: str | None = None
) -> list[dict]:
    """Returns matching index JSONs for the agent to reason over"""

async def fetch_document_section(
    document_id: str,
    section_id: str
) -> str:
    """Returns full text of a specific document section"""
```

**Agent workflow:**
1. Call `list_document_indexes` with document type and ward name
2. Reason over the returned Table of Contents entries to identify the right `section_id`
3. Call `fetch_document_section` with the identified `section_id`
4. Reason over the section text alongside Postgres data
5. Cite `document_id` + `section_id` + `page` in the Level-1 payload

### File Storage Layout

```
/documents/
    raw/          -- original PDFs kept for audit and re-processing
    indexes/      -- one JSON index file per document
    sections/     -- one .txt file per document section
```

### Documents Indexed

| Document | Type | Primary Agent |
|---|---|---|
| BBMP Stormwater Drainage Master Plan | drainage_plan | Flood |
| September 2022 Bangalore Flood Post-Mortem | flood_postmortem | Flood, Logistics |
| IMD Weather Bulletins (monsoon season) | imd_bulletin | Flood, Heat |
| BBMP Urban Tree Density Maps | tree_density_map | Infrastructure |
| BESCOM Annual Incident Reports | bescom_report | Infrastructure |
| Climate Resilience Research Papers | resilience_paper | Heat |

---

## 7. Guardrails

### Three-Layer Input Guardrail (Chat Agent)

**Layer 1 — Hard rules (no LLM cost, applied first):**
- Block off-domain queries — UrbanClimate AI is Bangalore climate risk only
- Strip prompt injection patterns before any agent receives the input
- Enforce query length limits
- Tool-level protected data gate — protected tier tools not registered in public sessions

**Layer 2 — Semantic similarity check:**
- Golden set of ~30 in-domain example queries embedded at startup
- Cosine similarity of new query vs golden set — below threshold triggers clarification request
- No extra LLM call needed for narrow domain

**Layer 3 — LLM classifier (borderline only):**
- Only invoked when semantic similarity is inconclusive
- Avoids adding latency and cost to every query

### Per-Agent Guardrails

| Layer | Guardrail | Mechanism |
|---|---|---|
| Input | Domain relevance | Semantic similarity vs golden query set |
| Input | Injection filter | Pattern matching and sanitization |
| Input | Protected data gate | Tool-level access by role |
| Root Agent | Intent confidence gate | Clarification if confidence below 0.6 |
| All Agents | Citation grounding | Every claim references a DB record ID or document section ID |
| All Agents | Confidence threshold | Payloads below 0.5 confidence marked as `partial` |
| All Agents | Data freshness | Stale sources flagged in every response |
| Chat Agent | Hallucination filter | NL output checked against Level-1 source payloads |
| Output | Schema validation | Pydantic v2 strict mode on all payloads |
| Output | Partial result handling | Never silently dropped — always surfaced with warning |

### Security Model

**Public tier:** weather, AQI, lake levels, traffic, flood history, ward-level risk scores.

**Protected tier:** sewage and drainage infrastructure detail, power grid topology, specific building plans.

**Core principle:** Security lives at the tool layer, not the prompt layer. Protected tier tools are simply not registered in public role sessions. No prompt can override this regardless of what it says.

---

## 8. Evals Strategy

### Four Eval Types

**Type 1 — Retrieval Evals (deterministic)**

Postgres tool tests:
- Given a query, assert correct location returned, correct time window, correct columns, correct row count
- Pure unit tests, fully deterministic, no LLM involved
- Target: > 95% correctness

Document index retrieval:
- Golden set of 20-30 queries paired with known correct document sections
- Metric: Was the correct section in the top result from `list_document_indexes`?
- Target: > 90% hit rate

---

**Type 2 — Reasoning Evals (scenario-based)**

Use September 2022 Bangalore flood as the primary calibration ground truth.

Example scenario:
```
Input conditions (from 2022 flood data):
  rainfall_mm_3h = 62 for Bellandur ward
  lake fill_percentage = 94
  overflow_status = true

Expected output assertions:
  flood_probability > 0.85
  barricade_recommended = true
  barricade_locations contains "ORR underpass km 14"
  traffic_delay_index > 2.0 for ORR corridor
```

Build 15-20 scenarios covering:
- September 2022 flood events (primary calibration set)
- Known high AQI days from CPCB records
- Known major traffic disruption days
- Known power outage cluster events correlated with wind events

Target: > 80% precision against ground truth

**Critical dependency:** Reasoning evals are only valid if mock data is seeded with verified September 2022 flood dates, rainfall measurements, and affected ward data before any eval is written.

---

**Type 3 — Output Faithfulness**

Citation coverage (always on, built into guardrails):
- Every factual claim in NL output must reference a DB record ID or document section ID
- Claims without citations are flagged automatically
- Target: 100% citation coverage

LLM-as-judge (eval suite only, selective):
- Applied only to the two highest-consequence output types:
  - Flood barricade recommendations
  - Health advisories for sensitive populations
- Not applied to all outputs — cost and latency constraint

---

**Type 4 — Conversational Quality**

10-15 multi-turn conversation traces testing:
- Compound query routing to correct domain agents
- Context persistence — "what about Koramangala?" after a Bellandur answer resolves correctly
- Ambiguous query handling — agent asks for clarification rather than guessing

Target: > 90% routing accuracy

### Eval Metrics Summary

| Eval Type | Metric | Target |
|---|---|---|
| Postgres tool retrieval | Query correctness | > 95% |
| Document section retrieval | Correct section hit rate | > 90% |
| Flood reasoning | Precision vs 2022 ground truth | > 80% |
| Citation coverage | % claims cited | 100% |
| Conversation routing | Routing accuracy | > 90% |

### Fixture Files

```
tests/evals/fixtures/
    flood_2022_scenarios.json      -- verified September 2022 input conditions + expected outputs
    golden_retrieval_set.json      -- 20-30 query → correct section pairs
    conversation_traces.json       -- 10-15 multi-turn conversation traces
```

---

## 9. Open Design Gaps

These are known open items that must be resolved before or during implementation.

---

**Gap 1 — Mock Data Temporal Patterns**

Mock data must respect Bangalore-specific seasonal and diurnal patterns. If it does not, evals pass on fake data and fail on real data.

Patterns to respect:
- Rainfall peaks June–October, near-zero November–May
- AQI worse November–January, especially mornings 7-10am and evenings 6-9pm
- Traffic peaks 8-10am and 5-8pm on weekdays, lighter weekends
- Power outages correlate with wind gust events and heavy rainfall, not uniformly distributed
- Lake fill levels rise sharply after 3 or more consecutive rain days

A mock data generator that respects these distributions needs to be built before evals are written.

---

**Gap 2 — Orchestrator Intent Classification Detail**

- Exact confidence threshold values for routing decisions
- Behaviour when a query spans 3 or more domains simultaneously
- Merge behaviour when one agent returns `status: partial` or `status: error`
- Whether a partial scorecard is returned with a warning or held until all agents complete

---

**Gap 3 — Prompt Design Per Agent**

- System prompt template for each domain agent
- How Postgres rows are formatted before injection — JSON, table, or natural language
- How document section text is formatted before injection
- Token budget per agent — how many rows and section characters fit before hitting context limits
- Eviction strategy — what gets dropped first when context is full

---

**Gap 4 — Local Development Setup**

- Postgres initialisation and seeding steps from scratch
- Document pipeline — PDF to markdown to JSON index to section .txt files
- Required environment variables across all three layers
- Steps to run the full system locally and verify it is working end-to-end

---

**Gap 5 — Failure Modes and Retry Logic**

For internal government use, a confident wrong answer is strictly worse than "insufficient data to answer reliably."

Failure modes to define:
- Postgres unreachable — what does the user see?
- Document index returns no matching sections — agent degrades gracefully or hard fails?
- One domain agent times out — partial scorecard returned or wait and retry?
- All agents return low confidence — how is this communicated to the user?

---

*UrbanClimate AI — Agents & ADK Reference v1.0*
*Internal use — Bengaluru Climate Risk Intelligence Platform*
