# MetroSense — Product Document
### Bengaluru Climate Risk Intelligence Platform
---

## Problem Statement

Bengaluru is one of India's fastest-growing cities and one of its most climate-vulnerable. Every monsoon season, the city faces a predictable but poorly managed cascade of compounding risks — flash flooding in low-lying wards, power outages triggered by tree falls during wind events, toxic AQI spikes on still mornings, and traffic grid-lock that turns 30-minute commutes into 4-hour ordeals.

The problem is not a lack of data. IMD publishes weather bulletins. KSNDMC monitors lake levels. CPCB runs AQI stations. BESCOM logs outages. BBMP has drainage master plans and flood post-mortems.

**The problem is that none of this data talks to each other — and no one is asking it the right questions in real time.**

A BBMP disaster officer today must manually check multiple portals, cross-reference a PDF drainage report, and then make a judgment call on whether to barricade an underpass. A logistics company planning night deliveries has no way to know that a lake at 92% fill plus 3 hours of rain means ORR will be underwater by 11pm. A city planner reviewing heat vulnerability has to correlate AQI station data with a ward population report in Excel.

The result is reactive decision-making. Underpasses flood before barricades go up. Fleets get stranded. Emergency teams deploy late. Communities in dense, low-lying colonies bear the highest cost.

---

## Who This Is For

**Primary users — internal government use only (v1):**

| User | Their Core Need |
|---|---|
| BBMP Disaster Management Teams | Real-time flood black spot identification and barricade recommendations |
| City Planners | Ward-level multi-hazard risk scoring for infrastructure investment decisions |
| Logistics Operations Teams | Route-specific delay forecasting correlated with rainfall and waterlogging |
| Public Health Officers | Neighbourhood AQI advisories targeting sensitive populations |

---

## What UrbanClimate AI Does

UrbanClimate AI is a conversational multi-agent intelligence system that fuses real-time sensor telemetry, historical incident data, and structured domain documents into a single natural language interface.

A user can ask:

> "If it rains 60mm tonight, which underpasses need barricading and how bad will ORR delays get?"

And receive a grounded, cited answer in seconds — not a dashboard to interpret, not a raw data export, not a generic alert. A specific, actionable answer with sources.

The system covers five risk domains simultaneously:

**1. Flood Vulnerability**
Predicts inundation probability per ward and colony, identifies critical underpass black spots, recommends barricade deployment locations, and cross-references drainage capacity data from BBMP master plans with live lake telemetry.

**2. Urban Heat and Health**
Generates neighbourhood-specific health advisories by combining AQI sensor readings with population vulnerability data — flagging wards with high elderly and child populations during severe pollution or heat events.

**3. Infrastructure Stress**
Forecasts power outage probability by correlating wind gust telemetry with tree canopy density and historical BESCOM fault data — identifying which feeders and substations are at risk before a storm hits.

**4. Logistics Disruption**
Estimates time-to-destination delay factors for key Bangalore corridors (ORR, Sarjapur Road, Hosur Road, Bellary Road, Mysore Road, KR Puram) as a function of rainfall intensity, waterlogging status, and historical traffic behaviour.

**5. Contextual Conversation**
All of the above is accessible through plain natural language. Users ask questions the way they think — crossing domains, specifying locations by colony name, referencing past events — and the system routes, reasons, and responds with grounded citations.

---

## What Makes This Different

**It fuses structured data and documents.** Most dashboards show you the numbers. UrbanClimate AI reads the BBMP drainage master plan, the 2022 flood post-mortem, and the BESCOM incident reports — and reasons over them alongside live sensor data to produce answers, not charts.

**It is grounded and cited.** Every factual claim in every response references a specific database record or a specific section of a source document. A BBMP officer can trace any recommendation back to its source. There are no hallucinated risk scores.

**It is conversational, not a dashboard.** No portal to log into. No layer to toggle. No report to generate. Ask a question, get an answer, ask a follow-up.

**It handles compound queries.** "60mm rain + lake at 92% + wind gusts — what breaks first?" activates flood, infrastructure, and logistics reasoning in parallel and synthesises the answer into a single coherent response.

**It tells you how fresh the data is.** Every response includes a data freshness indicator. A disaster officer making a live decision knows if the rainfall reading is 2 minutes old or 45 minutes old.

---

## Solution Architecture Summary

UrbanClimate AI is built on **Google ADK** (Agent Development Kit) with a three-layer deployment:

```
Frontend (Chat Interface)
        ↕ HTTP REST
Backend (FastAPI + PostgreSQL)
        ↕ HTTP REST
ADK AI Server (Multi-Agent System)
```

**The AI layer** runs a hierarchy of specialised agents:
- A Root Orchestrator that manages routing, state, and parallel dispatch
- A Chat Agent that is the sole conversational interface — the only agent a user talks to
- Four domain sub-agents (Flood, Heat/Health, Infrastructure, Logistics) that each own their data tools

**The data layer** runs on PostgreSQL with 12 normalised tables covering raw sensor telemetry, reference data, and operational session data. No derived or computed fields are stored — agents reason over raw data.

**The document layer** uses an Agentic RAG approach without a vector database. Source documents (IMD bulletins, BBMP drainage plans, BESCOM reports, flood post-mortems) are converted to structured text and indexed with a JSON Table of Contents. Agents navigate documents like a human expert — reading the index, identifying the relevant section, fetching only what they need.

---

## What Is Not in Scope (v1)

- Public-facing access — internal government use only
- Authentication and role-based access — deferred to v2
- Real-time streaming — responses are complete payloads, no SSE
- Mobile app — web interface only
- Coverage outside BBMP ward boundaries
- Predictive modelling or ML forecasting — the system reasons over current and historical data, it does not train predictive models

---

## Success Criteria

The system is working correctly when:

- A BBMP officer can ask a compound flood query and receive a cited barricade recommendation within 10 seconds
- The flood reasoning eval against September 2022 ground truth data achieves greater than 80% precision
- Every NL response has 100% citation coverage — no uncited factual claims
- A logistics operator can get corridor-specific delay estimates for any major Bangalore route during a rain event
- The system correctly routes multi-domain queries to the right combination of agents without user guidance

---

*UrbanClimate AI — Product Document v1.0*
*Internal use — Bengaluru Climate Risk Intelligence Platform*
