# MetroSense Agent Implementation Spec
### Full Production Agent — Guardrails, Tools, Sub-agent Delegation, Session Persistence
### Status: Approved for Implementation

---

## Locked Decisions (from design session)

| Decision | Choice |
|----------|--------|
| Data access | Option B — agents call backend internal HTTP API (`X-Internal-Token`) |
| Documents | Shared volume mount of `server/Documents_Metrosense/` at `DOCUMENTS_PATH` env var |
| Response mode | Non-streaming — single POST/response, no SSE |
| ADK session state | `InMemorySessionService` (ADK-side) + write-through to `sessions` + `conversation_history` tables (backend-side, after each turn) |
| Agent app name | `metrosense_agent` (replaces `metrosearch_agent`) |
| Root agent name | `root_agent` |

---

## 1. What Changes and Where

### 1.1 Backend changes (`server/`)

| File | Change |
|------|--------|
| `app/api/routes/internal.py` | **NEW** — internal data query endpoints, `X-Internal-Token` gated |
| `app/services/data_service.py` | **NEW** — all SQLAlchemy async queries for internal API |
| `app/services/conversation_service.py` | **NEW** — session upsert + conversation turn persistence |
| `app/services/agent_proxy.py` | **UPDATE** — persist session + turn to DB after ADK response |
| `app/api/router.py` | **UPDATE** — register internal router |
| `app/core/config.py` | **UPDATE** — `agent_app_name = "metrosense_agent"` |
| `app/db/models.py` | **UPDATE** — add `ConversationHistory`, `AuditLog`, `DBSession` models (they exist in migration but not in models.py) |

### 1.2 Agents changes (`agents/`)

| File | Change |
|------|--------|
| `pyproject.toml` | **UPDATE** — add `python-dotenv`, `pydantic>=2.7` |
| `metrosense_agent/` | **NEW** — full agent package (see tree below) |
| `metrosearch_agent/` | **KEEP** — do not delete; rename app_name in backend config only |
| `.env.example` | **UPDATE** — add `BACKEND_INTERNAL_URL`, `DOCUMENTS_PATH` |

### 1.3 Infrastructure changes

| File | Change |
|------|--------|
| `docker-compose.yml` | **UPDATE** — agents service: add volume mount + env vars |

---

## 2. New Agents File Tree

```
agents/
└── metrosense_agent/
    ├── __init__.py                   # exports root_agent for ADK
    ├── agent.py                      # root_agent definition
    ├── prompts.py                    # all instruction strings (no inline strings in agent files)
    ├── subagents/
    │   ├── __init__.py
    │   ├── chat_agent.py             # chat_agent — sole user-facing agent
    │   ├── flood_agent.py            # flood_vulnerability_agent
    │   ├── heat_agent.py             # heat_health_agent
    │   ├── infra_agent.py            # infrastructure_agent
    │   └── logistics_agent.py        # logistics_agent
    └── tools/
        ├── __init__.py
        ├── backend_client.py         # shared HTTP client + all backend internal API calls
        ├── shared/
        │   ├── __init__.py
        │   ├── weather_tools.py      # get_weather_current, get_weather_historical
        │   ├── location_tools.py     # resolve_location, list_locations
        │   └── document_tools.py     # list_document_indexes, fetch_document_section
        ├── flood_tools.py            # get_lake_hydrology, get_flood_incidents
        ├── heat_tools.py             # get_aqi_current, get_aqi_historical, get_ward_profile
        ├── infra_tools.py            # get_power_outage_events
        └── logistics_tools.py        # get_traffic_current, get_traffic_corridor
```

---

## 3. Backend Internal API

### 3.1 Route file: `server/app/api/routes/internal.py`

All routes prefixed `/internal`. Protected by a FastAPI dependency that reads `X-Internal-Token` from the request header and compares to `settings.agent_internal_token`. Returns HTTP 401 on mismatch. This dependency is **not** the same as `require_user` — no DB lookup, no JWT.

```
Dependency: require_internal_token(request: Request, settings: Settings) -> None
```

#### Endpoints

| Method | Path | Query params | Returns |
|--------|------|-------------|---------|
| GET | `/internal/weather/current` | `location_id: str`, `limit: int = 1` | list of weather observation rows |
| GET | `/internal/weather/historical` | `location_id: str`, `hours: int = 24` | list of weather observation rows |
| GET | `/internal/aqi/current` | `location_id: str`, `limit: int = 1` | list of AQI observation rows |
| GET | `/internal/aqi/historical` | `location_id: str`, `days: int = 7` | list of AQI observation rows |
| GET | `/internal/lakes` | `lake_id: str`, `limit: int = 5` | list of lake hydrology rows |
| GET | `/internal/floods` | `location_id: str`, `limit: int = 20` | list of flood incident rows |
| GET | `/internal/outages` | `location_id: str`, `window_days: int = 30` | list of power outage rows |
| GET | `/internal/traffic/current` | `location_id: str`, `limit: int = 5` | list of traffic observation rows |
| GET | `/internal/traffic/corridor` | `corridor_name: str`, `limit: int = 20` | list of traffic observation rows |
| GET | `/internal/locations/resolve` | `name: str` | list of matching location_master rows |
| GET | `/internal/ward/profile` | `ward_id: str` | ward_profile row or null |

All endpoints return JSON arrays (or single object for ward profile). No pagination needed — results are bounded by the `limit` / `window_days` params and the golden dataset size.

#### Response shape convention

Each endpoint returns a plain `list[dict[str, Any]]` — raw column values serialised to JSON. Agents receive this and reason over it. No transformation at the API layer.

Timestamps are serialised as ISO-8601 strings. Booleans remain booleans. Nulls remain nulls.

### 3.2 Service: `server/app/services/data_service.py`

One async function per endpoint. All use `AsyncSession`. Examples:

```python
async def get_weather_current(session, location_id: str, limit: int = 1) -> list[dict]
async def get_weather_historical(session, location_id: str, hours: int = 24) -> list[dict]
async def get_aqi_current(session, location_id: str, limit: int = 1) -> list[dict]
async def get_aqi_historical(session, location_id: str, days: int = 7) -> list[dict]
async def get_lake_hydrology(session, lake_id: str, limit: int = 5) -> list[dict]
async def get_flood_incidents(session, location_id: str, limit: int = 20) -> list[dict]
async def get_power_outages(session, location_id: str, window_days: int = 30) -> list[dict]
async def get_traffic_current(session, location_id: str, limit: int = 5) -> list[dict]
async def get_traffic_corridor(session, corridor_name: str, limit: int = 20) -> list[dict]
async def resolve_location(session, name: str) -> list[dict]
async def get_ward_profile(session, ward_id: str) -> dict | None
```

All queries use `ORDER BY observed_at DESC` (or equivalent timestamp column) to return most-recent-first. Power outages filter `outage_type != 'planned'` by default (only unplanned outages returned). All use `LIMIT` parameter.

`resolve_location` does a case-insensitive ILIKE search across `canonical_name` and `aliases` (JSON array contains).

### 3.3 Router registration

In `server/app/api/router.py`, add:

```python
from app.api.routes import internal
root_router.include_router(internal.router)
```

Internal router is **not** wrapped in the `protected_router` (no JWT dependency). It has its own token check dependency.

---

## 4. Conversation Persistence

### 4.1 DB models to add to `server/app/db/models.py`

Three models missing from models.py (they exist in the migration already):

**`DBSession`** (maps to `sessions` table):
```python
class DBSession(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str]          # PK
    user_role: Mapped[str]
    created_at: Mapped[datetime]
    last_active_at: Mapped[datetime]
    total_turns: Mapped[int]
    active_flag: Mapped[bool]
```

**`ConversationHistory`** (maps to `conversation_history` table):
```python
class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    turn_id: Mapped[str]             # PK, uuid
    session_id: Mapped[str]          # FK → sessions.session_id
    role: Mapped[str]                # "user" | "assistant"
    message: Mapped[str]
    agents_invoked: Mapped[list]     # JSON
    response_mode: Mapped[str | None]
    cited_documents: Mapped[list]    # JSON
    cited_records: Mapped[list]      # JSON
    timestamp: Mapped[datetime]
    latency_ms: Mapped[int | None]
```

**`AuditLog`** (maps to `audit_log` table):
```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    log_id: Mapped[str]              # PK, uuid
    session_id: Mapped[str | None]
    turn_id: Mapped[str | None]
    query_text: Mapped[str]
    intent_classified: Mapped[str | None]
    agents_invoked: Mapped[list]
    overall_confidence: Mapped[float | None]
    data_freshness_lag_seconds: Mapped[int | None]
    stale_sources: Mapped[list]
    error_flag: Mapped[bool]
    error_detail: Mapped[str | None]
    created_at: Mapped[datetime]
```

### 4.2 Service: `server/app/services/conversation_service.py`

```python
async def upsert_session(
    session: AsyncSession,
    session_id: str,
    user_role: str = "user",
) -> None
```
- Uses `INSERT ... ON CONFLICT (session_id) DO UPDATE SET last_active_at = now(), total_turns = total_turns + 1`
- If it does not exist: creates with `created_at = now()`, `active_flag = True`, `total_turns = 1`

```python
async def append_turn(
    session: AsyncSession,
    session_id: str,
    user_message: str,
    assistant_message: str,
    agents_invoked: list[str],
    latency_ms: int | None = None,
) -> str
```
- Inserts TWO rows: one `role = "user"`, one `role = "assistant"` (same turn)
- Returns `turn_id` (the assistant turn's uuid)
- `cited_documents = []`, `cited_records = []` for now (populated by agents in a later phase)

### 4.3 Update `server/app/services/agent_proxy.py`

`get_chat_response` signature changes to accept a DB session:

```python
async def get_chat_response(
    settings: Settings,
    db_session: AsyncSession,      # NEW
    session_id: str,
    message: str,
) -> dict[str, Any]
```

After extracting `message_text` from ADK events:
1. Call `conversation_service.upsert_session(db_session, session_id)`
2. Call `conversation_service.append_turn(db_session, session_id, message, message_text, agents_invoked=[], latency_ms=<elapsed>)`
3. `await db_session.commit()`

The chat route in `server/app/api/routes/chat.py` already gets `db_session` injected via `Depends(db_session)` — pass it through to `get_chat_response`.

---

## 5. Agent Architecture

### 5.1 Agent hierarchy (exact ADK structure)

```
root_agent  (LlmAgent, name="root_agent")
    sub_agents:
        └── chat_agent  (LlmAgent, name="chat_agent")
                sub_agents:
                    ├── flood_vulnerability_agent
                    ├── heat_health_agent
                    ├── infrastructure_agent
                    └── logistics_agent
```

ADK `sub_agents` are registered as a list on the parent agent. The parent can transfer control to them via tool call or explicit hand-off. The root_agent routes to chat_agent for all domain traffic.

### 5.2 `metrosense_agent/agent.py` — root_agent

```python
from google.adk.agents import Agent
from metrosense_agent.subagents.chat_agent import chat_agent
from metrosense_agent.prompts import ROOT_AGENT_INSTRUCTION

root_agent = Agent(
    name="root_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.5-flash"),
    description="MetroSense root orchestrator — routes all queries to the chat agent.",
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[chat_agent],
)
```

root_agent instruction:
- Never answer directly. Always delegate to chat_agent.
- Domain: Bengaluru climate, flood, AQI, power, traffic only.
- Reject non-Bengaluru geography queries before delegation.
- Reject harmful / non-domain queries with a fixed refusal string.

### 5.3 `subagents/chat_agent.py` — chat_agent

The only agent that synthesises a natural language response to the user.

Tools on chat_agent: `resolve_location`, `list_document_indexes`

Sub-agents: `flood_vulnerability_agent`, `heat_health_agent`, `infrastructure_agent`, `logistics_agent`

Instruction responsibilities:
1. **Input guardrail** — if the query is not about Bengaluru climate/infrastructure, respond with: `"I can only answer questions about Bengaluru's climate, flood risk, air quality, power grid, and traffic. Please rephrase."`
2. **Location resolution** — always call `resolve_location` before forwarding to domain agents. Canonical `location_id` must be established.
3. **Routing** — map intents to agents:
   - Flood / lake / inundation / drainage → `flood_vulnerability_agent`
   - AQI / air quality / health / heat / UHI → `heat_health_agent`
   - Power / outage / BESCOM / tree fall / wind → `infrastructure_agent`
   - Traffic / corridor / ORR / delay / logistics → `logistics_agent`
   - Multi-domain → delegate to multiple agents in sequence, then synthesise
4. **Scorecard trigger** — if query contains `risk`, `scorecard`, `vulnerability`, `assessment`, `how vulnerable is` → call ALL four domain agents and synthesise the Unified Risk Scorecard format.
5. **Citation rule** — every factual claim in the response must reference either a DB record timestamp or a document section ID. No unsourced numerical claims.
6. **Data freshness** — include the observed_at timestamp of the most recent data point used in the response.

### 5.4 `subagents/flood_agent.py` — flood_vulnerability_agent

Tools:
- `get_weather_current(location_id)` — from `tools/shared/weather_tools.py`
- `get_weather_historical(location_id, hours)` — from `tools/shared/weather_tools.py`
- `get_lake_hydrology(lake_id, limit)` — from `tools/flood_tools.py`
- `get_flood_incidents(location_id, limit)` — from `tools/flood_tools.py`
- `list_document_indexes(document_type, ward_name)` — from `tools/shared/document_tools.py`
- `fetch_document_section(document_id, section_id)` — from `tools/shared/document_tools.py`

Instruction:
- Primary signal: `rainfall_intensity_mm_hr` from weather + `fill_percentage` + `overflow_status` from lake hydrology
- Secondary signal: `flood_incident` history for the location (frequency, severity, water_depth_cm)
- Document grounding: read flood study index → identify relevant sections (ones with `contains_thresholds: true` for the ward) → fetch section → extract threshold values → compare against live data
- Barricade recommendation: only if `rainfall_intensity_mm_hr > threshold_from_document` AND (`fill_percentage > 85` OR `overflow_status = true`)
- Output in structured format (see §7)
- Known monitored lake IDs (from golden data): Bellandur, Varthur, KR Puram, Hebbal — map these from location resolution

### 5.5 `subagents/heat_agent.py` — heat_health_agent

Tools:
- `get_aqi_current(location_id, limit)` — from `tools/heat_tools.py`
- `get_aqi_historical(location_id, days)` — from `tools/heat_tools.py`
- `get_weather_current(location_id)` — shared weather tool (temperature, humidity)
- `get_ward_profile(ward_id)` — from `tools/heat_tools.py`
- `list_document_indexes(document_type, ward_name)` — document tools
- `fetch_document_section(document_id, section_id)` — document tools

Instruction:
- `aqi_value` + `aqi_category` + `dominant_pollutant` drive advisory specificity
- `elderly_population_pct` + `children_population_pct` from ward_profile → sensitive population multiplier
- `green_cover_pct` → UHI intensity factor
- WHO thresholds applied per pollutant type (these are embedded in instruction, not from DB)
- Requires specific advisory text per pollutant: PM2.5 → "avoid outdoor exercise", NO2 → "keep windows closed", etc.

### 5.6 `subagents/infra_agent.py` — infrastructure_agent

Tools:
- `get_weather_current(location_id)` — shared
- `get_weather_historical(location_id, hours)` — shared (wind gust trend)
- `get_power_outage_events(location_id, window_days)` — from `tools/infra_tools.py`
- `list_document_indexes(document_type, ward_name)` — document tools
- `fetch_document_section(document_id, section_id)` — document tools

Instruction:
- Primary signal: `wind_gust_kmh` (NOT `wind_speed_kmh`) from most recent weather observation
- Only `outage_type != 'planned'` events are used for historical calibration
- `fault_type = 'treefall'` events are the direct tree-fall risk signal
- Document: BBMP tree canopy reference → tree density for the ward
- Document: BESCOM infra reference → powerline proximity data for the ward
- Risk tiers: `wind_gust_kmh < 40` = LOW, `40–60` = MODERATE, `60–80` = HIGH, `> 80` = CRITICAL (instruction-embedded, then calibrated by historical outage frequency)

### 5.7 `subagents/logistics_agent.py` — logistics_agent

Tools:
- `get_traffic_current(location_id, limit)` — from `tools/logistics_tools.py`
- `get_traffic_corridor(corridor_name, limit)` — from `tools/logistics_tools.py`
- `get_weather_current(location_id)` — shared
- `get_flood_incidents(location_id, limit)` — flood tools (waterlogging signals)
- `list_document_indexes(document_type, ward_name)` — document tools
- `fetch_document_section(document_id, section_id)` — document tools

Instruction:
- `congestion_index` + `delay_minutes` + `waterlogging_flag` are the primary traffic signals
- `rainfall_mm_1h_at_time` on traffic observations provides the rain-at-observation context
- `heavy_vehicle_share` matters for ORR and Hosur Road degradation rate
- Document: flood study s4 (delay multipliers by corridor and rainfall band) → use for calibration
- Key corridors: ORR, Sarjapur Road, Hosur Road, Bellary Road, Mysore Road, KR Puram

---

## 6. Tool Implementations

### 6.1 `tools/backend_client.py`

Single `httpx.AsyncClient`-based module. Reads `BACKEND_INTERNAL_URL` and `AGENT_INTERNAL_TOKEN` from environment.

```python
BACKEND_URL = os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8010")
INTERNAL_TOKEN = os.getenv("AGENT_INTERNAL_TOKEN", "")

async def _get(path: str, params: dict) -> list[dict] | dict | None:
    """Single internal HTTP GET with token auth. Raises on non-2xx."""
```

All tool functions call `_get()`. On `httpx.TimeoutException` or HTTP error → return empty list `[]` (tools must be fault-tolerant — a data source being unavailable should not crash the agent, just reduce answer quality).

Timeout: `10.0` seconds per tool call.

### 6.2 `tools/shared/weather_tools.py`

```python
async def get_weather_current(location_id: str, limit: int = 1) -> list[dict]:
    """Get most recent weather observations for a location."""

async def get_weather_historical(location_id: str, hours: int = 24) -> list[dict]:
    """Get weather observations for the past N hours for a location."""
```

### 6.3 `tools/shared/location_tools.py`

```python
async def resolve_location(name: str) -> list[dict]:
    """
    Resolve a free-text location name (e.g. 'Bellandur', 'HSR Layout Sector 2')
    to canonical location_master entries.
    Returns list of matches with location_id, canonical_name, ward_id, ward_name.
    """

async def list_locations() -> list[dict]:
    """List all known Bangalore locations in the system."""
```

`resolve_location` hits `GET /internal/locations/resolve?name=<name>`.

### 6.4 `tools/shared/document_tools.py`

Document tools work **entirely from the filesystem** — no backend HTTP call. They read the mounted volume at `DOCUMENTS_PATH`.

```python
DOCUMENTS_PATH = Path(os.getenv("DOCUMENTS_PATH", "/documents"))

async def list_document_indexes(
    document_type: str | None = None,
    ward_name: str | None = None,
) -> list[dict]:
    """
    List available document indexes.
    If document_type is given, filter by index['document_type'].
    If ward_name is given, filter to indexes whose wards_covered contains ward_name.
    Returns list of index metadata (without full table_of_contents content — just section summaries).
    Agents use this to decide WHICH document and section to fetch before calling fetch_document_section.
    """

async def fetch_document_section(
    document_id: str,
    section_id: str,
) -> str:
    """
    Read and return the text of one section from a document.
    document_id maps to the *_index.json file (e.g. 'bangalore_flood_study_2022').
    section_id is the section_id field in the index's table_of_contents (e.g. 's2').
    Returns the full markdown text of that section.
    """
```

`list_document_indexes` reads all `*_index.json` files from `DOCUMENTS_PATH`.
`fetch_document_section` reads the `text_file` path from the matching index entry.

These functions are `async def` but use `asyncio.to_thread` for the filesystem reads (non-blocking).

### 6.5 `tools/flood_tools.py`

```python
async def get_lake_hydrology(lake_id: str, limit: int = 5) -> list[dict]:
    """Get most recent lake hydrology observations for a lake."""

async def get_flood_incidents(location_id: str, limit: int = 20) -> list[dict]:
    """Get recent flood incidents for a location."""
```

### 6.6 `tools/heat_tools.py`

```python
async def get_aqi_current(location_id: str, limit: int = 1) -> list[dict]:
async def get_aqi_historical(location_id: str, days: int = 7) -> list[dict]:
async def get_ward_profile(ward_id: str) -> dict | None:
```

### 6.7 `tools/infra_tools.py`

```python
async def get_power_outage_events(location_id: str, window_days: int = 30) -> list[dict]:
    """Get unplanned power outage events within the past N days for a location."""
```

### 6.8 `tools/logistics_tools.py`

```python
async def get_traffic_current(location_id: str, limit: int = 5) -> list[dict]:
async def get_traffic_corridor(corridor_name: str, limit: int = 20) -> list[dict]:
```

---

## 7. Prompts (`prompts.py`)

All instruction strings live here. Never inline strings in agent files. Structure:

```python
ROOT_AGENT_INSTRUCTION: str
CHAT_AGENT_INSTRUCTION: str
FLOOD_AGENT_INSTRUCTION: str
HEAT_AGENT_INSTRUCTION: str
INFRA_AGENT_INSTRUCTION: str
LOGISTICS_AGENT_INSTRUCTION: str
```

Each instruction includes:
- Role and domain scope
- Explicit list of tools available (agents reason better when told what they can call)
- Output format for Level-1 domain payload (strict typed JSON envelope)
- Citation requirements
- Data freshness: include `observed_at` of the most recent record used
- Context requirements: include resolved location, time window, and key assumptions in `context_used`

### Guardrail strings embedded in CHAT_AGENT_INSTRUCTION

```
OFF_DOMAIN_REFUSAL = "I can only answer questions about Bengaluru's climate, flood risk,
air quality, power grid, and traffic. Please rephrase your question."

LOCATION_NOT_FOUND = "I couldn't find '{name}' in the Bengaluru location registry.
Please use a ward name or neighbourhood (e.g. 'Bellandur', 'Koramangala', 'Whitefield')."

NO_DATA_AVAILABLE = "No recent data is available for {location} on {domain}.
The dataset covers historical records — please check the data freshness."
```

---

## 8. Session Persistence Flow

```
User → POST /api/chat
    │
    ▼
chat route (FastAPI)
    │ ─── calls ──→ agent_proxy.get_chat_response(settings, db_session, session_id, message)
    │                   │
    │                   ├─ 1. _ensure_session (ADK InMemory)
    │                   ├─ 2. POST /run → ADK → root_agent → chat_agent → domain agents
    │                   ├─ 3. map ADK output to canonical Level-2 response contract
    │                   ├─ 4. conversation_service.upsert_session(db_session, session_id)
    │                   ├─ 5. conversation_service.append_turn(db_session, session_id, ...)
    │                   └─ 6. await db_session.commit()
    │
    ▼
Level-2 response returned to user
```

The DB write happens **after** the ADK call succeeds. If the DB write fails, the response is still returned to the user (log the error, don't fail the request). This is a best-effort persistence approach — data availability > perfect persistence.

### 8.1 Canonical response contracts (Level-1 vs Level-2)

Level-1 is internal and mandatory for every domain agent call. Level-2 is the only backend response shape exposed to frontend clients.

**Level-1 domain payload (internal)**
- Strict typed schema with required fields: `agent`, `query_id`, `timestamp`, `status`, `confidence`, `data`, `citations`, `data_freshness`, `context_used`, `errors`
- `status` enum is `ok | partial | error`
- `context_used` is required to capture resolved location, intent, and operational assumptions
- L1 payloads are not rendered directly in UI

**Level-2 user delivery contract (backend -> frontend)**
- Single stable shape for all chat responses:
  - `session_id`
  - `response_mode` (`text | scorecard | artifact`)
  - `response_text` (always present)
  - `citations_summary` (always present, may be empty)
  - `data_freshness_summary` (always present)
  - `risk_card` (nullable)
  - `artifact` (nullable)
  - `follow_up_prompt` (nullable)
- `risk_card` and `artifact` are populated only when the user explicitly asks and the capability is implemented; otherwise they remain `null`
- Mapping from Level-1 -> Level-2 is deterministic (no separate formatting agent)

Example Level-2 response:

```json
{
  "session_id": "uuid",
  "response_mode": "text",
  "response_text": "Bellandur flood risk is elevated tonight due to rainfall and lake fill conditions.",
  "citations_summary": [],
  "data_freshness_summary": {
    "telemetry_lag_seconds": 42,
    "stale_sources": []
  },
  "risk_card": null,
  "artifact": null,
  "follow_up_prompt": null
}
```

---

## 9. Environment Variables

### Backend additions (`server/.env`)

No new variables needed — the backend already has `AGENT_INTERNAL_TOKEN`. The internal routes use it for verification.

### Agents additions (`agents/.env`)

```
BACKEND_INTERNAL_URL=http://localhost:8010    # or http://server:8010 in Docker
DOCUMENTS_PATH=/documents                     # mounted volume path
AGENT_INTERNAL_TOKEN=dev-internal-token       # same as backend
AGENT_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=<your_key>
```

### Docker Compose changes (agents service)

```yaml
agents:
  ...
  environment:
    - BACKEND_INTERNAL_URL=http://server:8010
    - DOCUMENTS_PATH=/documents
    - AGENT_INTERNAL_TOKEN=${AGENT_INTERNAL_TOKEN}
    - AGENT_MODEL=${AGENT_MODEL:-gemini-2.5-flash}
  volumes:
    - ./server/Documents_Metrosense:/documents:ro
```

---

## 10. Backend Config Update

In `server/app/core/config.py`:

```python
agent_app_name: str = "metrosense_agent"   # was: "metrosearch_agent"
```

---

## 11. `agents/pyproject.toml` Updates

Add to `dependencies`:
```toml
"python-dotenv>=1.0",
"pydantic>=2.7",
```

`httpx` is already present. `google-adk` is already present.

---

## 12. Implementation Order

Execute in this order. Each step is independently testable before moving to the next.

### Phase 1 — Backend data layer (no agent changes yet)

1. Add `ConversationHistory`, `AuditLog`, `DBSession` models to `server/app/db/models.py`
2. Implement `server/app/services/data_service.py`
3. Implement `server/app/api/routes/internal.py` with all 11 endpoints
4. Register internal router in `server/app/api/router.py`
5. **Test:** `curl -H "X-Internal-Token: <your-agent-internal-token>" http://localhost:8010/internal/weather/current?location_id=<id>` returns data

### Phase 2 — Conversation persistence

6. Implement `server/app/services/conversation_service.py`
7. Update `server/app/services/agent_proxy.py` signature + DB write-through
8. Update `server/app/api/routes/chat.py` to pass db_session to agent_proxy
9. Update `server/app/core/config.py` (agent_app_name)
10. **Test:** After a chat request, rows appear in `sessions` and `conversation_history` tables

### Phase 3 — Agent tools

11. Update `agents/pyproject.toml`
12. Create `agents/metrosense_agent/tools/backend_client.py`
13. Create `agents/metrosense_agent/tools/shared/weather_tools.py`
14. Create `agents/metrosense_agent/tools/shared/location_tools.py`
15. Create `agents/metrosense_agent/tools/shared/document_tools.py`
16. Create `agents/metrosense_agent/tools/flood_tools.py`
17. Create `agents/metrosense_agent/tools/heat_tools.py`
18. Create `agents/metrosense_agent/tools/infra_tools.py`
19. Create `agents/metrosense_agent/tools/logistics_tools.py`
20. **Test:** Import each tool module; call one function against live backend

### Phase 4 — Agents

21. Create `agents/metrosense_agent/prompts.py`
22. Create domain agent files (flood, heat, infra, logistics)
23. Create chat_agent
24. Create root_agent (`agent.py` + `__init__.py`)
25. **Test:** `uv run adk api_server` picks up `metrosense_agent`; smoke test a flood query

### Phase 5 — Docker + integration

26. Update `docker-compose.yml` (volume + env vars)
27. Update `agents/.env.example`
28. Run full smoke test through backend → proxy → ADK → domain agents → DB persistence

---

## 13. Testing Checkpoints

| Checkpoint | What to verify |
|------------|----------------|
| Phase 1 done | All 11 internal endpoints return data for known location_ids from the golden dataset |
| Phase 2 done | `sessions` + `conversation_history` rows written after each `/api/chat` call |
| Phase 3 done | Each tool function returns non-empty list for a known location_id |
| Phase 4 done | `adk web` can complete a flood query, a health query, and a scorecard query |
| Phase 5 done | Full Docker stack end-to-end: frontend chat → backend → proxy → ADK → domain agents → DB |

---

## 14. What Is Out of Scope for This Phase

- Streaming / SSE (confirmed not in scope)
- AuditLog writes (schema exists, writes added in a later phase after agent invocation tracking is wired)
- Chart follow-up prompts (agent instruction includes the hook, UI not yet wired)
- Non-null `risk_card` / `artifact` rendering in the frontend (Level-2 fields exist now but are null until those capabilities are implemented)
- Sub-agent splitting (current agent files stay flat; sub-agents introduced when any agent > 300 lines)
- google_search tool removal (metrosearch_agent still exists and works; new agent replaces it for new sessions)

---

## 15. Known Risks

| Risk | Mitigation |
|------|------------|
| ADK sub_agent transfer reliability | Test each routing path explicitly in Phase 4 before moving to Phase 5 |
| `resolve_location` returning zero results | Chat agent instruction handles `LOCATION_NOT_FOUND` case and asks user to rephrase |
| Documents volume not mounted in dev | `DOCUMENTS_PATH` defaults to a local path; document tools return empty list gracefully on `FileNotFoundError` |
| DB write fails after ADK response | Best-effort persistence — log error, return response to user regardless |
| `conversation_history` → `sessions` FK violation on first turn | `upsert_session` runs before `append_turn` in the flow |
