# SOLUTIONS.md: MetroSense Agent Architecture & Design

**Date**: March 2026
**Status**: Production-ready with data seeding pending
**Target Audience**: Developers, DevOps, AI/ML engineers extending the system

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Agent Solution Overview](#agent-solution-overview)
3. [Agent & Subagent Architecture](#agent--subagent-architecture)
4. [Tool Ecosystem](#tool-ecosystem)
5. [Intent Classification & Routing](#intent-classification--routing)
6. [Session & Context Management](#session--context-management)
7. [Response Structuring](#response-structuring)
8. [Error Handling & Resilience](#error-handling--resilience)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [Security Model](#security-model)
11. [Deployment & Operations](#deployment--operations)
12. [Testing & Validation](#testing--validation)
13. [Known Limitations & Future Work](#known-limitations--future-work)

---

## Executive Summary

MetroSense's agent solution is a **hierarchical multi-agent system** built on Google Agent Development Kit (ADK) for Python. The architecture separates concerns into:

- **Frontend** (React 18, Vite): Chat UI, message rendering, structured output visualization
- **Backend** (FastAPI): Public API boundary, authentication, session orchestration, request validation
- **Agent Service** (Google ADK): Private reasoning, tool execution, domain intelligence

The design enforces a **strict architecture boundary**: browsers never call agents directly. All requests flow through the backend, which acts as a security and orchestration layer. This enables:

- ✅ Secrets and internal tools remain off the public internet
- ✅ Centralized auth, rate limiting, and observability
- ✅ Stable frontend contract despite agent framework changes
- ✅ Granular control over which user gets access to which conversation

---

## Agent Solution Overview

### Why This Approach?

MetroSense asks questions spanning multiple domains (flooding, air quality, outages, traffic). Rather than a single large model handling all domains equally, we use **specialized subagents**:

1. **Flood Vulnerability Agent** → lake hydrology, flood incidents, monsoon patterns
2. **Heat & Health Agent** → AQI trends, ward profiles, mortality risk
3. **Infrastructure Agent** → power outages, grid stress, treefall risk
4. **Logistics Agent** → traffic, corridor disruption, route impact

Each agent has:
- Domain-specific tools (e.g., floods only talk to flood data)
- Domain-specific prompts (monsoon reasoning vs. traffic reasoning)
- Access to cross-cutting shared tools (weather, location, documents)

### Model & Provider

- **Provider**: Google Gemini 2.5 Flash (fast, multimodal-capable)
- **Framework**: Google Agent Development Kit (ADK) for Python
- **Gemini Features Used**:
  - Native function calling (tools)
  - Streaming (token-by-token text generation)
  - Sub-agent delegation (chat_agent can invoke flood_vulnerability_agent, etc.)

---

## Agent & Subagent Architecture

### Hierarchy

```
root_agent (empty orchestrator)
    name: "root_agent"
    model: gemini-2.5-flash
    instruction: "Delegate everything to chat_agent"
    sub_agents: [chat_agent]
    ↓
chat_agent (user interface)
    name: "chat_agent"
    model: gemini-2.5-flash
    instruction: CHAT_AGENT_INSTRUCTION (classify intent, guard rails, greeting handling)
    tools: [resolve_location, list_document_indexes]
    sub_agents: [
        flood_vulnerability_agent,
        heat_health_agent,
        infrastructure_agent,
        logistics_agent
    ]
    ↓
    ├─ flood_vulnerability_agent (domain specialist)
    │   tools: [get_lake_hydrology, get_flood_incidents] + shared tools
    │   instruction: FLOOD_AGENT_INSTRUCTION
    │
    ├─ heat_health_agent (domain specialist)
    │   tools: [get_aqi_current, get_aqi_historical, get_ward_profile] + shared tools
    │   instruction: HEAT_AGENT_INSTRUCTION
    │
    ├─ infrastructure_agent (domain specialist)
    │   tools: [get_power_outage_events] + shared tools
    │   instruction: INFRA_AGENT_INSTRUCTION
    │
    └─ logistics_agent (domain specialist)
        tools: [get_traffic_current, get_traffic_corridor] + shared tools
        instruction: LOGISTICS_AGENT_INSTRUCTION
```

### Why This Shape?

1. **Root Agent**: Minimal orchestrator. All instructions live in chat_agent, preventing agent confusion.
2. **Chat Agent**: Single point of user intent classification and guardrails. Decides which domain to route to.
3. **Domain Agents**: Specialized reasoning. Flood agent never calls traffic tools, reducing hallucination and improving accuracy.

### Agent Configurations

Each agent is configured in `agents/metrosense_agent/agent.py` and subagent files:

| Agent | File | Model | Purpose | Sub-Agents |
|-------|------|-------|---------|-----------|
| `root_agent` | `agent.py` | gemini-2.5-flash | Top-level orchestrator | [chat_agent] |
| `chat_agent` | `subagents/chat_agent.py` | gemini-2.5-flash | User-facing, intent routing | [flood, heat, infra, logistics] |
| `flood_vulnerability_agent` | `subagents/flood_agent.py` | gemini-2.5-flash | Flood reasoning | None |
| `heat_health_agent` | `subagents/heat_agent.py` | gemini-2.5-flash | AQI & health reasoning | None |
| `infrastructure_agent` | `subagents/infra_agent.py` | gemini-2.5-flash | Power & grid reasoning | None |
| `logistics_agent` | `subagents/logistics_agent.py` | gemini-2.5-flash | Traffic & route reasoning | None |

---

## Tool Ecosystem

### Design Philosophy

All tools are:
- **Async** — non-blocking for high-concurrency handling
- **Backend-Proxied** — never touch the database directly; always call agent routes
- **Structured Error Handling** — return `ToolResult` with error codes, not exceptions
- **Metadata-Rich** — include data freshness, row counts, citation sources
- **Timeout-Safe** — 10-second HTTP timeout prevents hanging

### Tool Categories

#### 1. Domain-Specific Tools (backend-proxied via `/internal/*`)

**Flood Tools** (`tools/flood_tools.py`)
```python
async def get_lake_hydrology(
    lake_name: str | None = None,
    neighborhood: str | None = None,
) -> ToolResult
```
- **Endpoint**: `GET /internal/lakes`
- **Query Params**: `lake_name`, `neighborhood`
- **Returns**: Lake ID, current level, spillway status, last updated
- **Freshness**: MetroSense dataset (Jan 2023 – Dec 2023)
- **Use When**: User asks about lakes, reservoir levels, water bodies
- **Error Cases**:
  - `BACKEND_TIMEOUT` — lake service unresponsive (10s timeout)
  - `BACKEND_HTTP_ERROR` — invalid lake name or backend error
  - `BACKEND_CONFIG_MISSING` — BACKEND_INTERNAL_URL or token missing

```python
async def get_flood_incidents(
    neighborhood: str | None = None,
    ward: str | None = None,
    days_back: int = 30,
) -> ToolResult
```
- **Endpoint**: `GET /internal/floods`
- **Query Params**: `neighborhood`, `ward`, `days_back`
- **Returns**: Incident ID, location, water level, impact severity, timestamp
- **Freshness**: Dataset historical (2023) or live if seeded post-2023
- **Use When**: User asks "Has area X flooded?" or "Show recent inundation"
- **Error Cases**: Same as above

**Heat & AQI Tools** (`tools/heat_tools.py`)
```python
async def get_aqi_current(
    neighborhood: str | None = None,
    ward: str | None = None,
) -> ToolResult
```
- **Endpoint**: `GET /internal/aqi/current`
- **Returns**: Pollutant levels (PM2.5, PM10, NO2, O3), AQI category, health warning
- **Freshness**: Most recent observation in dataset
- **Use When**: "What's the air quality in Whitefield?" or "Is it safe to go outside?"

```python
async def get_aqi_historical(
    neighborhood: str,
    days: int = 30,
) -> ToolResult
```
- **Endpoint**: `GET /internal/aqi/historical`
- **Returns**: Time series of daily AQI, trends, episodic events
- **Use When**: "How has air quality trended in Koramangala?" or "When was the worst AQI?"

```python
async def get_aqi_summary(
    ward: str,
) -> ToolResult
```
- **Endpoint**: `GET /internal/aqi/summary`
- **Returns**: Ward-level aggregates: avg AQI, pollution hotspots, seasonal patterns
- **Use When**: Agent needs ward-level statistics for risk card generation

```python
async def get_ward_profile(
    ward: str,
) -> ToolResult
```
- **Endpoint**: `GET /internal/ward/profile`
- **Returns**: Demographic data (population, vulnerable groups), health facilities, schools
- **Purpose**: Contextualize AQI with population risk (elderly, children, hospitals)
- **Use When**: Scoring heat/AQI risk for a neighborhood

**Infrastructure Tools** (`tools/infra_tools.py`)
```python
async def get_power_outage_events(
    neighborhood: str | None = None,
    ward: str | None = None,
    days_back: int = 30,
) -> ToolResult
```
- **Endpoint**: `GET /internal/outages`
- **Query Params**: `neighborhood`, `ward`, `days_back`
- **Returns**: Outage start time, duration, estimated customers affected, cause (tree fall, grid fault)
- **Freshness**: Dataset 2023 or live if newly seeded
- **Use When**: "Why is power out in Indiranagar?" or "How often do outages happen?"

**Logistics Tools** (`tools/logistics_tools.py`)
```python
async def get_traffic_current(
    corridor: str | None = None,
    neighborhood: str | None = None,
) -> ToolResult
```
- **Endpoint**: `GET /internal/traffic/current`
- **Returns**: Congestion score (0–100), avg speed, incident count, estimated delay
- **Use When**: "Is ORR congested right now?" or "Best route to avoid delays?"

```python
async def get_traffic_corridor(
    corridor_name: str,
) -> ToolResult
```
- **Endpoint**: `GET /internal/traffic/corridor`
- **Returns**: Corridor metadata, historical congestion patterns, incident types
- **Use When**: Agent needs context on a specific corridor (e.g., ORR, Hosur Road)

#### 2. Shared Tools (cross-domain, backend-proxied)

**Location Tools** (`tools/shared/location_tools.py`)
```python
async def resolve_location(
    location_name: str,
) -> ToolResult
```
- **Endpoint**: `GET /internal/locations/resolve`
- **Returns**: Canonical location ID, neighborhood, ward, lat/lon
- **Purpose**: Normalize fuzzy user input ("Indira Nagar", "Indiranagar", "3rd Block") to standard location
- **Use When**: First step in any location-dependent query
- **Error Cases**:
  - Location not found → agent offers suggestions or asks for clarification
  - Ambiguous → agent asks user to disambiguate

```python
async def list_locations(
    filter: str | None = None,
    neighbors_of: str | None = None,
) -> ToolResult
```
- **Endpoint**: `GET /internal/locations/list`
- **Returns**: All neighborhoods, wards, zones in Bengaluru
- **Use When**: Agent doesn't know if location exists; lists nearby areas

**Weather Tools** (`tools/shared/weather_tools.py`)
```python
async def get_weather_current(
    neighborhood: str | None = None,
) -> ToolResult
```
- **Endpoint**: `GET /internal/weather/current`
- **Returns**: Temperature, humidity, wind speed, precipitation, cloud cover
- **Use When**: Assessing flood/heat risk; context for recommendations

```python
async def get_weather_historical(
    neighborhood: str,
    days: int = 30,
) -> ToolResult
```
- **Returns**: Daily weather time series (temp, rainfall, wind)
- **Use When**: Analyzing seasonal trends, unusual events

```python
async def get_weather_summary(
    season: str,  # "monsoon", "summer", "winter"
) -> ToolResult
```
- **Returns**: Seasonal averages, extremes, typical patterns
- **Use When**: Agent contextualizing current conditions: "This rainfall is 40% above monsoon average"

```python
async def get_weather_extremes(
    days_back: int = 365,
) -> ToolResult
```
- **Returns**: Record highs/lows, strongest winds, heaviest rains in lookback window
- **Use When**: Assessing likelihood of extreme events

**Document Tools** (`tools/shared/document_tools.py`)
```python
async def list_document_indexes() -> ToolResult
```
- **Endpoint**: Filesystem or `/internal/documents/list`
- **Returns**: Available documents (flooding guideline, AQI interpretation, outage protocols)
- **Use When**: Agent needs to cite official guidance

```python
async def fetch_document_section(
    document_id: str,
    section: str | None = None,
    query: str | None = None,
) -> ToolResult
```
- **Returns**: Relevant section text from a document
- **Use When**: Agent citing or reasoning from official guidelines

### Tool Implementation Pattern

All tools follow this structure:

```python
async def my_tool(param1: str, param2: int = 10) -> ToolResult:
    """
    Description visible to LLM.

    Args:
        param1: Description for LLM
        param2: Description (default: 10)

    Returns:
        ToolResult with success/failure status
    """
    # Validate input
    if not param1.strip():
        return failure_result(
            source="my_tool",
            error_code="INVALID_PARAM",
            error_detail="param1 cannot be empty",
            fallback_data=[]
        )

    # Call backend
    result = await backend_get(
        path="/internal/my-endpoint",
        params={"param1": param1, "param2": param2}
    )

    # Return structured result with metadata
    if result.success:
        return success_result(
            result.data,
            source="my_tool",
            dataset_note="Custom freshness note"
        )
    else:
        return failure_result(
            source="my_tool",
            error_code=result.error_code,
            error_detail=result.error_detail,
            fallback_data=[]
        )
```

### Tool Result Structure (`tools/types.py`)

```python
@dataclass
class ToolResult:
    success: bool
    data: Any  # JSON-serializable payload
    source: str  # Name of tool or backend
    error_code: str | None = None  # e.g., "BACKEND_TIMEOUT"
    error_detail: str | None = None  # Human-readable error message
    dataset_note: str | None = None  # Freshness/provenance info
    missing_params: list[str] | None = None  # Params agent didn't provide
```

**Success Example**:
```python
ToolResult(
    success=True,
    data=[
        {"lake_name": "Ulsoor", "level_m": 6.2, "spillway_status": "closed"},
    ],
    source="backend",
    dataset_note="MetroSense dataset — coverage: Jan 2023 – Dec 2023. Most recent: 2023-12-15."
)
```

**Failure Example**:
```python
ToolResult(
    success=False,
    data=[],
    source="backend",
    error_code="BACKEND_TIMEOUT",
    error_detail="Lake hydrology service did not respond within 10 seconds.",
    missing_params=None
)
```

### Backend Client (`tools/backend_client.py`)

All tools use a shared `backend_get()` function:

```python
async def backend_get(
    path: str,
    params: dict[str, Any] | None = None
) -> ToolResult:
    """HTTP wrapper with token auth and error handling."""
```

**Configuration** (environment variables):
- `BACKEND_INTERNAL_URL` — e.g., `http://localhost:8010`
- `AGENT_INTERNAL_TOKEN` — shared secret (e.g., `dev-internal-token`)

**Error Handling**:
- **Timeout (10s)** → `BACKEND_TIMEOUT`
- **HTTP Error (4xx/5xx)** → `BACKEND_HTTP_ERROR`
- **Unauthorized (401)** → `BACKEND_UNAUTHORIZED`
- **Invalid JSON response** → `BACKEND_HTTP_ERROR`
- **Missing config** → `BACKEND_CONFIG_MISSING`

**Freshness Tracking**:
```python
def _build_dataset_note(payload: Any) -> str:
    """Extract most-recent timestamp from returned rows."""
```
Examines `observed_at`, `reported_at`, `started_at` fields to add notes like:
> "MetroSense dataset — coverage: Jan 2023 – Dec 2023. Most recent record: 2023-12-15."

---

## Intent Classification & Routing

### Routing System (`orchestration/routing.py`)

The chat_agent uses keyword-based intent classification to decide which subagent to invoke:

```python
def classify_intents(query: str) -> IntentClassification:
    """
    Parse user query for domain keywords.
    Returns flags for each domain (flood, heat, infra, logistics).
    """
    keywords_by_intent = {
        "flood": {"flood", "rain", "inundation", "lake", "waterlogging", "barricade"},
        "heat": {"aqi", "air quality", "heat", "pollution", "pm2.5", "pm10", "no2"},
        "infra": {"power", "outage", "grid", "bescom", "tree fall", "wind"},
        "logistics": {"traffic", "corridor", "delay", "route", "orr", "hosur"},
        "scorecard": {"risk", "vulnerability", "assessment", "how vulnerable"},
    }
```

### Intent Examples

| User Query | Classification | Subagent(s) Invoked |
|-----------|-----------------|-------------------|
| "Will Whitefield flood in the monsoon?" | flood=True | flood_vulnerability_agent |
| "What's the air quality in Koramangala?" | heat=True | heat_health_agent |
| "Is power out in Indiranagar?" | infra=True | infrastructure_agent |
| "Is ORR congested?" | logistics=True | logistics_agent |
| "How vulnerable is Bangalore to floods?" | flood=True, scorecard=True | flood_vulnerability_agent (with artifact generation) |
| "Hi, who are you?" | greeting=True | None (chat_agent greets directly) |
| "What's the weather and traffic situation?" | logistics=True, (weather context) | logistics_agent + weather tools |

### Response Mode Detection

```python
def determine_response_mode(query: str) -> str:
    """
    Return "text", "scorecard", or "comparison".
    """
    if any(kw in query.lower() for kw in SCORECARD_KEYWORDS):
        return "scorecard"
    elif "compare" in query.lower() or "vs" in query.lower():
        return "comparison"
    return "text"
```

### Greeting-Only Behavior

```python
def is_greeting_only(query: str) -> bool:
    """
    Return True if query is a greeting without substantive question.
    Examples: "Hi", "Hello, how are you?", "Good morning"
    """
```

When True, chat_agent responds directly with:
```
Hello! I'm MetroSense, your climate and infrastructure intelligence assistant for Bengaluru.

I can help you with:
- Flood risk and lake status
- Air quality and health advisories
- Power outages and grid stress
- Traffic and corridor congestion
- Neighborhood vulnerability assessments

What would you like to know?
```

---

## Session & Context Management

### Data Model

#### Session Model (`server/app/db/models.py`)

```python
class Session(Base):
    __tablename__ = "sessions"

    session_id: str = Column(String(36), primary_key=True)
    user_id: int = Column(ForeignKey("users.id"), nullable=False)
    user_role: str = Column(String(20), default="user")
    title: str = Column(String(255))
    created_at: datetime = Column(DateTime(timezone=True), default=utcnow)
    last_active_at: datetime = Column(DateTime(timezone=True), onupdate=utcnow)
    total_turns: int = Column(Integer, default=0)
    active_flag: bool = Column(Boolean, default=True)
```

**Purpose**: Track chat sessions for the sidebar UI and conversation management.

**Lifecycle**:
1. User opens/creates chat → `session_id` UUID generated
2. First message → `upsert_session()` creates/updates Session record
3. Each turn → `total_turns` incremented, `last_active_at` updated
4. User archives chat → `active_flag` set to False (soft delete)

#### ConversationHistory Model

```python
class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    turn_id: str = Column(String(36), primary_key=True, default=uuid4)
    session_id: str = Column(ForeignKey("sessions.session_id"), nullable=False)
    role: str = Column(String(20), enum=["user", "assistant"])
    message: str = Column(Text)
    agents_invoked: list[str] = Column(ARRAY(String), nullable=False)
    response_mode: str = Column(String(20), nullable=True)  # "text", "scorecard", "comparison"
    cited_documents: list[str] = Column(ARRAY(String), default=[])
    cited_records: list[str] = Column(ARRAY(String), default=[])
    timestamp: datetime = Column(DateTime(timezone=True), default=utcnow)
    latency_ms: int = Column(Integer, nullable=True)
```

**Purpose**: Immutable log of all conversation turns for context injection and audit.

**Fields**:
- `role`: "user" or "assistant"
- `message`: Full text of message or response
- `agents_invoked`: List of agent names used (e.g., `["chat_agent", "flood_vulnerability_agent"]`)
- `response_mode`: Metadata on how response was structured
- `cited_documents`: References to MetroSense documents included in response
- `cited_records`: Data row IDs from backend API results

### Session Lifecycle

#### 1. Upsert Session

**Called**: On first chat message or new chat creation
**Service**: `conversation_service.upsert_session()`

```python
async def upsert_session(
    session: AsyncSession,
    session_id: str,
    user_id: int,
    title: str,
    user_role: str = "user",
) -> None:
```

**Behavior**:
- If `session_id` doesn't exist: Create new Session with created_at = now, total_turns = 1
- If `session_id` exists: Update last_active_at = now, total_turns += 1

**SQL** (PostgreSQL UPSERT):
```sql
INSERT INTO sessions (session_id, user_id, title, created_at, last_active_at, total_turns)
VALUES (...)
ON CONFLICT (session_id) DO UPDATE SET
    last_active_at = now(),
    total_turns = sessions.total_turns + 1;
```

#### 2. Append Turn

**Called**: After agent response is ready
**Service**: `conversation_service.append_turn()`

```python
async def append_turn(
    session: AsyncSession,
    session_id: str,
    user_message: str,
    assistant_message: str,
    agents_invoked: list[str],
    latency_ms: int | None = None,
) -> str:  # Returns assistant_turn_id
```

**Behavior**:
1. Generate UUIDs for user_turn and assistant_turn
2. Create two ConversationHistory rows (user, then assistant)
3. Flush to DB (so foreign keys are valid for audit logs)
4. Return assistant_turn_id for logging

**Sequence**:
```python
payload = [
    ConversationHistory(
        turn_id=user_turn_id,
        role="user",
        message=user_message,
        agents_invoked=agents_invoked,
        timestamp=now,
    ),
    ConversationHistory(
        turn_id=assistant_turn_id,
        role="assistant",
        message=assistant_message,
        agents_invoked=agents_invoked,
        latency_ms=latency_ms,
        timestamp=now,
    ),
]
session.add_all(payload)
await session.flush()  # FK constraint for audit_log
return assistant_turn_id
```

#### 3. List Sessions

**Called**: User views sidebar chat history
**API**: `GET /api/sessions`
**Service**: `conversation_service.list_sessions()`

```python
async def list_sessions(
    session: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[DBSession]:
```

**Returns**: Recent sessions ordered by `last_active_at DESC`, only for the authenticated user.

#### 4. List Session Transcript

**Called**: User opens a chat to view history
**API**: `GET /api/sessions/{session_id}`
**Service**: `conversation_service.list_session_messages()`

```python
async def list_session_messages(
    session: AsyncSession,
    user_id: int,
    session_id: str,
) -> tuple[DBSession | None, list[ConversationHistory]]:
```

**Behavior**:
1. Verify user owns this session (FK check: session.user_id == user_id)
2. Fetch all ConversationHistory rows for session, ordered by timestamp ASC
3. Return (session_metadata, messages_list)

**Security**: Only owner of session can view its messages.

### Context Injection (Current Status)

**❌ Planned but not yet implemented**

Currently, new chat requests do not include prior conversation history. Future work:

```python
async def build_runtime_context(
    session: AsyncSession,
    session_id: str,
    max_turns: int = 10,
) -> str:
    """
    Fetch recent conversation turns and format as context for agent session.

    Returns a string like:
    "Previous conversation:
    User: What's the flood risk in Whitefield?
    Assistant: Whitefield has moderate flood risk because...
    User: What about the ORR?
    Assistant: ORR flooding is rare because..."
    """
```

**Placeholder**: `server/app/services/runtime_context.py` created but not wired into chat endpoint.

**Next Step**: Integrate into `agent_proxy.get_chat_response()` to pass context to agent session.

---

## Response Structuring

### Chat Response Schema

**Endpoint**: `POST /api/chat`
**Request**:
```json
{
  "session_id": "a1b2c3d4-...",
  "message": "What's the flood risk in Whitefield?"
}
```

**Response** (`ChatResponse` model):
```json
{
  "session_id": "a1b2c3d4-...",
  "response_mode": "text",
  "response_text": "Whitefield has moderate flood risk because...",
  "citations_summary": [
    {"source": "Lake Hydrology Database", "date": "2023-12-15"},
    {"source": "MetroSense Flooding Guidelines"}
  ],
  "data_freshness_summary": {
    "note": "MetroSense dataset — coverage: Jan 2023 – Dec 2023. Most recent record: 2023-12-15."
  },
  "risk_card": null,
  "artifact": null,
  "follow_up_prompt": "Would you like to know about specific areas in Whitefield?",
  "message": "Whitefield has moderate flood risk because..."  // Backward compat
}
```

### Risk Card Payloads

**When Generated**: `response_mode == "scorecard"`

**Schema** (`RiskCardPayload`):
```python
class RiskCardPayload(BaseModel):
    neighborhood: str
    generated_at: str  # ISO 8601
    overall_risk_score: float  # 0–100

    # Domain-specific metrics
    flood_risk: RiskMetric | None  # {probability, severity}
    power_outage_risk: RiskMetric | None
    traffic_delay_index: RiskMetric | None

    # Health & advisory
    health_advisory: HealthAdvisory | None  # {aqi, aqi_category}
    emergency_readiness: EmergencyReadiness | None  # {recommendation, actions}

    # Flood-specific details
    rainfall_expected_mm_per_hr: float | None
    rainfall_classification: str | None  # "Light", "Moderate", "Heavy"
    barricade_recommendations: list[BarricadeRecommendation] | None

    class RiskMetric(BaseModel):
        probability: float | None  # 0–1
        severity: str | None  # "Low", "Moderate", "High"
        congestion_score: float | None  # Traffic-specific: 0–100
```

**Example**:
```json
{
  "neighborhood": "Whitefield",
  "generated_at": "2024-03-12T15:45:00Z",
  "overall_risk_score": 62.5,
  "flood_risk": {
    "probability": 0.45,
    "severity": "MODERATE"
  },
  "power_outage_risk": {
    "probability": 0.12,
    "severity": "LOW"
  },
  "traffic_delay_index": {
    "probability": 0.80,
    "congestion_score": 75.0
  },
  "health_advisory": {
    "aqi": 142,
    "aqi_category": "UNHEALTHY_FOR_SENSITIVE_GROUPS"
  },
  "emergency_readiness": {
    "recommendation": "Stock water and keep medications on hand",
    "actions": [
      "Monitor lake levels daily",
      "Maintain emergency contact list"
    ]
  },
  "rainfall_expected_mm_per_hr": 8.5,
  "rainfall_classification": "MODERATE",
  "barricade_recommendations": [
    {
      "underpass_name": "Koramangala Underpass",
      "reason": "Prone to 1.2m water accumulation in 2-hour heavy rain"
    }
  ]
}
```

### Artifact Payloads

**When Generated**: `response_mode == "text"` but response includes structured data

**Types**:
1. **TableArtifact**: Tabular comparison data
2. **ChartArtifact**: Time series or bar charts
3. **MapArtifact**: Neighborhood-level geographic data

**Schema** (generic):
```python
class ArtifactPayload(BaseModel):
    type: str  # "table", "chart", "map"
    title: str
    source: str | None  # Data provenance
    columns: list[str] | None  # For tables
    rows: list[list[object]] | None  # For tables
    description: str | None
```

**Table Example** (AQI comparison):
```json
{
  "type": "table",
  "title": "Air Quality Comparison: Indiranagar vs. Koramangala",
  "source": "MetroSense AQI Database",
  "columns": ["Pollutant", "Indiranagar", "Koramangala", "Safe Threshold"],
  "rows": [
    ["PM2.5", 85, 120, 35],
    ["PM10", 150, 210, 100],
    ["NO2", 65, 78, 80],
    ["AQI Category", "Unhealthy", "Very Unhealthy", "-"]
  ],
  "description": "Koramangala has more severe pollution. Avoid outdoor activity."
}
```

### Response Building (`orchestration/response_contract.py`)

Agent constructs response via:

```python
def build_level2_response(
    *,
    session_id: str,
    response_text: str,
    response_mode: str = "text",
    citations_summary: list[dict[str, Any]] | None = None,
    data_freshness_summary: dict[str, Any] | None = None,
    risk_card: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    follow_up_prompt: str | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "response_mode": response_mode,
        "response_text": response_text,
        "citations_summary": citations_summary or [],
        "data_freshness_summary": data_freshness_summary or {},
        "risk_card": risk_card,
        "artifact": artifact,
        "follow_up_prompt": follow_up_prompt,
        "message": response_text,  # Backward compat
    }
```

**Agent Prompt Instruction** (enforced via `CHAT_AGENT_INSTRUCTION`):
> "Return a JSON object with structure above. Include risk_card if user asks for scorecard. Include artifact for comparisons. Always include response_text."

---

## Error Handling & Resilience

### Tool-Level Errors

**Pattern**: Tools return `ToolResult` with `success=False`, never raise exceptions.

**Error Codes** (from `backend_client.py`):
| Code | Cause | Handling |
|------|-------|----------|
| `BACKEND_CONFIG_MISSING` | BACKEND_INTERNAL_URL or token not set | Agent should not call tools (return greeting) |
| `BACKEND_UNAUTHORIZED` | Token invalid or expired | Log security incident; refresh token |
| `BACKEND_TIMEOUT` | Service didn't respond within 10s | Retry or use cached result |
| `BACKEND_HTTP_ERROR` | 4xx/5xx response or invalid JSON | Log error; agent should apologize |
| `INVALID_PARAM` | Tool received bad input from agent | Agent should retry with corrected param |

**Agent Logic** (from `CHAT_AGENT_INSTRUCTION`):
```
If a tool returns an error:
1. Check error_code
2. If BACKEND_TIMEOUT, mention "Data temporarily unavailable, please try again"
3. If BACKEND_HTTP_ERROR, fall back to general knowledge: "I can tell you that..."
4. If location not found, ask user: "Which area did you mean?"
5. Never expose error codes to user; always provide graceful fallback
```

### Request-Level Errors

**Endpoint**: `POST /api/chat` (`agent_proxy.py`)

**Errors**:
| Scenario | Status Code | Response |
|----------|-------------|----------|
| Token validation fails | 401 | `{"error": "UNAUTHORIZED"}` |
| Session not owned by user | 403 | `{"error": "CHAT_SESSION_NOT_FOUND"}` |
| Agent service unavailable (no proxy) | 502 | `{"error": "AGENT_UNAVAILABLE"}` |
| Agent timeout (600s) | 504 | `{"error": "CHAT_TIMEOUT"}` |
| Invalid request body | 400 | Pydantic validation error |

**Timeout Handling** (`CHAT_TIMEOUT_SECONDS = 600.0`):

If agent exceeds 10 minutes, the httpx request times out. The backend logs and returns to user:
```json
{
  "status": 504,
  "error": {
    "code": "CHAT_TIMEOUT",
    "message": "The agent took too long to respond. Please try a simpler question."
  }
}
```

### Token Limit Overflow Handling

If agent's token count (context + tools + response) exceeds Gemini's limit (~1M tokens):

```python
async def get_chat_response(...) -> ChatResponse:
    try:
        response = await _call_agent(...)
    except httpx.HTTPStatusError as exc:
        if _is_input_token_limit_error(exc):
            # Retry with a shorter session_id for correlation
            new_session_id = _overflow_retry_session_id(session_id)
            return await _call_agent(..., session_id=new_session_id)
```

**Note**: This is a **workaround** for future context injection. Once conversation history is wired, we'll need windowing (keep only last N turns) to avoid overflow.

### Exception Propagation

**Backend Services** (FastAPI exception handlers in `app/main.py`):
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.detail, "message": "..."}},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "..."}},
    )
```

All exceptions are logged to `loguru` with full traceback for debugging.

---

## Data Flow Diagrams

### Request → Response Flow

```
┌─────────┐
│ Browser │ React chat UI
└────┬────┘
     │ POST /api/chat + JWT cookie
     v
┌─────────────────────────┐
│ Backend (FastAPI)       │ Port 8010
│  /api/chat endpoint     │
│  - Auth check           │
│  - Upsert session       │
│  - Call agent via proxy │
└────────┬────────────────┘
         │ POST /api/chat (with X-Internal-Token)
         v
┌─────────────────────────┐
│ Agent Proxy             │ Port 8020
│ (FastAPI)               │
│ - Token validation      │
│ - Header filtering      │
│ - Proxy request         │
└────────┬────────────────┘
         │ POST /api/chat (internal)
         v
┌─────────────────────────┐
│ Agent API Server        │ Port 8021
│ (Google ADK)            │
│ - root_agent            │
│   └─ chat_agent         │
│       ├─ flood_agent    │
│       ├─ heat_agent     │
│       ├─ infra_agent    │
│       └─ logistics_agent│
└────────┬────────────────┘
         │ Tool calls (async)
         v
┌─────────────────────────┐
│ Backend Internal Routes │ Ports 8010
│  /internal/*            │
│  (Token-gated)          │
│  - /internal/lakes      │
│  - /internal/aqi/*      │
│  - /internal/outages    │
│  - /internal/traffic/*  │
│  - /internal/locations  │
└────────┬────────────────┘
         │ SELECT queries
         v
┌─────────────────────────┐
│ PostgreSQL 16           │
│  - weather_observations │
│  - flood_incidents      │
│  - aqi_readings         │
│  - outage_events        │
│  - traffic_snapshots    │
│  - ward_profiles        │
└─────────────────────────┘
```

### Tool Execution Sequence

```
Agent (chat_agent) receives user query: "What's the flood risk in Whitefield?"

1. Classify Intent
   ├─ Keywords: ["flood", "risk"] match FLOOD_KEYWORDS
   └─ Result: IntentClassification(flood=True, heat=False, ...)

2. Route to Subagent
   └─ Invoke flood_vulnerability_agent

3. flood_vulnerability_agent calls tools:
   ├─ resolve_location("Whitefield")
   │  └─ backend_get("/internal/locations/resolve", params={"name": "Whitefield"})
   │     └─ Returns: {location_id: 123, neighborhood: "Whitefield", ward: "Ward_12"}
   │
   ├─ get_lake_hydrology(neighborhood="Whitefield")
   │  └─ backend_get("/internal/lakes", params={"neighborhood": "Whitefield"})
   │     └─ Returns: [{lake_name: "Ulsoor", level_m: 6.2}]
   │
   └─ get_weather_current(neighborhood="Whitefield")
      └─ backend_get("/internal/weather/current", params={"neighborhood": "Whitefield"})
         └─ Returns: {rainfall_mm: 8.2, wind_kmh: 15}

4. Score Risk
   ├─ Analyze data: "Monsoon rainfall 8.2mm, lake at 6.2m (normal 6.0m), wind 15kmh"
   ├─ Reasoning: "Moderate risk: rainfall typical, lake slightly elevated"
   └─ Score: 0.55 (out of 1.0)

5. Build Response
   └─ response_contract.build_level2_response(
        session_id: "...",
        response_text: "Whitefield has moderate flood risk due to...",
        response_mode: "text",
        risk_card: {
          neighborhood: "Whitefield",
          overall_risk_score: 55,
          flood_risk: {probability: 0.45, severity: "MODERATE"},
          ...
        }
      )

6. Backend (agent_proxy) receives response
   ├─ Extract response_text, risk_card, artifact
   ├─ Call append_turn() to log conversation
   └─ Return ChatResponse to browser

7. Browser renders
   ├─ Display response_text
   ├─ If risk_card: render RiskCardRenderer
   ├─ If artifact: render ArtifactRenderer
   └─ Update chat message list
```

---

## Security Model

### Authentication & Authorization

**Public Endpoints** (no auth required):
```
POST /api/auth/signup
POST /api/auth/login
GET  /health
```

**Protected Endpoints** (JWT cookie required):
```
GET  /api/me
POST /api/chat
GET  /api/sessions
GET  /api/sessions/{session_id}
POST /api/auth/logout
```

**JWT Implementation** (`app/api/routes/auth.py`):
- Issuer: Backend (Settings.secret_key)
- Token Type: HS256
- Payload:
  ```json
  {
    "sub": "user_id",
    "exp": "<60 mins from now>",
    "iat": "<now>"
  }
  ```
- Storage: HttpOnly, Secure, SameSite=Lax cookie named `access_token`
- Validation: `require_user` dependency checks cookie, raises 401 if invalid

**Session Ownership**:
```python
async def session_owner_id(session: AsyncSession, session_id: str) -> int | None:
    """Verify user owns session."""
    stmt = select(DBSession.user_id).where(DBSession.session_id == session_id)
    return (await session.execute(stmt)).scalar_one_or_none()

# In chat endpoint:
if await session_owner_id(db_session, payload.session_id) != current_user.id:
    raise PermissionError("Not your session")
```

### Internal Token Authentication

**Backend ↔ Agent Communication**:
- Header: `X-Internal-Token: <AGENT_INTERNAL_TOKEN>`
- Checked in proxy (`app/proxy.py`):
  ```python
  token = request.headers.get("X-Internal-Token")
  if not token or token != settings.agent_internal_token:
      raise HTTPException(status_code=401, detail="Unauthorized")
  ```
- Value: Environment variable set at startup (e.g., `dev-internal-token` in dev, cryptic string in prod)

**Agent ↔ Backend Communication**:
- Method: Same `X-Internal-Token` in `backend_client.py`
- Validates backward: If token is empty, tools fail safely with `BACKEND_CONFIG_MISSING`

### Data Isolation

| Layer | Isolation Method |
|-------|------------------|
| Browser | JWT auth; session FK to user_id |
| Backend-to-Agent | X-Internal-Token; not callable from browser |
| Agent-to-Backend | X-Internal-Token again (defense in depth) |
| Backend-to-DB | SQLAlchemy async; user_id checked in queries |

Example: User A **cannot** see User B's sessions:
```python
# GET /api/sessions
async def get_sessions(current_user: User, ...):
    sessions = await conversation_service.list_sessions(db, current_user.id)
    # Only sessions WHERE user_id = current_user.id returned
```

### Secrets Management

**Required Environment Variables**:
```bash
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/metrosense
SECRET_KEY=<random secret for JWT signing>
AGENT_INTERNAL_TOKEN=<shared secret with agents>
AGENT_INTERNAL_URL=http://localhost:8020

# Agents
BACKEND_INTERNAL_URL=http://localhost:8010
AGENT_INTERNAL_TOKEN=<same as backend's AGENT_INTERNAL_TOKEN>
GOOGLE_API_KEY=<Gemini API key>
DOCUMENTS_PATH=/path/to/Documents_Metrosense
```

**Best Practices**:
- Never commit `.env` to Git; use `.env.example` for template
- Use Kubernetes secrets or vault in production
- Rotate `AGENT_INTERNAL_TOKEN` quarterly
- Use unique `SECRET_KEY` per environment

---

## Deployment & Operations

### Local Development

**Prerequisites**:
- Docker & Docker Compose
- Python 3.12 + uv (backend & agents)
- Node.js 18+ + pnpm (frontend)

**Startup Sequence** (5 terminals):

**Terminal 1 — Database**:
```bash
docker-compose up -d db
# Waits ~5 seconds for PostgreSQL to be ready
```

**Terminal 2 — Backend**:
```bash
cd server
export AGENT_INTERNAL_TOKEN=dev-internal-token
export DATABASE_URL=postgresql+asyncpg://metrosense:secret@localhost:5432/metrosense
export AGENT_INTERNAL_URL=http://localhost:8020
export SECRET_KEY=dev-secret-change-in-prod

uv sync --all-extras
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8010
# Listens on http://localhost:8010
```

**Terminal 3 — Agent API Server**:
```bash
cd agents
export AGENT_INTERNAL_TOKEN=dev-internal-token
export BACKEND_INTERNAL_URL=http://localhost:8010
export GOOGLE_API_KEY=<your-key>
export DOCUMENTS_PATH=/home/dell/ai-track-metrosense/Documents_Metrosense

uv sync
uv run adk api_server --host 0.0.0.0 --port 8021
# Listens on http://localhost:8021 (internal only)
```

**Terminal 4 — Agent Proxy**:
```bash
cd agents
export AGENT_INTERNAL_TOKEN=dev-internal-token

uv sync
uv run uvicorn app.proxy:app --host 0.0.0.0 --port 8020
# Listens on http://localhost:8020 (bridges backend → ADK)
```

**Terminal 5 — Frontend**:
```bash
cd client
pnpm install
pnpm run dev
# Listens on http://localhost:5173
```

**Open Browser**: http://localhost:5173

### Docker Compose (Full Stack)

**File**: `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: metrosense
      POSTGRES_USER: metrosense
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"

  backend:
    build: ./server
    environment:
      DATABASE_URL: postgresql+asyncpg://metrosense:secret@db:5432/metrosense
      AGENT_INTERNAL_URL: http://agent-proxy:8020
      AGENT_INTERNAL_TOKEN: dev-internal-token
      SECRET_KEY: dev-secret
    ports:
      - "8010:8000"
    depends_on:
      - db

  agent-api:
    build: ./agents
    command: adk api_server --host 0.0.0.0 --port 8021
    environment:
      BACKEND_INTERNAL_URL: http://backend:8000
      AGENT_INTERNAL_TOKEN: dev-internal-token
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    ports:
      - "8021:8021"

  agent-proxy:
    build: ./agents
    command: uvicorn app.proxy:app --host 0.0.0.0 --port 8020
    environment:
      AGENT_INTERNAL_TOKEN: dev-internal-token
    ports:
      - "8020:8020"
    depends_on:
      - agent-api

  frontend:
    build: ./client
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

**Run**:
```bash
export GOOGLE_API_KEY=<your-key>
docker-compose up
```

### Production Checklist

- [ ] Set unique `SECRET_KEY` and `AGENT_INTERNAL_TOKEN`
- [ ] Use managed PostgreSQL (AWS RDS, GCP Cloud SQL) with SSL
- [ ] Enable CORS only for trusted origins
- [ ] Use HTTPS for all endpoints
- [ ] Set `ENVIRONMENT=production` in FastAPI config
- [ ] Enable security headers (HSTS, X-Frame-Options, CSP)
- [ ] Use container orchestration (Kubernetes, ECS)
- [ ] Set up error tracking (Sentry, CloudWatch)
- [ ] Configure logging aggregation (ELK, CloudLogging)
- [ ] Enable rate limiting on `/api/chat` (10 req/min per user)
- [ ] Set up monitoring for agent latency (should be <30s for 90th percentile)
- [ ] Test disaster recovery (DB backup, secret rotation)

---

## Testing & Validation

### Backend Tests

**Unit Tests** (`server/tests/unit/`):
- Auth flow (signup, login, logout, password hashing)
- Conversation service (upsert_session, append_turn)
- Domain service queries (mocked DB)

**Command**:
```bash
cd server && uv run pytest tests/unit -q
```

**Integration Tests** (`server/tests/integration/`):
- Full auth flow with real DB
- Chat endpoint (mocks agent service)
- ConversationHistory persistence

**Command**:
```bash
cd server && uv run pytest tests/integration -q
```

### Agent Tests

**Smoke Tests** (`agents/scripts/smoke_test.py`):
- Proxy health check
- Agent session creation
- Simple tool call (location resolve)

**Command**:
```bash
cd agents && uv run python scripts/smoke_test.py
```

**Evaluation Framework** (`agents/evals/`):
- MetroSense-specific eval rubrics
- Community-driven test cases
- Structured response validation

### Frontend Tests

**Linting**:
```bash
cd client && pnpm run lint
```

**Unit Tests** (Vitest):
```bash
cd client && pnpm run test
```

**E2E Tests** (Playwright):
```bash
cd client && pnpm exec playwright install
pnpm run test:e2e
```

**Test Scenarios**:
- Auth: signup, login, logout
- Chat: send message, receive streaming response
- Risk Cards: render structured card from agent response
- Session Sidebar: list chats, switch between sessions

### Quality Gates (CI/CD)

**GitHub Actions** (`.github/workflows/`):

```yaml
on: [push, pull_request]

jobs:
  backend-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd server && uv sync --all-extras
      - run: cd server && uv run ruff format --check .
      - run: cd server && uv run ruff check .
      - run: cd server && uv run mypy .
      - run: cd server && uv run lint-imports
      - run: cd server && uv run pytest tests/unit -q
      - run: cd server && uv run pytest tests/integration -q

  agents-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd agents && uv sync
      - run: cd agents && uv run python scripts/smoke_test.py

  frontend-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd client && pnpm install --frozen-lockfile
      - run: cd client && pnpm run lint
      - run: cd client && pnpm run build
      - run: cd client && pnpm run test:e2e
```

### Monitoring & Observability

**Logging** (Loguru):
- Backend logs to stdout + rotating files in `logs/`
- Chat requests logged with session_id, user_id, latency_ms
- Agent errors logged with tool name, error_code, fallback status

**Metrics** (Future):
- Agent latency distribution (p50, p95, p99)
- Tool success rates by domain
- Session creation/turn counts per hour
- Conversation dropout rates

**Example Log**:
```
2024-03-12 14:23:45 | INFO | session_id=a1b2c3 | user=123 | message_len=45 | agents=floods | latency_ms=2341
2024-03-12 14:23:50 | DEBUG | session_id=a1b2c3 | tool=resolve_location | param=Whitefield | result=success
2024-03-12 14:24:12 | INFO | session_id=a1b2c3 | response_mode=text | risk_card=true | artifact=false
```

---

## Known Limitations & Future Work

### Current Limitations

1. **No Streaming**: Responses buffered; sent all-at-once after agent completes
   - **Impact**: User sees long delay before first character
   - **Fix**: Implement SSE or WebSocket to stream text incrementally

2. **No Conversation Context**: New questions don't reference prior turns
   - **Impact**: Agent forgets previous questions in same session
   - **Fix**: Inject ConversationHistory into agent session (see `runtime_context.py`)

3. **Dataset Coverage**: MetroSense dataset 2023 only (not live)
   - **Impact**: Tool responses are historical; not current conditions
   - **Fix**: Run `server/scripts/load_metrosense_dataset.py` to seed; integrate live data feeds post-MVP

4. **No Rate Limiting**: Endpoint callable by any authenticated user N times/second
   - **Impact**: Dos/abuse risk
   - **Fix**: Add middleware: 10 req/min per user on `/api/chat`

5. **Document Tools Filesystem-Based**: Documents served from local directory
   - **Impact**: Not scalable; documents not versioned
   - **Fix**: Ingest into vector DB; use semantic search

6. **Limited Error Context**: Agent doesn't know why a tool failed (only "data unavailable")
   - **Impact**: Hard to debug; user gets vague responses
   - **Fix**: Add error_code to agent prompt; let agent decide recovery strategy

### Planned Enhancements (Phase 2)

| Feature | Status | Timeline | Impact |
|---------|--------|----------|--------|
| Streaming (SSE/WebSocket) | Design | Q2 2026 | UX improvement; faster perceived response |
| Context Injection | Planned | Q2 2026 | Multi-turn conversations |
| Live Data Integration | Planned | Q3 2026 | Real-time risk assessments |
| Document Vectorization | Planned | Q2 2026 | Better semantic search for guidelines |
| Rate Limiting | Priority | Q1 2026 | Security hardening |
| Agentic Web Search | Backlog | Q3 2026 | Beyond-Bengaluru context (e.g., global weather) |
| Multi-Language Support | Backlog | Q4 2026 | Hindi/Kannada responses |
| Audit Log UI | Backlog | Q3 2026 | Admin visibility; compliance |
| Fine-Tuning | Backlog | Q4 2026 | Domain-specific model optimization |

### Debugging Tips

**Agent Not Responding**:
1. Check `AGENT_INTERNAL_TOKEN` matches between backend & agents
2. Verify `/health` on agent-api (http://localhost:8021/health)
3. Check agent logs for "No available capacity"

**Tool Returning Empty Data**:
1. Check backend internal route (e.g., `GET http://localhost:8010/internal/lakes`)
2. Verify database is seeded (`load_metrosense_dataset.py`)
3. Check `BACKEND_INTERNAL_URL` and token in agent environment

**Frontend Not Showing Risk Card**:
1. Verify `response_mode` == "scorecard" in ChatResponse
2. Check console for ArtifactRenderer errors
3. Validate `risk_card` JSON against RiskCardPayload schema

---

## Appendix: Quick Reference

### Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://metrosense:secret@localhost:5432/metrosense
SECRET_KEY=dev-secret-key-change-in-prod
AGENT_INTERNAL_TOKEN=dev-internal-token
AGENT_INTERNAL_URL=http://localhost:8020
ENVIRONMENT=development

# Agents (.env)
BACKEND_INTERNAL_URL=http://localhost:8010
AGENT_INTERNAL_TOKEN=dev-internal-token
GOOGLE_API_KEY=<google-gemini-api-key>
DOCUMENTS_PATH=/home/dell/ai-track-metrosense/Documents_Metrosense
LOG_LEVEL=DEBUG
```

### API Endpoints Cheat Sheet

**Public**:
```
POST   /api/auth/signup
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/me
GET    /health
```

**Protected**:
```
POST   /api/chat              # Main conversation endpoint
GET    /api/sessions          # User's chat list
GET    /api/sessions/{id}     # Chat transcript
```

**Internal** (token-gated):
```
GET    /internal/lakes
GET    /internal/floods
GET    /internal/aqi/current
GET    /internal/aqi/historical
GET    /internal/aqi/summary
GET    /internal/ward/profile
GET    /internal/outages
GET    /internal/traffic/current
GET    /internal/traffic/corridor
GET    /internal/locations/resolve
GET    /internal/locations/list
GET    /internal/weather/current
GET    /internal/weather/historical
GET    /internal/weather/summary
GET    /internal/documents/list
GET    /internal/documents/{id}/{section}
```

### Key Files

| File | Purpose |
|------|---------|
| `agents/metrosense_agent/agent.py` | Root agent definition |
| `agents/metrosense_agent/subagents/chat_agent.py` | Chat agent + subagent wiring |
| `agents/metrosense_agent/orchestration/routing.py` | Intent classifier |
| `agents/metrosense_agent/orchestration/response_contract.py` | Response builder |
| `agents/metrosense_agent/tools/backend_client.py` | HTTP wrapper for all tool calls |
| `server/app/api/routes/chat.py` | Chat endpoint + response schemas |
| `server/app/services/agent_proxy.py` | Backend-to-agent proxy + parsing |
| `server/app/services/conversation_service.py` | Session & history management |
| `server/app/db/models.py` | Database schema (Session, ConversationHistory, etc.) |
| `client/src/components/RiskCard.tsx` | Risk card visualization |
| `client/src/components/MessageBubble.tsx` | Chat message component |

### Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 502 Bad Gateway | Agent proxy/ADK server down | Check port 8020 & 8021 |
| 504 Gateway Timeout | Agent took >600s | Simplify question; increase timeout |
| Chat returns empty | Token mismatch | Verify AGENT_INTERNAL_TOKEN |
| Risk cards not rendering | response_mode != "scorecard" | Check agent prompt |
| Database connection error | Wrong DATABASE_URL | Check .env file |
| "Location not found" | typo or location doesn't exist | Ask agent to list locations |

---

**Document Version**: 1.0
**Last Updated**: March 12, 2026
**Maintained By**: MetroSense Engineering
**Next Review**: June 2026
