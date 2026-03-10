# FRONTEND_SPEC.md — MetroSense Chat Interface

## 1. Overview

A minimal, single-page chat interface for the **UrbanClimate AI** system, serving city planners, BBMP disaster teams, and logistics companies in evaluating weather-related risks and infrastructure readiness for Bengaluru.

Users interact via natural language. The agent queries a local PostgreSQL database (real-time sensor data: temperature, humidity, wind speed, rainfall, AQI, lake water levels, power outage logs, traffic heatmaps) and retrieves context from local documentation (IMD weather bulletins, BBMP drainage master plans, flood post-mortem reports, urban forest maps, climate resilience whitepapers). The UI is a **plain chat interface** — it shows a text response for the vast majority of queries.

The chat interface has **two structured output types** beyond plain text — both are agent-decided and never client-inferred:

1. **RiskCard** — rendered when the backend response contains a `risk_card` object carrying a neighborhood risk scorecard as structured JSON (flood probability, power outage risk, traffic delay index, health advisory, emergency readiness).
2. **Artifact** — rendered when the backend response contains an `artifact` object carrying sanitized HTML for a chart, graph, table, or data visualisation. The frontend sanitizes and sandboxes this markup before rendering it inline in the conversation.

The frontend never infers, guesses, or keyword-triggers either output type — the presence of structured response fields is the sole rendering signal.

**Design language:** Clean, accessible light theme. Background `#F7F9FC`, white card surfaces, slate-navy `#0F1F2E` text, steel-blue `#005F8E` primary accent. IBM Plex Sans for body copy, IBM Plex Mono for data/labels. All colours meet WCAG 2.1 AA (≥ 4.5:1 for text, ≥ 3:1 for UI components). No colour-only status signals — every state is communicated with colour + icon + text label.

---

## 2. Architecture

```
User (Browser)
    │
    │  HTTP POST /api/chat  (message + session_id)
    ▼
FastAPI Backend  (server/)          ← port 8010
    │
    │  internal HTTP call
    ▼
Agent Server  (agents/)            ← internal service, e.g. port 8020
    │
    │  tool calls → PostgreSQL, sensor APIs, local knowledge sources
    ▼
Agent Response  (message text + optional RiskCard JSON + optional sanitized HTML artifact)
```

The Agent Server is a **first-party internal service you own**. For v1, the architecture is fixed as `frontend -> backend -> agents`, with the frontend never calling the agent server directly. The FastAPI backend remains the only browser-facing API boundary and is responsible for validation, orchestration, error handling, and returning a stable response contract to the UI.

---

## 3. Pages / Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `ChatPage` | The only page. Full-height chat interface. |

No routing library needed beyond React Router with a single route, or just a single-page render.

---

## 4. Component Tree

```
App
└── ChatPage
    ├── Header
    │   ├── Logo ("METROSENSE" + sub-label)
    │   ├── StatusPill (agent connection status)
    │   └── SessionId (mono, dimmed)
    ├── MessageList  (scrollable, flex-col)
    │   ├── MessageBubble (role: user | assistant)
    │   │   ├── TextContent       (markdown-rendered)
    │   │   ├── RiskCard?         (optional — backend `risk_card` payload)
    │   │   └── ArtifactRenderer? (optional — backend `artifact` payload)
    │   └── ThinkingIndicator  (request in flight / loading state)
    └── InputBar
        ├── TextArea  (auto-resize, max 4 rows)
        ├── SendButton
        └── SuggestedPrompts  (shown only when MessageList is empty)
```

---

## 5. Component Specifications

### 5.1 Header

- Sticky top, `background: #FFFFFF`, `border-bottom: 1px solid #D1DBE8`, `box-shadow: 0 1px 4px rgba(0,0,0,0.06)`.
- **Logo:** "METROSENSE" in IBM Plex Sans 600 20px, colour `#0F1F2E`. Sub-label: "BENGALURU CLIMATE INTELLIGENCE" in IBM Plex Mono 11px, colour `#4A5568`.
- **StatusPill:** Icon (✓ / spinner / ⚠) + colour tint + text label — never colour alone. States:
  - Online: `#F0FDF4` background, `#14532D` text, `#16A34A` left border, label "Agent Online"
  - Connecting: `#FFF9EB` background, `#6B4C00` text, `#CA8A04` left border, label "Connecting…"
  - Degraded: `#FFF0F2` background, `#9B1D2A` text, `#DC2626` left border, label "Degraded"
- **SessionId:** `SESSION · <id[:8]>` in IBM Plex Mono 11px, colour `#4A5568`. Tap to copy — expose `aria-label="Copy session ID"` and a visible focus ring on the button.

### 5.2 MessageList

- `overflow-y: auto`, flex column, padding `24px 0`, gap between bubbles `16px`.
- Auto-scrolls to bottom on new messages.
- Maintains scroll position if user has scrolled up (don't yank them down).

### 5.3 MessageBubble

**User bubble:**
- Right-aligned.
- Background: `#EEF2F7`, border: `1px solid #C9D6E3`, border-radius `12px 12px 2px 12px`.
- Text: IBM Plex Sans 14px, colour `#0F1F2E` (contrast 14.1:1 on `#EEF2F7` — AAA).
- Timestamp: IBM Plex Mono 11px, colour `#4A5568`, below bubble.

**Assistant bubble:**
- Left-aligned, slightly wider (max-width 80%).
- Background: `#FFFFFF`, left border: `3px solid #005F8E`.
- Text: IBM Plex Sans 14px, colour `#0F1F2E`.
- Renders Markdown: bold, inline code, bullet lists, code blocks styled with mono font and `#F7F9FC` background with `#D1DBE8` border.
- **RiskCard rendering:** Only rendered when the response contains a `risk_card` payload. The frontend does not inspect message text or keywords — the presence of `riskCard` data on the `Message` object is the sole rendering condition.
- **Artifact rendering:** Only rendered when the response contains an `artifact` payload. The presence of `artifact` data on the `Message` object is the sole rendering condition. Rendered via `ArtifactRenderer` (see §5.5) below the RiskCard if both are present. A single message may contain plain text, a RiskCard, an Artifact, or any combination.

### 5.4 RiskCard

Rendered inline within an assistant message **only when the backend returns a `risk_card` object.** This is the structured output for a neighborhood risk scorecard. It is never shown for plain conversational responses — not for flood questions, not for AQI questions, not for any keyword match. The agent decides when a scorecard is warranted.

The card surfaces four risk dimensions derived from the agent's cross-analysis of sensor data and documentation:

```
┌─────────────────────────────────────────┐
│  SARJAPUR ROAD  ·  RISK SCORE: 9.1 ◼    │  ← neighborhood + overall score badge
├─────────────────────────────────────────┤
│  FLOOD         ████████░░  94%  CRITICAL │  ← flood_risk (DB rainfall + drainage docs)
│  POWER OUTAGE  ██████░░░░  72%  HIGH     │  ← power_outage_risk (wind telemetry + outage logs)
│  TRAFFIC       ████████░░  8.4  HIGH     │  ← traffic_delay_index (congestion heatmaps)
│  AQI           █████░░░░░  187  UNHEALTHY│  ← health_advisory (AQI sensors + UHI research)
└─────────────────────────────────────────┘
```

- Each row: label (mono) + progress bar (tinted per severity) + value + severity badge.
- **Accessible severity system** — every severity uses a dark text on a light tinted background badge. Never colour alone; the text label is always present:

  | Severity | Badge bg | Badge text | Bar fill | Min contrast |
  |----------|----------|------------|----------|--------------|
  | CRITICAL | `#FFF0F2` | `#9B1D2A` | `#C0213A` | 7.3:1 |
  | HIGH     | `#FFF4ED` | `#7C3005` | `#C2520C` | 8.5:1 |
  | MODERATE | `#FFFBEB` | `#6B4C00` | `#B07D0A` | 7.6:1 |
  | LOW      | `#F0FDF4` | `#14532D` | `#16863E` | 8.7:1 |

- Card background: `#FFFFFF`, border: `1px solid #D1DBE8`, border-radius `8px`, `box-shadow: 0 2px 8px rgba(0,0,0,0.06)`.
- Header row background: `#F7F9FC`.
- If `emergency_readiness.recommendation` is present, render it as a footer row below the metric rows, background `#F0F6FF`, text `#0F1F2E`.
- If `emergency_readiness.actions` is present, render as a compact bulleted list below the recommendation.

**What each field represents:**
- `flood_risk` — agent's cross-reference of predicted rainfall intensity against drainage capacity documents (BBMP master plan, 2022 flood post-mortems) and lake water level telemetry.
- `power_outage_risk` — probability derived from wind-speed telemetry merged with tree-density maps and historical outage incident logs.
- `traffic_delay_index` — estimated delay factor from rainfall-threshold/traffic-bottleneck correlation in historical congestion heatmaps.
- `health_advisory` — AQI sensor reading synthesized with Urban Heat Island research docs; `aqi_category` surfaces the advisory level for sensitive populations.
- `emergency_readiness` — agent's final recommendation and specific action items (e.g., underpass barricading, evacuation routes).

### 5.5 ArtifactRenderer

Rendered inline within an assistant message **only when the backend returns an `artifact` object** in the chat response. For v1, the agent may return **HTML artifacts only**. No JSX, runtime code execution, or client-side chart evaluation is part of this spec.

#### 5.5.1 What the agent sends

The backend forwards an artifact payload with a fixed HTML-only shape:

```typescript
interface ArtifactPayload {
  type: "html";
  title: string;                 // e.g. "Rainfall Trend — Sarjapur Road (7 days)"
  source: string;                // raw HTML string from the agent service
  description?: string;          // optional plain-text alt description for screen readers
}
```

Examples of artifacts the agent might produce:
- An HTML `<table>` of neighborhood AQI readings ranked by severity
- An inline SVG rainfall trend chart
- A compact HTML risk-comparison panel across locations

#### 5.5.2 Sanitization and sandboxing

The renderer receives an `ArtifactPayload` and converts it into a safe render target.

1. Receive the raw HTML string from the backend.
2. Sanitize it with DOMPurify before any rendering.
3. Render the sanitized markup inside a sandboxed `<iframe srcDoc={sanitizedHtml} />`.
4. Keep the iframe isolated from the main app so agent-generated markup cannot affect app styles, script execution, or global state.

**Allowed artifact content for v1:**
- plain HTML elements such as `div`, `span`, `p`, `table`, `thead`, `tbody`, `tr`, `td`, `th`, `ul`, `li`
- inline SVG for charts
- inline styles only if explicitly allowed by the sanitizer configuration

**Disallowed artifact content for v1:**
- `<script>`
- inline event handlers such as `onclick`
- external resource URLs
- remote images, fonts, or stylesheets
- nested iframes
- arbitrary JavaScript execution

**Security rules (non-negotiable):**
- HTML artifacts must be sanitized before insertion into `srcDoc`.
- The iframe sandbox must stay strict; do not combine permissive flags such as `allow-scripts` and `allow-same-origin` for agent-generated content.
- If sanitization strips most or all of the content, fall back to a safe error state plus the optional `description`.

#### 5.5.3 ArtifactRenderer component

```
┌─────────────────────────────────────────────────┐
│  📊  Rainfall Trend — Sarjapur Road (7 days)    │  ← title bar
│                                          [⤢ expand] │
├─────────────────────────────────────────────────┤
│                                                 │
│         [rendered chart / graph here]           │
│                                                 │
└─────────────────────────────────────────────────┘
```

- **Title bar:** `#F7F9FC` background, `border-bottom: 1px solid #D1DBE8`. Icon prefix (📊 for charts, 📋 for tables, 🗺 for maps). Title in IBM Plex Sans 13px `#0F1F2E`. Expand button `[⤢]` opens the artifact full-screen in a Modal (`aria-modal="true"`).
- **Content area:** White background, `min-height: 200px`, `max-height: 480px`, overflow hidden (scrollable if content exceeds). For iframes, set `width: 100%` and auto-size height to the sanitized content.
- **Error state:** If parsing or rendering fails, show a bordered `#FFF0F2` panel with icon ⚠, message "Chart could not be rendered", and the `description` text if available.
- **Loading state:** Skeleton shimmer while sanitization completes.
- **Accessibility:** `role="figure"`, `aria-label={artifact.title}`. If `description` is present, include a visually hidden `<figcaption>` for screen readers. Expand button: `aria-label="Expand chart: {title}"`.

#### 5.5.4 Expand / full-screen Modal

- Triggered by the `[⤢]` button or keyboard `Enter`/`Space` on it.
- MUI `<Dialog fullWidth maxWidth="lg">`, `aria-modal="true"`, `aria-labelledby` pointing to the title.
- Focus is trapped inside the modal while open. `Escape` closes it and returns focus to the expand button.
- Modal renders the same sanitized artifact at full width.

### 5.6 ThinkingIndicator

Shown while awaiting agent response.

- Three animated dots (CSS pulse) + label "Analyzing sensor data…" in IBM Plex Sans 13px, colour `#4A5568`.
- Wrap in `role="status" aria-live="polite" aria-label="Agent is analyzing sensor data"` so screen readers announce it without being disruptive.
- Disappears as soon as the response arrives or fails.

### 5.7 InputBar

- Sticky bottom, `background: #FFFFFF`, `border-top: 1px solid #D1DBE8`.
- `<textarea>` auto-resizes (1–4 rows). Background `#F7F9FC`, border `1px solid #C9D6E3`, text `#0F1F2E`. Placeholder text `#6B7B8D` (contrast 4.6:1 — AA).
- Visible `:focus` ring: `outline: 2px solid #005F8E`, `outline-offset: 2px` — never `outline: none`.
- Placeholder text: `"Ask about flood risk, AQI, traffic, power…"`.
- **Send button:** background `#005F8E`, icon + text label "Send" (visually hidden text for screen readers via `aria-label="Send message"`). Disabled state: `#C9D6E3` background, `#6B7B8D` text, `aria-disabled="true"`. `Enter` submits, `Shift+Enter` newline.
- **Abort:** optional for v1. If implemented, it cancels the in-flight request and the button becomes "Stop" (square icon, `background: #DC2626`, `aria-label="Stop response"`). Never rely on colour alone — icon + label both change.

### 5.8 SuggestedPrompts

Shown only in the empty state (no messages yet). These reflect the UrbanClimate AI's core capabilities.

Four chips in a 2×2 grid:
- "If it rains 60mm tonight, which underpasses should be barricaded?"
- "How does current humidity compare to pre-monsoon averages of the last decade?"
- "Which logistics routes through Bengaluru are highest risk today?"
- "Generate a risk scorecard for Sarjapur Road."

> **Note:** Only the last prompt reliably triggers a RiskCard — it explicitly requests a structured scorecard. The others are natural language queries that usually return plain text. Chips are for user convenience, not a trigger mechanism.

Clicking a chip populates and submits the textarea.

---

## 6. API Contract

### POST `/api/chat`

**Request:**
```json
{
  "session_id": "uuid-v4",
  "message": "If it rains 60mm tonight, which underpasses should be barricaded based on previous years?"
}
```

**Response (`application/json`):**
```json
{
  "message": "Based on drainage capacity reports and recent rainfall patterns, Sarjapur Road has elevated flood risk tonight.",
  "risk_card": {
    "neighborhood": "SARJAPUR ROAD",
    "generated_at": "2026-03-10T12:00:00Z",
    "overall_risk_score": 9.1
  },
  "artifact": {
    "type": "html",
    "title": "Rainfall Trend - Sarjapur Road",
    "source": "<div>...</div>",
    "description": "Seven-day rainfall trend for Sarjapur Road"
  }
}
```

`risk_card` and `artifact` are both optional. Most responses will return `message` text only.

**Error response:**
```json
{
  "error": {
    "code": "AGENT_UNAVAILABLE",
    "message": "The agent service is currently unavailable."
  }
}
```

**GET `/api/health`** — used by `StatusPill` to poll composite system health every 30 seconds.

Recommended response shape:
```json
{
  "backend": "ok",
  "agent": "ok",
  "status": "online"
}
```

Example degraded response:
```json
{
  "backend": "ok",
  "agent": "down",
  "status": "degraded"
}
```

The frontend behavior should be:
- render `message` as the assistant reply
- render `risk_card` only when the response includes it
- render `artifact` only when the response includes it
- show degraded state when backend is reachable but agent health is not `ok`

---

## 7. Risk Card JSON Schema

The agent returns this as a `risk_card` payload when it determines a structured neighborhood scorecard is the appropriate response. The frontend renders it as a RiskCard component. All top-level metric fields are optional — the agent only populates fields it has sufficient data to compute.

```typescript
interface RiskCardPayload {
  neighborhood: string;           // e.g. "SARJAPUR ROAD", "BELLANDUR", "MANYATA TECH PARK"
  generated_at: string;           // ISO 8601 — timestamp of agent analysis
  overall_risk_score: number;     // 0–10 composite score

  // Cross-reference: DB rainfall forecast + drainage capacity docs + lake telemetry
  flood_risk?: {
    probability: number;          // 0–1
    severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  };

  // Cross-reference: wind-speed telemetry + tree-density maps + historical outage logs
  power_outage_risk?: {
    probability: number;          // 0–1
    severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  };

  // Derived from: rainfall threshold / traffic bottleneck historical correlation
  traffic_delay_index?: {
    congestion_score: number;     // 0–10
    severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  };

  // Derived from: AQI sensor data + Urban Heat Island research docs
  health_advisory?: {
    aqi: number;                  // raw AQI value
    aqi_category: string;         // e.g. "GOOD", "MODERATE", "UNHEALTHY FOR SENSITIVE GROUPS", "UNHEALTHY", "HAZARDOUS"
  };

  // Agent's final recommendations based on full cross-analysis
  emergency_readiness?: {
    recommendation: string;       // e.g. "Evacuate low-lying zones; barricade underpasses"
    actions?: string[];           // Specific action items, e.g. ["Barricade Silk Board underpass", "Pre-position pumps at Bellandur inlet"]
  };
}
```

---

## 8. State Management

No external state library needed. Use React `useState` + `useRef`.

```typescript
// ChatPage state
const [messages, setMessages] = useState<Message[]>([]);
const [input, setInput] = useState('');
const [isSending, setIsSending] = useState(false);
const [agentStatus, setAgentStatus] = useState<'online' | 'connecting' | 'degraded'>('connecting');
const sessionId = useRef(crypto.randomUUID());
```

```typescript
interface ArtifactPayload {
  type: 'html';
  title: string;
  source: string;              // raw HTML string from the agent
  description?: string;        // plain-text alt for screen readers / error fallback
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  riskCard?: RiskCardPayload;  // optional structured block
  artifact?: ArtifactPayload;  // optional chart / visualisation artifact
  timestamp: Date;
  isError?: boolean;
}
```

Artifact sanitization state is managed separately inside `ArtifactRenderer` — it does not live on `Message` to avoid polluting the message store with transient UI state.

---

## 9. File Structure

```
client/src/
├── App.tsx                        # Single route → ChatPage
├── main.tsx                       # Providers (ThemeProvider, etc.)
├── lib/
│   ├── api.ts                     # Axios instance (already in scaffold)
│   └── artifactSandbox.ts         # DOMPurify wrapper + iframe srcDoc helpers
├── hooks/
│   └── useChat.ts                 # All chat logic: send request, map response, manage session
├── components/
│   ├── layout/
│   │   └── Header.tsx
│   ├── chat/
│   │   ├── MessageList.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── RiskCard.tsx
│   │   ├── ArtifactRenderer.tsx   # Sandboxed iframe for sanitized HTML artifacts
│   │   ├── ThinkingIndicator.tsx
│   │   └── SuggestedPrompts.tsx
│   └── input/
│       └── InputBar.tsx
├── pages/
│   └── ChatPage.tsx
├── types/
│   └── chat.ts                    # Message, RiskCardPayload, ArtifactPayload interfaces
└── theme/
    └── metrosense.ts              # MUI theme overrides
```

---

## 10. Styling

### 10.1 Colour Tokens

All values verified at WCAG 2.1 AA (text ≥ 4.5:1, UI components ≥ 3:1).

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#F7F9FC` | Page / app background |
| `--bg-surface` | `#FFFFFF` | Cards, bubbles, panels |
| `--bg-sunken` | `#EEF2F7` | User bubble, input field |
| `--border` | `#D1DBE8` | All dividers and borders |
| `--border-strong` | `#C9D6E3` | Input fields, card outlines |
| `--text-primary` | `#0F1F2E` | All body text (15.9:1 on `--bg-page`) |
| `--text-secondary` | `#4A5568` | Labels, timestamps (7.1:1 on `--bg-page`) |
| `--text-placeholder` | `#6B7B8D` | Input placeholder (4.6:1 — AA) |
| `--accent` | `#005F8E` | Primary action, links, AI bubble border (6.6:1 on white) |
| `--accent-hover` | `#004A70` | Hover/active state |
| `--accent-text` | `#FFFFFF` | Text on `--accent` buttons (6.9:1) |
| `--sev-critical-bg` | `#FFF0F2` | CRITICAL badge background |
| `--sev-critical-text` | `#9B1D2A` | CRITICAL badge text (7.3:1) |
| `--sev-critical-bar` | `#C0213A` | CRITICAL progress bar |
| `--sev-high-bg` | `#FFF4ED` | HIGH badge background |
| `--sev-high-text` | `#7C3005` | HIGH badge text (8.5:1) |
| `--sev-high-bar` | `#C2520C` | HIGH progress bar |
| `--sev-moderate-bg` | `#FFFBEB` | MODERATE badge background |
| `--sev-moderate-text` | `#6B4C00` | MODERATE badge text (7.6:1) |
| `--sev-moderate-bar` | `#B07D0A` | MODERATE progress bar |
| `--sev-low-bg` | `#F0FDF4` | LOW badge background |
| `--sev-low-text` | `#14532D` | LOW badge text (8.7:1) |
| `--sev-low-bar` | `#16863E` | LOW progress bar |

### 10.2 MUI Theme Override

```typescript
// theme/metrosense.ts
{
  palette: {
    mode: 'light',
    background: { default: '#F7F9FC', paper: '#FFFFFF' },
    primary: { main: '#005F8E', contrastText: '#FFFFFF' },
    error:   { main: '#C0213A' },
    warning: { main: '#B07D0A' },
    success: { main: '#16863E' },
    text: { primary: '#0F1F2E', secondary: '#4A5568', disabled: '#6B7B8D' }
  },
  typography: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: 14,
    // Mono variant: sx={{ fontFamily: 'IBM Plex Mono, monospace' }}
  },
  components: {
    MuiButtonBase: {
      defaultProps: { disableRipple: false },
      styleOverrides: {
        root: {
          '&:focus-visible': {
            outline: '2px solid #005F8E',
            outlineOffset: '2px',
          }
        }
      }
    }
  }
}
```

### 10.3 Accessibility Requirements

- **Focus rings:** Every interactive element must show a visible `2px solid #005F8E` focus ring on keyboard focus. Never suppress `outline`.
- **Colour independence:** Every status, severity, and state must also communicate via text label or icon — not colour alone.
- **Touch targets:** All buttons and chips minimum `44 × 44px` tap target (WCAG 2.5.5).
- **Motion:** Wrap all non-essential animations in `@media (prefers-reduced-motion: reduce)` — disable or reduce them.
- **Semantic HTML:** Use `<main>`, `<header>`, `<section aria-label>` landmark roles. Message list: `role="log" aria-live="polite" aria-label="Conversation"`. Loading indicator: `role="status" aria-live="polite"`.
- **Minimum font size:** 13px for any visible text. Secondary/timestamp labels may be 11px only if colour contrast ≥ 7:1.
- **Link underlines:** Inline links in message text must be underlined (not colour-only).
- **Custom scrollbar:** Thin, `#C9D6E3` track, `#005F8E` thumb. Ensure scrollbar thumb contrast ≥ 3:1 against track.

---

## 11. Environment Variables

Add to the scaffold's existing env var pattern:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_SERVER_URL` | `http://agents:8020` | Internal Agent Server URL (Docker Compose service name). Used by the backend to call the internal agent service. |
| `AGENT_INTERNAL_TOKEN` | `change-me` | Shared secret header value sent from backend to agent proxy (`X-Internal-Token`). |
| `VITE_API_BASE_URL` | *(proxied via Vite → :8010)* | Frontend API base (already handled by Vite proxy in scaffold) |

---

## 12. Backend Route to Add

Add one route to `server/app/api/routes/`:

```
server/app/api/routes/chat.py
```

Responsibilities:
- Accept `POST /api/chat` with `{ session_id, message }`.
- Call the Agent Server via `agent_proxy.get_chat_response()`.
- Return a single JSON response with `message`, optional `risk_card`, and optional `artifact`.
- Accept `GET /api/health` and return composite backend + agent health for the frontend status pill.
- Accept `DELETE /api/chat/{session_id}` to clear agent session state if session reset is implemented.

Add one service:

```
server/app/services/agent_proxy.py
```

Responsibilities:
- `async def get_chat_response(session_id, message) -> ChatResponse`
- Call the internal `agents/` service over HTTP at `AGENT_SERVER_URL`.
- Normalize agent failures into backend-owned error responses.
- Handle timeout (30s) and connection errors cleanly.

Add to `docker-compose.yml`:

```yaml
agents:
  build: ./agents         # your Agent Server directory
  ports:
    - "8020:8020"         # internal service port
  depends_on:
    - db
  environment:
    - DATABASE_URL=${DATABASE_URL}
```

---

## 13. Validation Scenarios

- `POST /api/chat` returns text-only responses and renders a plain assistant bubble.
- `POST /api/chat` returns text + `risk_card` and renders both in one assistant message.
- `POST /api/chat` returns text + `artifact` and renders the sanitized HTML artifact in a sandboxed iframe.
- Sanitization strips scripts, event handlers, nested iframes, and external URLs from artifact HTML.
- Invalid or mostly stripped artifact HTML falls back to a safe error panel plus `description` if provided.
- `GET /api/health` returning backend `ok` + agent `down` renders the status pill as degraded.
- Backend timeout or agent unavailability produces a user-visible error state without breaking existing messages.

---

## 14. Out of Scope (Not in this spec)

- Authentication / user accounts.
- Chat history persistence (no DB writes for chat messages).
- Map rendering (separate concern — existing MetroSense dashboard).
- Mobile-specific layout (responsive is sufficient — no native app).
- Multi-agent routing or tool call visibility in the UI.
- **Keyword-based or client-side RiskCard triggering.** The frontend must never inspect message content to decide whether to show a RiskCard. That decision belongs entirely to the agent.
- **Executable artifacts.** JSX, arbitrary JavaScript, dynamic chart library evaluation, and client-side code generation are out of scope for v1.
- **External resource loading inside artifacts.** No remote fonts, images, stylesheets, scripts, or nested frames.
- **Agent-side artifact generation logic.** This spec covers parsing, sanitization, and rendering on the frontend, not how the agent decides to produce the artifact.
- **Streaming chat responses.** V1 chat is request/response JSON only.

---

## 15. Implementation Order

1. `theme/metrosense.ts` — get the design tokens right first.
2. `Header.tsx` + `StatusPill` — static shell.
3. `types/chat.ts` — lock the interfaces including `ArtifactPayload`.
4. `useChat.ts` hook — request/response chat logic with loading, error, and session handling.
5. `InputBar.tsx` + `SuggestedPrompts.tsx`.
6. `MessageBubble.tsx` + `ThinkingIndicator.tsx`.
7. `RiskCard.tsx`.
8. `lib/artifactSandbox.ts` — DOMPurify wrapper and iframe `srcDoc` helper; write sanitizer tests before wiring into the UI.
9. `ArtifactRenderer.tsx` — compose the title bar, sandboxed content area, expand Modal, loading skeleton, and error state.
10. `MessageList.tsx` — compose bubbles including `ArtifactRenderer`, auto-scroll logic.
11. `ChatPage.tsx` — wire everything together.
12. `server/app/api/routes/chat.py` + `agent_proxy.py` — real backend integration using JSON responses and composite health.
13. Add focused tests for health degradation, chat success states, and artifact sanitization fallback behavior.
