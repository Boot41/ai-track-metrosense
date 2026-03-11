# UrbanClimate AI System — Architecture & Design Document
### Bengaluru Climate Risk Intelligence Platform (Google ADK)
### Version 4.0 — Normalized Schema, Agentic RAG, No Vector DB, 12 Tables Final

---

## Table of Contents

1. System Overview
2. Architecture Decisions & Rationale
3. Agent Architecture — Final Design
4. High-Level Query Flow
5. Domain Agents — Detailed Design
6. Structured JSON Output Design
7. Output Modes — Text, Chart, Scorecard
8. Data Architecture Overview
9. PostgreSQL Schema — Final Normalized Tables
10. Agentic RAG — Document Intelligence Layer
11. Guardrails & Security
12. Evals Strategy
13. Three-Layer System Architecture
14. Technology Stack
15. Project Folder Structure
16. Open Gaps — To Be Addressed

---

## 1. System Overview

UrbanClimate AI is a **multi-agent orchestration system** built on Google ADK. It serves city planners, BBMP disaster teams, and logistics companies by fusing real-time sensor telemetry, PostgreSQL historical data, and unstructured documentation (IMD bulletins, flood post-mortems, drainage master plans) into actionable, explainable risk intelligence for Bangalore.

**Core design principles locked in:**
- Internal government use only for now — auth and public access handled later
- Purely agentic conversation — no SSE, no streaming UI
- Text-first responses — charts and scorecards are progressive, on-demand
- Every answer must be grounded in cited data — no hallucinated risk scores
- Data freshness indicator on every response so decision-makers know how current the data is
- No vector database — documents are converted to structured JSON indexes and navigated agentically
- Normalized Postgres schema — raw sensor/telemetry data only, no derived or computed fields in DB

---

## 2. Architecture Decisions & Rationale

### Decision 1 — Agent Count: 1 Orchestrator + 5 Domain Agents, No Sub-Agents

**What was considered:** Original design had 1 Orchestrator + 5 Domain Agents + 2-3 Sub-Agents per domain = 12-15 total agents.

**Problem:** Too many agents managing context and state creates debugging nightmares. A failure anywhere in the chain is hard to trace. Testing compound queries requires mocking 4-5 agent boundaries simultaneously. The Orchestrator ends up owning complex glue logic which contradicts the thin orchestrator principle.

**Decision:** Flatten to **1 Orchestrator + 5 Domain Agents**. Each domain agent directly owns its tools — both Postgres query tools and Agentic RAG document tools. Sub-agents are a refactoring step for later if a specific domain agent becomes too large, not a starting point.

**Why this works for Bangalore scope:** This is a city-specific internal system in testing. Query volume and complexity do not justify the overhead of sub-agent management.

---

### Decision 2 — Structured JSON Output: A Discipline, Not an Agent

**What was considered:** A dedicated JSON Output Agent that formats final responses.

**Problem:** Adds a redundant LLM call, introduces a fragile parsing step, and creates an unnecessary agent boundary.

**Decision:** JSON output is enforced as a **typed contract at every agent boundary** using Pydantic v2 strict mode. Every domain agent returns a Level-1 typed payload. The Orchestrator runs a pure Python merge function to produce Level-2 structured blocks (risk card/artifact) when requested and available. The Chat Agent then returns the canonical Level-2 user delivery contract for the frontend. No extra formatting agent is added.

```
Domain Agent Output  →  Pydantic Level-1 Payload  (per domain)
Orchestrator Merge   →  Level-2 Structured Blocks  (deterministic)
Chat Agent Output    →  Level-2 User Delivery Contract (single frontend shape)
```

---

### Decision 3 — Output Modes: Text First, Progressive Enhancement

**Three output modes exist:**

**Mode 1 — Conversational Text (default)**
Every query gets a clean NL answer. This is always the primary response.

**Mode 2 — Chart (on follow-up)**
If a chart would genuinely improve understanding such as trend queries or comparative queries, the system appends a follow-up prompt: "Would you like to see this as a chart?" User replies yes and the chart is generated. This keeps the user in control and avoids over-engineering the response layer.

**Mode 3 — Risk Scorecard (triggered explicitly)**
Two trigger mechanisms:
- **Button trigger** — dedicated UI button asks user for a ward/location and generates full scorecard for that zone
- **NL trigger** — if the user's query contains words like "risk", "scorecard", "vulnerability", "assessment", "how vulnerable is" for a specific place, scorecard generation kicks in automatically

**Important:** "summary" is intentionally excluded from NL triggers because it is too generic and can be used in non-scorecard contexts.

---

### Decision 4 — Zone Registry: Bangalore Major Wards Only

The system recognizes Bangalore's major BBMP wards as canonical zones. A `location_master` table with canonical names, aliases, and geometry is the grounding layer. This prevents the LLM from misinterpreting freeform location references.

Examples: Bellandur, Sarjapur, Koramangala, Whitefield, Hebbal, Manyata Tech Park, Yelahanka, BTM Layout, Jayanagar, Peenya, KR Puram, Silk Board.

---

### Decision 5 — No SSE, Purely Agentic

The system is conversational and agentic. No server-sent events, no streaming token output. Responses are returned as complete payloads from agent execution.

---

### Decision 6 — Authentication: Deferred

Currently internal government use only. No authentication layer is implemented in v1. When the system is made public, role-based access will be added — specifically to protect the protected data tier covering power grid topology, sewage infrastructure, and building plans. This is a known open item.

**Two data tiers defined for when auth is added:**
- **Public tier** — weather, AQI, lake levels, traffic, flood history, ward-level risk scores
- **Protected tier** — sewage and drainage infrastructure detail, power grid topology, specific building plans. BBMP and government roles only.

**Security principle locked in:** Security cannot live only in the prompt. Protected tier tools must not be exposed to public role sessions regardless of prompt content. Tool-level access control, not prompt-level.

---

### Decision 7 — Data Freshness Indicator

Every agent response includes a `data_freshness` block telling the user when the underlying data was last updated. A BBMP disaster officer acting on 6-hour-old rainfall data needs to know that. This is non-negotiable for government internal use.

```json
"data_freshness": {
  "telemetry_lag_seconds": 42,
  "last_imd_bulletin": "2024-07-15T06:00:00+05:30",
  "pg_query_time_ms": 310,
  "stale_sources": []
}
```

---

### Decision 8 — Real-World Data Strategy

The Postgres schema is not a replica of any single real-world database. In reality BESCOM stores outage logs in a proprietary OMS, BBMP drainage data exists in scattered Excel files and physical maps, KSNDMC lake levels are published as PDFs and HTML tables, and IMD data comes as fixed-width text files.

The Postgres schema is a **designed consolidation layer** — real-world sources are cleaned, transformed, and loaded into this schema. For development the data is mocked to mirror realistic patterns. The developer will find real datasets from IMD, CPCB OpenAQ, KSNDMC, BESCOM annual reports, Uber Movement, and TomTom Move, then mirror them into the mock database.

---

## 3. Agent Architecture — Final Design

### Agent Hierarchy

```
ADK Runner (infrastructure — not designed, just configured)
    │
    ▼
Root Agent (Orchestrator — routing, state, guardrails, parallel dispatch)
    │
    ▼
Chat Agent (main conversational interface — only agent user talks to)
    │
    ├── Flood Vulnerability Agent      (sub-agent)
    ├── Heat & Health Agent            (sub-agent)
    ├── Infrastructure Stress Agent    (sub-agent)
    └── Logistics Disruption Agent     (sub-agent)
```

### Key Decisions on This Structure

**Runner:** The ADK Runner is not an agent you design. It is the ADK infrastructure that executes the Root Agent, manages the event loop, and handles tool call cycles. You configure it in one line — `Runner(agent=root_agent)`. It is not a component in the architecture diagram.

**Root Agent:** Pure routing and state management. Never talks to the user directly. Owns parallel dispatch, global guardrails, and deterministic Level-1 to Level-2 structured block merge.

**Chat Agent:** The only agent that has a conversation with the user. Owns session memory, NL synthesis, citation formatting, chart follow-up prompts, and scorecard triggers. It calls domain agents directly — no round-trip back through the Root Agent.

**Domain Agents:** Pure domain reasoning. They are sub-agents registered under the Chat Agent. They own their own Postgres tools and Agentic RAG document tools directly. They never receive user input directly.

**Important guardrail implication:** Because the Chat Agent is the actual entry point for user input, input filtering, injection detection, domain relevance checks, and citation grounding must all live at the Chat Agent level — not assumed to be handled upstream.

### Sub-Agent Future-Proofing

Sub-agents are not used in v1. The signals to introduce them later:
- Any domain agent's tool count exceeds 10-12 and LLM tool selection degrades
- Any domain agent's agent.py file exceeds ~300-400 lines
- Logic is being copy-pasted across two domain agents

The folder structure pre-partitions tool logic by concern inside each agent so splitting into sub-agents is a mechanical refactor, not a rewrite.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                             │
│     Natural Language Input — Planner / BBMP Team / Logistics Co.    │
│     Internal Government Use Only (v1)                                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP POST /chat
                            ▼
                    ┌───────────────┐
                    │   BACKEND     │
                    │   FastAPI     │
                    └───────┬───────┘
                            │ HTTP POST /agent/run (internal)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ADK RUNNER                                         │
│                    Root Agent (Orchestrator)                          │
│                                                                      │
│  • Route intent, manage state bag                                    │
│  • Parallel dispatch via asyncio.gather()                            │
│  • Merge Level-1 payloads → Level-2 structured blocks               │
│  • Apply global guardrails                                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CHAT AGENT                                         │
│            Main conversational interface                             │
│                                                                      │
│  • Only agent the user interacts with                                │
│  • Owns session memory and NL synthesis                              │
│  • Input guardrails live here                                        │
│  • Calls domain agents directly (Option A)                           │
│  • Triggers chart follow-up and scorecard mode                       │
└──┬──────────────┬──────────────┬──────────────┬──────────────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
FLOOD          HEAT &        INFRA          LOGISTICS
VULN           HEALTH        STRESS         DISRUPTION
AGENT          AGENT         AGENT          AGENT
(sub-agent)    (sub-agent)   (sub-agent)    (sub-agent)
   │              │              │              │
   └──────────────┴──────────────┴──────────────┘
                               │
                    Each owns Postgres + Document RAG tools
                    Each returns Level-1 Pydantic Payload
                               │
                    Chat Agent synthesizes NL response
                    Root Agent merges → Level-2 structured blocks
```

---

## 4. High-Level Query Flow

```
User types in chat UI
        │
        │ POST /chat { session_id, message, user_role }
        ▼
Backend (FastAPI)
  • Validates input
  • Loads session history from Postgres
  • Forwards to ADK server
        │
        │ POST /agent/run { session_id, message, history[], user_role }
        ▼
ADK Runner → Root Agent
  • Classifies intent
  • Determines output mode
        │
        ▼
Chat Agent
  • Applies input guardrails
  • Resolves location to ward_id via location_master
  • Fans out to domain agents directly via asyncio.gather()
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
Flood Agent                      Logistics Agent
  • Queries Postgres tools          • Queries Postgres tools
  • Queries Document RAG tools      • Queries Document RAG tools
  • Returns FloodRiskPayload        • Returns LogisticsPayload
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
Chat Agent collects Level-1 payloads
Root Agent merges → Level-2 structured blocks (risk_card/artifact when applicable)
Chat Agent synthesizes canonical Level-2 user response with citations
        │
        │ Complete response JSON
        ▼
Backend
  • Saves session history to Postgres
  • Saves response to conversation log
  • Returns to Frontend
        │
        ▼
Frontend renders NL answer in chat
  + scorecard card if triggered
  + chart follow-up prompt if warranted
```

**Parallel dispatch principle:** Compound queries activate multiple domain agents simultaneously via `asyncio.gather()`. "60mm rain tonight, barricade underpasses and reroute my fleet?" activates Flood + Logistics in parallel, not sequentially. Simple single-domain queries activate one agent only.

**Long query handling:** Complex compound queries can take 5-10 seconds. Since there is no SSE the Frontend shows a loading state. This is acceptable for internal government use. Users are not consumer users expecting instant responses.

---

## 5. Domain Agents — Detailed Design

### 5.1 Flood Vulnerability Agent

**Goal:** Identify flood black spots, predict inundation risk, recommend barricade locations.

**Tools owned directly:**
```
Postgres Tools:
  get_rainfall_current(location_id)
  get_rainfall_historical(location_id, window_hours)
  get_lake_hydrology(lake_id)
  get_flood_incidents_historical(location_id)

Document RAG Tools:
  list_document_indexes(document_type, ward_name)
  fetch_document_section(document_id, section_id)
```

**Key logic:**
- Pre-seeded monitored zones: Sarjapur, Bellandur, Manyata Tech Park, Varthur, Hebbal, KR Puram, Koramangala, Silk Board
- `fill_percentage` + `overflow_status` + `surplus_flow_cusecs` from `lake_hydrology` drives backflow risk
- Rainfall intensity vs drainage capacity — capacity values extracted from drainage plan document sections
- 2022 flood post-mortem sections provide calibration priors for black spot scoring
- Barricade threshold values (mm/hr) come from drainage plan document sections, not hardcoded

**Output — Level-1 FloodRiskPayload (Pydantic):**
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

### 5.2 Urban Heat & Health Agent

**Goal:** Generate neighborhood-specific health advisories from AQI data and UHI research documents.

**Tools owned directly:**
```
Postgres Tools:
  get_aqi_current(location_id)
  get_aqi_historical(location_id, days)
  get_weather_heat_metrics(location_id)
  get_population_vulnerability(ward_id)

Document RAG Tools:
  list_document_indexes(document_type, ward_name)
  fetch_document_section(document_id, section_id)
```

**Key logic:**
- `aqi_category` + `dominant_pollutant` generates specific advisory — not generic messaging
- `elderly_population_pct` + `children_population_pct` from `ward_profile` flags sensitive population zones
- `green_cover_pct` from `ward_profile` is the UHI intensity multiplier
- WHO AQI thresholds applied per pollutant type
- Temperature + humidity from `weather_observation` drives heat stress tier reasoning

**Output — Level-1 HeatHealthPayload (Pydantic):**
```json
{
  "agent": "heat_health",
  "confidence": 0.82,
  "status": "ok",
  "data": {
    "zone_aqi": [],
    "heat_index_map": {},
    "advisories": [],
    "population_risk_tier": "HIGH"
  },
  "citations": [],
  "data_freshness": {}
}
```

---

### 5.3 Infrastructure Stress Testing Agent

**Goal:** Predict tree-fall likelihood and power grid failure probability by combining wind telemetry with tree density and historical outage data.

**Tools owned directly:**
```
Postgres Tools:
  get_wind_current(location_id)
  get_wind_historical(location_id, window_hours)
  get_power_outage_events(location_id, window_days)

Document RAG Tools:
  list_document_indexes(document_type, ward_name)
  fetch_document_section(document_id, section_id)
```

**Key logic:**
- `wind_gust_kmh`, not average wind speed, is the primary tree-fall predictor
- Tree density and fall-prone species data extracted from BBMP tree density map document sections
- Powerline proximity data extracted from BESCOM incident report sections
- `outage_type = planned` is excluded from risk scores — only unplanned outages are relevant
- `fault_type = treefall` outages in `power_outage_event` are the direct calibration signal

**Output — Level-1 InfraPayload (Pydantic):**
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

### 5.4 Logistics Disruption Agent

**Goal:** Estimate Time-to-Destination delay factor for delivery fleets by correlating rainfall thresholds with Bangalore traffic bottleneck data.

**Tools owned directly:**
```
Postgres Tools:
  get_traffic_current(location_id)
  get_traffic_historical(corridor_name, time_band)
  get_waterlogging_incidents(location_id)

Document RAG Tools:
  list_document_indexes(document_type, ward_name)
  fetch_document_section(document_id, section_id)
```

**Key logic:**
- `rainfall_mm_1h` + `corridor_name` + `time_band` + `weekday_weekend_flag` from `traffic_segment_observation` maps to delay factor reasoning
- `waterlogging_flag` on traffic segments indicates immediate closure risk
- `heavy_vehicle_share` matters for ORR and Hosur Road — heavier corridors degrade faster in rain
- Flood post-mortem traffic sections provide historical calibration for corridor-specific thresholds
- Key monitored corridors: ORR, Sarjapur Road, Hosur Road, Bellary Road, Mysore Road, KR Puram

**Output — Level-1 LogisticsPayload (Pydantic):**
```json
{
  "agent": "logistics",
  "confidence": 0.84,
  "status": "ok",
  "data": {
    "ttd_delay_factor_by_zone": {},
    "blocked_routes": [],
    "alt_route_suggestions": [],
    "rainfall_threshold_alerts": {}
  },
  "citations": [],
  "data_freshness": {}
}
```

---

### 5.5 Chat Agent

**Goal:** User-facing conversational layer. Routes to domain agents, synthesizes NL answers, manages session memory, handles follow-up chart prompts.

**Design principle:** Tool-poor, agent-rich. The Chat Agent never queries data directly. Every factual claim it makes is traceable to a domain agent Level-1 payload. This makes hallucination checking deterministic.

**Tools:**
```
  session_memory_read()
  session_memory_write()
  intent_classifier()
  call_domain_agent(agent_name, payload)    -- fan-out to domain agents
  synthesize_nl_response(results[])         -- final LLM call with citations
  guardrail_check(response)
  trigger_chart_followup(data, chart_type)  -- appends follow-up prompt if warranted
```

**Routing examples:**
```
"If 60mm tonight, which underpasses?"      → Flood + Logistics (parallel)
"Compare humidity vs decade average"       → Heat Agent (historical mode)
"Tree-fall risk near MG Road?"             → Infra Agent (zone filter)
"Risk scorecard for Bellandur"             → All agents → structured `risk_card` block
"Will ORR delay cross 1.5x tonight?"       → Logistics Agent only
```

**[ GAP 3 PLACEHOLDER — Orchestrator Intent Classification Detail ]**
Exact trigger word list, handling for queries spanning 3+ domains simultaneously,
and merge behavior when one agent returns status: partial — to be defined.

**Chart follow-up behavior:**
After any trend or comparative answer, Chat Agent evaluates whether a chart would improve understanding. If yes it appends "Would you like to see this as a chart?" On user confirmation a chart spec is generated and returned. Charts are never generated automatically — always requires explicit user confirmation.

---

## 6. Structured JSON Output Design

### Level-1 — Domain Payload Envelope (every agent returns this shape)

```json
{
  "agent": "flood_vulnerability",
  "query_id": "uuid-xyz",
  "timestamp": "2024-07-15T18:30:00+05:30",
  "confidence": 0.87,
  "status": "ok | partial | error",
  "data": {},
  "context_used": {
    "resolved_location_id": "loc_bellandur_001",
    "resolved_location_name": "Bellandur",
    "intent": "flood_risk",
    "time_window": "next_6h",
    "assumptions": [
      "Rainfall threshold sourced from drainage_plan_2019_07 section 4.2"
    ]
  },
  "citations": [
    {
      "type": "database",
      "table": "lake_hydrology",
      "record_id": "lake_003",
      "field": "fill_percentage"
    },
    {
      "type": "document",
      "document_id": "drainage_plan_2019_07",
      "page": 84,
      "section": "4.2 ORR Culvert Capacity"
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

`context_used` is mandatory in Level-1 so downstream synthesis remains explainable and auditable.

### Level-2 — User Delivery Contract (backend to frontend)

```json
{
  "session_id": "uuid",
  "response_mode": "text | scorecard | artifact",
  "response_text": "Bellandur flood risk is high for tonight due to rainfall intensity and lake fill levels.",
  "citations_summary": [
    {
      "source_type": "database",
      "source_id": "lake_hydrology:lake_003",
      "label": "Bellandur fill percentage"
    },
    {
      "source_type": "document",
      "source_id": "drainage_plan_2019_07#section_4_2",
      "label": "ORR culvert capacity"
    }
  ],
  "data_freshness_summary": {
    "telemetry_lag_seconds": 42,
    "stale_sources": []
  },
  "risk_card": null,
  "artifact": null,
  "follow_up_prompt": "Would you like this as a chart?"
}
```

`risk_card` and `artifact` are nullable and populated only when explicitly requested by the user and supported by implemented capabilities.

### Level-2 Structured Block Example — `risk_card`

```json
{
  "risk_card": {
    "scorecard_id": "uuid-abc",
    "generated_at": "2024-07-15T18:30:05+05:30",
    "query_context": "If it rains 60mm tonight, which underpasses need barricading?",
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
        "barricade_recommended": true
      }
    ],
    "global_summary": {
      "total_zones_analyzed": 12,
      "critical_zones": 2,
      "high_risk_zones": 4
    }
  }
}
```

### Scorecard Trigger Summary

| Trigger Type | Mechanism |
|---|---|
| UI Button | User clicks → prompted for ward/location → full scorecard generated |
| NL keyword | "risk", "scorecard", "vulnerability", "assessment", "how vulnerable is [place]" |
| Explicitly excluded | "summary" — too generic, reserved for other conversational uses |

---

## 7. Data Architecture Overview

### Two Sources, One Answer

```
User Query
    │
    ├──────────────────────────────────────┐
    │                                      │
    ▼                                      ▼
PostgreSQL                          Agentic RAG
Structured sensor + telemetry       JSON-indexed documents
    │                                      │
Answers numbers questions:          Answers document questions:
"AQI in Hebbal right now?"          "What does the drainage plan
"Bellandur lake fill % today?"       say about ORR capacity?"
"Outages in KR Puram last month?"   "What did the 2022 post-mortem
                                     say about Sarjapur failures?"
    │                                      │
    └──────────────────┬───────────────────┘
                       │
          Combined into one answer with citations
```

### What Lives Where

| Data Type | Storage | Rationale |
|---|---|---|
| Live sensor readings | Postgres | Time-series queries, joins, aggregations |
| Historical observations | Postgres | Trend and baseline comparisons |
| Reference and static facts | Postgres | Canonical names, lake properties, ward profiles |
| Session and operational data | Postgres | Session management, audit logging |
| Raw documents | File storage | Original PDFs kept for audit and re-processing |
| Document JSON indexes | File storage | Table of contents structure per document |
| Document section text | File storage | Full text per section referenced by index |

### No Vector Database

Documents in this system are domain-specific and well-structured. IMD bulletins have standard formats. Drainage plans have numbered sections. Flood post-mortems have clear chapter structures. Index-based agentic navigation is more deterministic and auditable than embedding-based similarity search for this use case. The agent reads the document index, reasons about which section contains the answer, then fetches only that section. No embeddings, no similarity scores, no black-box retrieval.

---

## 8. PostgreSQL Schema — Final Normalized Tables

**Design rules applied:**
- Raw sensor and reported facts only — no derived or computed fields
- Static entity properties separated into reference tables
- No document-derived tables — handled by Agentic RAG pipeline
- No precomputed/derived tables — handled by pipeline or computed at query time by agents

**Final table count: 12**

---

### Reference Tables

**1. location_master** — canonical zone/ward/colony registry, spine of the DB
```
location_id
canonical_name
location_type          -- ward / colony / neighborhood / lake / road / underpass
aliases                -- array of alternate names
ward_id
ward_name
zone_name              -- North / South / East / West / Central
neighborhood_name
pin_code
latitude
longitude
geometry
created_at
updated_at
```

**2. ward_profile** — static demographic and land character data per ward
```
profile_id
ward_id
population_density
elderly_population_pct
children_population_pct
slum_household_count
green_cover_pct
impervious_surface_pct
data_year              -- census/survey year this data came from
source_name
```

**3. lake_reference** — static physical properties of each lake
```
lake_id
lake_name
lake_type              -- natural / tank / reservoir
location_id
ward_id
latitude
longitude
catchment_area_sqkm
lake_area_sqkm
full_tank_level_meters
max_capacity_mcm
number_of_gates
source_name
```

---

### Sensor / Live Telemetry Tables

**4. weather_observation** — raw readings from AWS/ARG/manual stations
```
observation_id
observed_at
ingested_at
station_id
station_name
station_type           -- AWS / ARG / Manual
source_name
location_id
ward_id
latitude
longitude
elevation_meters

temperature_celsius
humidity_percent
pressure_hpa

wind_speed_kmh
wind_gust_kmh
wind_direction_degrees

rainfall_mm_hourly
rainfall_mm_24hour
rainfall_intensity_mm_hr

visibility_km

data_quality_flag
```

**5. air_quality_observation** — raw readings from CPCB monitoring stations
```
aq_obs_id
observed_at
ingested_at
station_id
station_name
station_type           -- continuous / manual
source_name
location_id
ward_id
latitude
longitude

pm2_5
pm10
no2
so2
co
ozone
nh3

aqi_value
aqi_category           -- Good / Satisfactory / Moderate / Poor / Very Poor / Severe
dominant_pollutant

data_quality_flag
```

**6. lake_hydrology** — live telemetry readings per lake per timestamp
```
lake_obs_id
observed_at
ingested_at
lake_id                -- FK to lake_reference
source_name

water_level_meters
fill_percentage

inflow_cusecs
outflow_cusecs
surplus_flow_cusecs

rainfall_last_1h_mm
rainfall_last_24h_mm

overflow_status
gate_status            -- open / closed / partial
number_of_gates_open
alert_level            -- Normal / Watch / Warning / Danger

encroachment_risk_flag
siltation_risk_flag

data_quality_flag
```

**7. power_outage_event** — historical outage log per incident
```
outage_id
event_id
started_at
restored_at
duration_minutes
location_id
ward_id
zone_name

feeder_id
feeder_name
substation_id
substation_name

outage_type            -- planned / unplanned
fault_type             -- treefall / conductor / transformer / lightning / overload
cause_text
affected_customers
critical_load_affected_flag

wind_speed_kmh_at_time
wind_gust_kmh_at_time
rainfall_mm_1h_at_time
rainfall_mm_24h_at_time

source_name
data_quality_flag
```

**8. traffic_segment_observation** — live and historical congestion per road segment
```
traffic_obs_id
observed_at
ingested_at
road_segment_id
road_name
corridor_name          -- ORR / Sarjapur Road / Hosur Road / Bellary Road
location_id
ward_id
latitude_start
longitude_start
latitude_end
longitude_end

road_class             -- highway / arterial / local
lanes_count
speed_limit_kmh

avg_speed_kmh
free_flow_speed_kmh
travel_time_minutes
free_flow_travel_time_minutes
delay_minutes
congestion_index

heavy_vehicle_share
waterlogging_flag
incident_type
incident_severity

rainfall_mm_1h_at_time
rainfall_mm_3h_at_time

source_name
data_quality_flag
```

**9. flood_incident** — reported flood and waterlogging incidents
```
incident_id
reported_at
resolved_at
location_id
ward_id
neighborhood_name
latitude
longitude

water_depth_cm
road_blocked_flag
vehicles_stranded_flag
property_damage_flag
pump_deployed_flag

source_type            -- bbmp_log / field_report / news / citizen_report
severity               -- low / medium / high / critical
rainfall_mm_1h_at_time
rainfall_mm_3h_at_time

data_quality_flag
```

---

### Backend Operational Tables

**10. sessions**
```
session_id
user_role              -- bbmp_internal / planner / logistics
created_at
last_active_at
total_turns
active_flag
```

**11. conversation_history**
```
turn_id
session_id
role                   -- user / assistant
message
agents_invoked
response_mode          -- text / scorecard / artifact
cited_documents
cited_records
timestamp
latency_ms
```

**12. audit_log**
```
log_id
session_id
turn_id
query_text
intent_classified
agents_invoked
overall_confidence
data_freshness_lag_seconds
stale_sources
error_flag
error_detail
created_at
```

---

### Table Summary

12 tables total. Every table maps directly to a use case or operational necessity. No derived fields, no computed scores, no document metadata — those are handled by the Agentic RAG pipeline outside Postgres.

| # | Table | Type | Serves |
|---|---|---|---|
| 1 | location_master | Reference | All agents — ward, colony, zone resolution |
| 2 | ward_profile | Reference | Heat agent — population vulnerability scoring |
| 3 | lake_reference | Reference | Flood agent — static lake physical properties |
| 4 | weather_observation | Sensor | Flood, heat, infra, logistics agents |
| 5 | air_quality_observation | Sensor | Heat and health agent |
| 6 | lake_hydrology | Sensor | Flood agent — live lake telemetry |
| 7 | power_outage_event | Log | Infrastructure stress agent |
| 8 | traffic_segment_observation | Sensor | Logistics disruption agent |
| 9 | flood_incident | Log | Flood agent — historical incident record |
| 10 | sessions | Operational | Backend — session lifecycle management |
| 11 | conversation_history | Operational | Chat agent — memory and turn history |
| 12 | audit_log | Operational | Audit trail, eval fixtures, debugging |

**What is not in Postgres and why:**

| Removed | Reason |
|---|---|
| document_catalog | Replaced by JSON index files in Agentic RAG pipeline |
| drainage_asset, underpass_risk, grid_asset_risk, tree_canopy_zone | Document-derived — extracted by pipeline, stored as structured JSON sections |
| neighborhood_risk_feature, logistics_weather_delay_model, climate_baseline | Precomputed derived — pipeline responsibility, not raw sensor data |
| historical_city_event | Derived from documents — lives in RAG pipeline output |
| asset_relationship | Linked document-derived assets — no longer needed |

---

## 9. Agentic RAG — Document Intelligence Layer

### Why No Vector Database

Three approaches were evaluated. The decision is to use Agentic RAG with structured JSON indexing — no vector DB.

**Option 1 — Vector DB RAG (ChromaDB / Qdrant)**
Documents are chunked arbitrarily, embedded into vectors, stored in a vector DB, retrieved by cosine similarity at query time.

Pros: scales to thousands of documents, handles fuzzy semantic matches well.

Cons: arbitrary chunking breaks document context, retrieval is a black box — hard to audit why a chunk was returned, embedding model adds infrastructure overhead, accuracy depends on chunk quality which is hard to control for government PDFs that have tables, diagrams, and non-standard formatting.

**Option 2 — Keyword Search + Agentic Tool Use**
Simple keyword/BM25 search over document text, wrapped as an agent tool.

Pros: no embeddings, no vector DB, deterministic. Achieves over 90% of RAG performance for domain-specific documents with consistent terminology.

Cons: misses semantic matches when query language differs from document language.

**Option 3 — Agentic RAG with Structured JSON Index (chosen)**
Documents are converted to clean text, a structured JSON index is built per document mirroring its Table of Contents, and the agent navigates the index to find and fetch only the relevant section.

This approach is known as **PageIndex** — the agent reasons over structure first, navigates like a human expert reading a report, then fetches only the section it needs. No vector DB, no embeddings, fully auditable, every retrieval step is traceable.

**Why this is the right choice for this system:**
- Document set is bounded and known — six document types, not thousands of unknown documents
- Documents are well-structured — drainage plans have numbered sections, IMD bulletins have standard formats, flood post-mortems have clear chapters
- Retrieval must be auditable — a BBMP officer asking "why did the system recommend barricading?" must be able to trace the answer to an exact section and page number
- Deterministic navigation is more reliable than similarity scores for this domain

---

### How It Works

```
PDF / Report / Excel / Any format
        ↓
Convert to clean Markdown or plain text
        ↓
Build JSON index per document
mimicking its Table of Contents structure
Each section gets: section_id, title, page range,
summary, wards_mentioned, metadata flags
        ↓
Store full section text as separate .txt files
each referenced by section_id in the index
        ↓
At query time:
Agent calls list_document_indexes(type, ward)
  → gets matching index JSONs
Agent reads index, reasons about which section_id answers the query
Agent calls fetch_document_section(document_id, section_id)
  → gets only that section text, not the full document
Agent cites document_id + section_id + page range in response
```

---

### JSON Index Structure Per Document

```json
{
  "document_id": "drainage_plan_bbmp_2019",
  "title": "BBMP Stormwater Drainage Master Plan",
  "agency": "BBMP",
  "document_type": "drainage_plan",
  "published_at": "2019-03",
  "wards_covered": ["Bellandur", "Sarjapur", "Koramangala", "Whitefield"],
  "source_path": "/documents/raw/drainage_plan_bbmp_2019.pdf",
  "total_pages": 210,
  "total_sections": 24,
  "table_of_contents": [
    {
      "section_id": "s1",
      "title": "Introduction and Scope",
      "page_start": 1,
      "page_end": 8,
      "summary": "Overview of drainage network coverage and methodology",
      "wards_mentioned": [],
      "contains_thresholds": false,
      "contains_recommendations": false,
      "text_file": "drainage_plan_bbmp_2019_s1.txt"
    },
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

**Key metadata flags on each section:**
- `wards_mentioned` — allows filtering by location before agent reads content
- `contains_thresholds` — flood agent prioritizes sections with threshold values
- `contains_recommendations` — agent knows this section has actionable guidance
- `text_file` — direct pointer to the section content file, no search needed

---

### File Storage Layout

```
/documents/
    raw/
        drainage_plan_bbmp_2019.pdf
        imd_bulletin_2024_july.pdf
        flood_postmortem_2022.pdf
        bbmp_tree_density_map.pdf
        climate_resilience_paper.pdf
        bescom_incident_report_2023.pdf
    indexes/
        drainage_plan_bbmp_2019_index.json
        imd_bulletin_2024_july_index.json
        flood_postmortem_2022_index.json
        bbmp_tree_density_map_index.json
        climate_resilience_paper_index.json
        bescom_incident_report_2023_index.json
    sections/
        drainage_plan_bbmp_2019_s1.txt
        drainage_plan_bbmp_2019_s4_2.txt
        flood_postmortem_2022_s3_1.txt
        imd_bulletin_2024_july_s2.txt
        ...
```

Raw PDFs are kept for audit — a user can always ask to see the original source document. Indexes and section text files are what the agents actually use at query time.

---

### Agent Tools for Document Access

Every domain agent gets two document tools. These are the only tools that touch the file system.

```python
list_document_indexes(document_type: str, ward_name: str) -> list[dict]
    # Returns matching index JSONs for the agent to reason over
    # Filters by document_type and ward coverage before returning
    # Agent uses the table_of_contents to decide which section to fetch

fetch_document_section(document_id: str, section_id: str) -> str
    # Returns full text of a specific section
    # Agent never loads a full document — only the section it needs
    # section_id comes from reasoning over the index
```

The agent's reasoning flow:
```
1. list_document_indexes("drainage_plan", "Bellandur")
   → returns drainage_plan_bbmp_2019_index.json

2. Agent reads table_of_contents
   → identifies s4_2 "ORR Corridor Culvert Capacity" as relevant
   → sees contains_thresholds: true, wards_mentioned: ["Bellandur"]

3. fetch_document_section("drainage_plan_bbmp_2019", "s4_2")
   → returns section text with exact capacity values and thresholds

4. Agent cites: drainage_plan_bbmp_2019 § s4_2, pages 82-89
```

---

### Trade-off Summary

| Dimension | Vector DB RAG | Keyword Search | Agentic JSON Index (chosen) |
|---|---|---|---|
| Auditability | Low — black box retrieval | Medium — keyword visible | High — exact section and page cited |
| Setup complexity | High — embeddings, vector DB infra | Low | Medium — manual index building |
| Scales to 1000s of docs | Yes | Yes | No — best for bounded doc sets |
| Works for structured docs | Medium | Medium | High — mirrors document structure |
| Retrieval determinism | Low — similarity scores vary | High | High — agent reasons explicitly |
| Infrastructure cost | High | Low | Low |
| Right for this system | No | Partial | Yes |

---

### Documents to Process

| Document | Type | Wards Covered | Used By Agent |
|---|---|---|---|
| IMD Weather Bulletins | imd_bulletin | All Bangalore | Flood, heat |
| BBMP Drainage Master Plan | drainage_plan | All wards | Flood |
| 2022 Flood Post-Mortem | flood_postmortem | Bellandur, Sarjapur, Varthur, KR Puram | Flood, logistics |
| BBMP Tree Density Maps | tree_density_map | All wards | Infrastructure |
| Climate Resilience Papers | resilience_paper | All Bangalore | Heat |
| BESCOM Incident Reports | bescom_report | All wards | Infrastructure |

---

### Trade-offs vs Vector DB RAG

| Dimension | Agentic RAG (this system) | Vector DB RAG |
|---|---|---|
| Setup complexity | Low — convert PDF, build JSON index | High — embedding model, vector DB infra |
| Retrieval determinism | High — agent reasons over structure | Low — depends on embedding quality |
| Auditability | Full — exact section cited | Partial — chunk source cited |
| Scale | Bounded document sets only | Scales to thousands of docs |
| Maintenance | No embedding model to update | Embeddings must be rebuilt on doc changes |
| Best for | Well-structured domain docs | Large fuzzy unstructured corpora |

**[ GAP 4 PLACEHOLDER — Prompt Design Per Agent ]**
How JSON index content and section text are formatted and injected into
each agent's LLM context — token budget management, injection templates,
what gets dropped when context is full — to be defined.

---

## 10. Guardrails & Security

### Input Guardrail Strategy — Three Layers

**Layer 1 — Hard rules (first, no LLM cost)**
- Block obvious off-domain queries
- Detect and strip prompt injection patterns before any agent receives the input
- Enforce query length limits
- Tool-level protected data access control by user role — a public session simply does not have protected tier tools registered

**Layer 2 — Semantic similarity check**
- Golden set of ~30 in-domain example queries embedded at startup
- Cosine similarity of new query vs golden set — below threshold triggers clarification request
- Right-sized for a narrow domain, no extra LLM call needed

**Layer 3 — LLM classifier (borderline only)**
- Only used when semantic similarity is inconclusive
- Avoids adding latency and cost to every query

### Guardrails Per Layer

| Layer | Guardrail | Mechanism |
|---|---|---|
| Input | Domain relevance check | Semantic similarity vs golden query set |
| Input | Prompt injection filter | Pattern matching and sanitization |
| Input | Protected data gate | Tool-level access by role, not prompt-level |
| Orchestrator | Intent confidence gate | Clarification request if classifier below 0.6 |
| All Agents | Citation grounding | Every claim references a DB record ID or document section ID |
| All Agents | Confidence threshold | Payloads below 0.5 confidence marked as partial |
| All Agents | Data freshness | Stale sources flagged in every response |
| Chat Agent | Hallucination filter | NL output checked against source payloads |
| Output | Schema validation | Pydantic v2 strict mode on all payloads |
| Output | Partial result handling | One agent failure returns partial result with warning, never silent drop |

### Security Model

**Public tier:** weather, AQI, lake levels, traffic, flood history, ward-level risk scores.

**Protected tier:** sewage and drainage infrastructure detail, power grid topology, specific building plans. BBMP and government roles only.

**Core principle:** Security lives at the tool layer, not the prompt layer. Protected tier Postgres tools and document RAG tools are simply not registered in public role sessions. No prompt can override this.

**Authentication:** Deferred to v2. Currently internal government use only.

---

## 12. Evals Strategy

### Four Eval Types

**Type 1 — Retrieval Evals (deterministic, no LLM involved)**

Postgres tools:
- Given a query, assert correct ward returned, correct time window, correct columns, correct row count
- Pure unit tests, fully deterministic

Document index retrieval:
- Golden set: 20–30 queries paired with known correct source document sections
- Primary metric: Hit rate — was the correct section returned by `list_document_indexes`?

**Type 2 — Reasoning Evals (scenario-based, ground truth from 2022 flood event)**

Example scenario:
```
Input conditions:
  rainfall_mm_3h = 62 for Bellandur ward
  lake fill_percentage = 94
  overflow_status = true
  gate_status = open

Expected output assertions:
  flood_probability > 0.85
  barricade_recommended = true
  barricade_locations contains "ORR underpass km14"
  traffic_delay_index > 2.0 for ORR corridor
```

Build 15–20 scenarios covering:
- September 2022 flood events (primary calibration set)
- Known high AQI days from CPCB records
- Known major traffic disruption days
- Known power outage cluster events

**Type 3 — Output Faithfulness**

Option A — Citation coverage (always on, built into guardrails): Every claim in the NL output must have a citation referencing a DB record ID or document section ID. Claims without citations are flagged automatically.

Option B — LLM-as-judge (eval suite only, selective): Applied to the two highest-consequence output types:
- Flood barricade recommendations
- Health advisories for sensitive populations

**Type 4 — Conversational Quality**

10–15 multi-turn conversation traces testing:
- Compound query routing to correct domain agents
- Context persistence across turns ("what about Koramangala?" after a Bellandur answer)
- Ambiguous query handling — does agent ask for clarification vs guess

### Eval Metrics

| Eval Type | Primary Metric | Target |
|---|---|---|
| Postgres retrieval | Query correctness % | > 95% |
| Document section retrieval | Correct section hit rate | > 90% |
| Flood reasoning | Precision vs 2022 ground truth | > 80% |
| Output faithfulness | Citation coverage % | 100% |
| Conversation routing | Routing accuracy % | > 90% |

**Critical dependency:** Evals are only as good as their fixtures. Mock data must be seeded with verified September 2022 flood dates, rainfall measurements, and affected zone data before any reasoning eval is written. This is the calibration foundation.

---

## 13. Technology Stack

| Component | Technology | Notes |
|---|---|---|
| Agent Framework | Google ADK Python | Multi-agent orchestration |
| LLM | Gemini 1.5 Pro / Flash | Via ADK |
| Backend API | FastAPI | API gateway, session management |
| Database | PostgreSQL + SQLAlchemy async | All structured sensor and operational data |
| Document Intelligence | Agentic RAG — JSON index + section files | No vector DB, index-based navigation |
| PDF Processing | Developer-handled pipeline | PDF → Markdown → JSON index + section .txt files |
| Schema Validation | Pydantic v2 strict mode | All agent payloads enforced |
| Testing | pytest + pytest-asyncio | Unit and integration |
| Evals | Custom harness + LLM-as-judge | See section 12 |
| Observability | OpenTelemetry | Agent trace and tool call logging |

---

## 14. Three-Layer System Architecture

### Overview

The system is split into three independently deployable layers. Each layer has a clear responsibility boundary. They communicate via synchronous HTTP REST — no SSE, no WebSockets, no message queues in v1.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                      │
│                    Chat Interface (Web)                              │
│                                                                      │
│  • Chat message input and conversation history display               │
│  • Loading state during agent processing (5-10s complex queries)    │
│  • Scorecard button → prompts for ward/location → renders card       │
│  • Chart rendering when user confirms follow-up chart prompt         │
│  • Stores session_id in local state                                  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP REST POST /chat
                            │ Synchronous — waits for complete response
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND                                      │
│                    FastAPI Server                                    │
│                                                                      │
│  • API gateway — single entry point for all Frontend requests        │
│  • Session management — stores and retrieves conversation history    │
│  • Input validation before anything reaches ADK server               │
│  • PostgreSQL connection pool — all 12 structured tables             │
│  • Document file storage — JSON indexes, section .txt files, raw PDFs│
│  • Response logging — every query and answer saved for audit + evals │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP REST POST /agent/run (internal)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       ADK AI SERVER                                  │
│                    Google ADK Runtime                                │
│                                                                      │
│  • ADK Runner executes Root Agent                                    │
│  • Root Agent → Chat Agent → Domain Sub-Agents                      │
│  • Domain agents connect directly to Postgres + file storage (dev)  │
│  • Returns complete structured response — NL text + nullable blocks  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Communication Pattern

**Frontend → Backend:**
```json
POST /chat
Request:
{
  "session_id": "uuid",
  "message": "If it rains 60mm tonight which underpasses need barricading?",
  "user_role": "bbmp_internal"
}

Response (canonical Level-2 shape):
{
  "session_id": "uuid",
  "response_mode": "text",
  "response_text": "Based on current conditions...",
  "citations_summary": [],
  "data_freshness_summary": {},
  "risk_card": null,
  "artifact": null,
  "follow_up_prompt": null
}
```

**Backend → ADK Server (internal):**
```json
POST /agent/run
Request:
{
  "session_id": "uuid",
  "message": "...",
  "history": [],
  "user_role": "bbmp_internal"
}

Response: same canonical Level-2 shape as above
```

---

### Data Access — Development vs Production

**Development (v1):** Domain agents connect directly to Postgres and the document file system. Fewer hops, faster to build, easier to debug locally.

```
Domain Agent → direct connection → Postgres
Domain Agent → direct file access → /documents/indexes/ and /documents/sections/
```

**Production (future):** Data access moves behind Backend APIs. ADK server becomes fully stateless. Proper security boundaries enforced without changing agent logic.

```
Domain Agent → HTTP → Backend API → Postgres
Domain Agent → HTTP → Backend API → Document file storage
```

The tool function signatures stay identical — only the internals of each tool change from direct access to HTTP calls. This is a clean refactor, not a rewrite.

---

### Responsibility Boundaries

| Concern | Frontend | Backend | ADK Server |
|---|---|---|---|
| Chat UI and message rendering | ✓ | | |
| Session ID management | ✓ | | |
| Chart rendering | ✓ | | |
| Scorecard button | ✓ | | |
| Loading state | ✓ | | |
| Input validation | | ✓ | |
| Session history storage | | ✓ | |
| Postgres connection pool | | ✓ prod | ✓ dev |
| Document file storage (indexes + sections) | | ✓ | |
| Raw PDF storage | | ✓ | |
| Response audit logging | | ✓ | |
| Agent orchestration | | | ✓ |
| NL synthesis | | | ✓ |
| Risk scoring and reasoning | | | ✓ |
| Citation generation | | | ✓ |

---

## 15. Project Folder Structure

```
urbanclimate_ai/
├── main.py                              # Entry point, ADK runner
│
├── backend/                             # FastAPI Backend Server
│   ├── main.py                          # FastAPI app entry point
│   ├── routers/
│   │   ├── chat.py                      # POST /chat endpoint
│   │   └── health.py                    # Health check
│   ├── services/
│   │   ├── session_service.py           # Session history load/save
│   │   ├── adk_client.py                # HTTP client to ADK server
│   │   └── audit_logger.py             # Response audit logging
│   └── db/
│       └── postgres.py                  # Connection pool
│
├── adk_server/                          # ADK AI Server
│   ├── orchestrator/
│   │   ├── agent.py                     # Root OrchestratorAgent
│   │   ├── intent_classifier.py         # Maps NL query to domain intents
│   │   ├── context_manager.py           # Shared session state bag
│   │   └── scorecard_merger.py          # Pure Python Level-1 to Level-2 structured merge
│   │
│   ├── agents/
│   │   ├── shared/
│   │   │   ├── weather_tools.py         # Shared weather Postgres tools (flood, heat, infra, logistics)
│   │   │   ├── location_tools.py        # Location resolution for all agents
│   │   │   └── document_tools.py        # list_document_indexes + fetch_document_section
│   │   │
│   │   ├── flood/
│   │   │   ├── agent.py                 # FloodVulnerabilityAgent
│   │   │   ├── tools/
│   │   │   │   └── pg_tools.py          # lake_hydrology, flood_incident queries
│   │   │   └── schemas.py               # FloodRiskPayload Pydantic model
│   │   │
│   │   ├── heat_health/
│   │   │   ├── agent.py                 # HeatHealthAgent
│   │   │   ├── tools/
│   │   │   │   └── pg_tools.py          # air_quality_observation, ward_profile queries
│   │   │   └── schemas.py               # HeatHealthPayload Pydantic model
│   │   │
│   │   ├── infrastructure/
│   │   │   ├── agent.py                 # InfrastructureStressAgent
│   │   │   ├── tools/
│   │   │   │   └── pg_tools.py          # power_outage_event queries
│   │   │   └── schemas.py               # InfraPayload Pydantic model
│   │   │
│   │   ├── logistics/
│   │   │   ├── agent.py                 # LogisticsDisruptionAgent
│   │   │   ├── tools/
│   │   │   │   └── pg_tools.py          # traffic_segment_observation queries
│   │   │   └── schemas.py               # LogisticsPayload Pydantic model
│   │   │
│   │   └── chat/
│   │       ├── agent.py                 # ChatAgent fan-out and NL synthesis
│   │       ├── session_memory.py        # Rolling window session history
│   │       └── response_synthesizer.py # Final NL with citations
│   │
│   ├── guardrails/
│   │   ├── input_filter.py              # Domain relevance + injection filter
│   │   ├── hallucination_filter.py      # Citation grounding check
│   │   ├── confidence_gate.py           # Block outputs below threshold
│   │   └── data_freshness.py            # Staleness indicator per response
│   │
│   └── schemas/
│       ├── base_payload.py              # Shared Level-1 envelope Pydantic model
│       └── unified_scorecard.py         # Level-2 Unified Risk Scorecard model
│
├── documents/                           # Agentic RAG document storage
│   ├── raw/                             # Original PDFs — kept for audit and re-processing
│   │   ├── drainage_plan_bbmp_2019.pdf
│   │   ├── flood_postmortem_2022.pdf
│   │   ├── imd_bulletin_sample.pdf
│   │   ├── bbmp_tree_density_map.pdf
│   │   ├── bescom_incident_report.pdf
│   │   └── climate_resilience_paper.pdf
│   ├── indexes/                         # One JSON index file per document
│   │   ├── drainage_plan_bbmp_2019_index.json
│   │   ├── flood_postmortem_2022_index.json
│   │   └── ...
│   └── sections/                        # One .txt file per document section
│       ├── drainage_plan_bbmp_2019_s4_2.txt
│       ├── flood_postmortem_2022_s3_1.txt
│       └── ...
│
├── data/
│   └── mock_db/
│       ├── seed_location_master.sql     # Bangalore wards + colonies with aliases
│       ├── seed_ward_profile.sql        # Demographic and land character data
│       ├── seed_lake_reference.sql      # Static lake properties
│       ├── seed_weather.sql             # Mock weather observations
│       ├── seed_aqi.sql                 # Mock AQI observations
│       ├── seed_lake_hydrology.sql      # Mock lake telemetry
│       ├── seed_traffic.sql             # Mock traffic observations
│       ├── seed_outages.sql             # Mock power outage events
│       └── seed_flood_incidents.sql     # 2022 flood incident data — critical for evals
│
├── tests/
│   ├── unit/
│   │   ├── test_flood_agent.py
│   │   ├── test_heat_agent.py
│   │   ├── test_infra_agent.py
│   │   ├── test_logistics_agent.py
│   │   ├── test_chat_agent.py
│   │   └── test_orchestrator.py
│   ├── integration/
│   │   ├── test_compound_query.py       # 60mm rain + underpass end-to-end
│   │   ├── test_scorecard_generation.py
│   │   └── test_partial_failure.py      # One agent fails, others return gracefully
│   └── evals/
│       ├── retrieval/
│       │   ├── eval_postgres_tools.py
│       │   └── eval_document_index.py   # Replaces eval_chroma_retrieval
│       ├── reasoning/
│       │   ├── eval_flood_scenarios.py
│       │   ├── eval_heat_scenarios.py
│       │   ├── eval_infra_scenarios.py
│       │   └── eval_logistics_scenarios.py
│       ├── faithfulness/
│       │   ├── eval_citation_grounding.py
│       │   └── eval_llm_judge.py
│       ├── conversation/
│       │   ├── eval_routing.py
│       │   └── eval_context_retention.py
│       └── fixtures/
│           ├── flood_2022_scenarios.json
│           ├── golden_retrieval_set.json
│           └── conversation_traces.json
│
└── config/
    ├── settings.py                      # DB URLs, model names, thresholds, file paths
    ├── ward_registry.py                 # Bangalore wards and canonical aliases
    └── scorecard_trigger_words.py       # NL trigger vocabulary for scorecard mode
```

---

## 16. Open Gaps — To Be Addressed

These are known open items identified during design. Placeholders are marked in relevant sections above.

---

### Gap 1 — Mock Data Temporal Patterns
**Marker:** Section 11 Guardrails, Section 12 Evals fixtures note

**What is unresolved:** How time-series mock data is generated with realistic seasonal and diurnal patterns.

Bangalore-specific patterns that must be respected:
- Rainfall peaks June–October, near-zero November–May
- AQI worse November–January especially mornings 7–10am and evenings 6–9pm
- Traffic peaks 8–10am and 5–8pm on weekdays, lighter weekends
- Power outages correlate with wind gust events and heavy rainfall, not uniformly distributed
- Lake fill levels rise sharply after 3 or more consecutive rain days

If mock data ignores these patterns, evals will pass on fake data and fail on real data. A mock data generator that respects seasonal and diurnal distributions needs to be designed before evals are written.

---

### Gap 2 — Agent Tool Design Detail
**What is unresolved:** Exact tool definitions — function signatures, which tools are shared across agents vs owned by a single agent.

Weather data is consumed by flood, heat, infra, and logistics agents. If each agent defines its own `get_weather_current()` that is redundant code and inconsistent behavior. A shared tool registry or shared tool module needs to be designed.

Questions to answer:
- Which tools are shared vs agent-owned?
- Exact async function signatures for every tool
- All tools must be async for parallel dispatch via asyncio.gather() to work correctly

---

### Gap 3 — Orchestrator Intent Classification Detail
**Marker:** Section 5.5 Chat Agent routing section

**What is unresolved:**
- Exact trigger word and pattern list for scorecard vs conversational vs chart mode
- Behavior when a query spans 3 or more domains simultaneously
- Merge behavior when one agent returns status partial or error — does Orchestrator return partial scorecard with warning or retry?
- Confidence threshold values for routing decisions

---

### Gap 4 — Prompt Design Per Agent
**Marker:** Section 9 Agentic RAG Layer

**What is unresolved:** How structured Postgres data and document section text are injected into each agent's LLM context window.

Questions to answer:
- System prompt template for each of the 5 domain agents
- How Postgres rows are formatted before injection — JSON, table, or natural language
- How document section text is formatted and truncated before injection
- Token budget per agent — how many rows and how many section characters fit before hitting context limits
- Eviction strategy — what gets dropped first when context is full

---

### Gap 5 — Local Development Setup
**What is unresolved:** End-to-end local setup documentation.
- How Postgres is initialised and seeded from scratch
- How the document pipeline works — PDF → Markdown → JSON index → section .txt files
- Required environment variables across all three layers
- Steps to run the full system locally for the first time and verify it is working end-to-end

---

### Gap 6 — Failure Modes and Retry Logic
**What is unresolved:** System behavior at each possible failure point.
- Postgres unreachable — what does the user see?
- Document index returns no matching sections — agent degrades gracefully or hard fails?
- One domain agent times out — Orchestrator returns partial scorecard or waits and retries?
- All agents return low confidence — how is this communicated to the user?

For internal government use this matters more than in a consumer product. A BBMP disaster officer receiving a confident-sounding wrong answer is strictly worse than receiving "insufficient data to answer reliably at this time."

---

*UrbanClimate AI — Architecture v3.0 | Bengaluru Climate Risk Platform*
*Document reflects full design brainstorm — all decisions locked, three-layer architecture defined, gaps marked for next phase*
