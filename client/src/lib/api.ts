import axios from "axios";
import type { ChatRequest, ChatResponse, HealthResponse } from "@/types/chat";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/",
});

export async function postChat(payload: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>("/api/chat", payload);
  return response.data;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/api/health");
  return response.data;
}

export default api;
