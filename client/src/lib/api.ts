import axios from "axios";
import type {
  ChatRequest,
  ChatResponse,
  ChatSessionsResponse,
  ChatTranscriptResponse,
  HealthResponse,
} from "@/types/chat";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/",
  withCredentials: true,
});

export async function postChat(payload: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>("/api/chat", payload);
  return response.data;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/api/health");
  return response.data;
}

export async function getChatSessions(limit = 20, offset = 0): Promise<ChatSessionsResponse> {
  const response = await api.get<ChatSessionsResponse>("/api/chat/sessions", { params: { limit, offset } });
  return response.data;
}

export async function getChatSession(sessionId: string): Promise<ChatTranscriptResponse> {
  const response = await api.get<ChatTranscriptResponse>(`/api/chat/sessions/${sessionId}`);
  return response.data;
}

export interface AuthPayload {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  email: string;
}

export async function postSignup(payload: AuthPayload): Promise<UserResponse> {
  const response = await api.post<{ user: UserResponse }>("/api/auth/signup", payload);
  return response.data.user;
}

export async function postLogin(payload: AuthPayload): Promise<UserResponse> {
  const response = await api.post<{ user: UserResponse }>("/api/auth/login", payload);
  return response.data.user;
}

export async function postLogout(): Promise<void> {
  await api.post("/api/auth/logout");
}

export async function getMe(): Promise<UserResponse> {
  const response = await api.get<UserResponse>("/api/auth/me");
  return response.data;
}

export default api;
