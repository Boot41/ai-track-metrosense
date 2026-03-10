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

export interface RiskCardPayload {
  neighborhood: string;
  generated_at: string;
  overall_risk_score: number;
  flood_risk?: RiskMetric;
  power_outage_risk?: RiskMetric;
  traffic_delay_index?: RiskMetric;
  health_advisory?: HealthAdvisory;
  emergency_readiness?: EmergencyReadiness;
}

export interface ArtifactPayload {
  type: "html";
  title: string;
  source: string;
  description?: string;
}

export interface ChatResponse {
  message: string;
  risk_card?: RiskCardPayload | null;
  artifact?: ArtifactPayload | null;
}

export interface ChatRequest {
  session_id: string;
  message: string;
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
  isError?: boolean;
}
