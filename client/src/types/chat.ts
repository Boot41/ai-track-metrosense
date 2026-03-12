export type AgentStatus = "online" | "connecting" | "degraded";

export interface RiskMetric {
  probability?: number;
  severity?: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  congestion_score?: number;
}

export interface HealthAdvisory {
  aqi?: number;
  aqi_category?: string;
}

export interface EmergencyReadiness {
  recommendation: string;
  actions?: string[];
}

export interface BarricadeRecommendation {
  underpass_name: string;
  reason: string;
}

export interface RiskCardPayload {
  neighborhood: string;
  generated_at: string;
  overall_risk_score: number;
  flood_risk?: RiskMetric;
  power_outage_risk?: RiskMetric;
  traffic_delay_index?: RiskMetric;
  health_advisory?: HealthAdvisory;
  emergency_readiness?: EmergencyReadiness;
  rainfall_expected_mm_per_hr?: number;
  rainfall_classification?: string;
  barricade_recommendations?: BarricadeRecommendation[];
}

export interface HtmlArtifactPayload {
  type: "html";
  title: string;
  source: string;
  description?: string;
}

export interface TableArtifactPayload {
  type: "table";
  title: string;
  columns: string[];
  rows: Array<Array<string | number | null>>;
  description?: string;
}

export type ArtifactPayload = HtmlArtifactPayload | TableArtifactPayload;

export interface ChatResponse {
  /** Primary response text (canonical field). */
  response_text: string;
  /** Backward-compatible alias of response_text. */
  message: string;
  response_mode?: string;
  citations_summary?: Array<Record<string, unknown>>;
  data_freshness_summary?: Record<string, unknown>;
  follow_up_prompt?: string | null;
  risk_card?: RiskCardPayload | null;
  artifact?: ArtifactPayload | null;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatSessionSummary {
  session_id: string;
  title: string;
  last_active_at: string;
  total_turns: number;
}

export interface ChatSessionsResponse {
  sessions: ChatSessionSummary[];
}

export interface ChatTranscriptMessage {
  role: "user" | "assistant";
  message: string;
  timestamp: string;
}

export interface ChatTranscriptResponse {
  session_id: string;
  title: string;
  last_active_at: string;
  messages: ChatTranscriptMessage[];
}

export interface HealthResponse {
  backend: "ok" | "down";
  agent: "ok" | "down";
  status: AgentStatus;
}

export interface AppError {
  code: string;
  message: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  riskCard?: RiskCardPayload;
  artifact?: ArtifactPayload;
  dataFreshnessSummary?: Record<string, unknown>;
  followUpPrompt?: string;
  isError?: boolean;
}
