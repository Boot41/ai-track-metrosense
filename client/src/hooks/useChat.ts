import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AxiosError } from "axios";
import { getHealth, postChat } from "@/lib/api";
import type { AgentStatus, AppError, ArtifactPayload, Message, RiskCardPayload } from "@/types/chat";

const HEALTH_POLL_MS = 30_000;
const PROMPTS = [
  "If it rains 60mm tonight, which underpasses should be barricaded?",
  "How does current humidity compare to pre-monsoon averages of the last decade?",
  "Which logistics routes through Bengaluru are highest risk today?",
  "Generate a risk scorecard for Sarjapur Road.",
];

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}`;
}

function createMessage(partial: Omit<Message, "id" | "timestamp">): Message {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    timestamp: new Date(),
    ...partial,
  };
}

function extractError(error: unknown): AppError {
  if (error instanceof AxiosError) {
    const payload = error.response?.data as { error?: AppError } | undefined;
    if (payload?.error) {
      return payload.error;
    }
  }
  return {
    code: "UNKNOWN_ERROR",
    message: "Something went wrong while contacting MetroSense.",
  };
}

export interface UseChatResult {
  agentStatus: AgentStatus;
  error: AppError | null;
  input: string;
  isSending: boolean;
  messages: Message[];
  prompts: string[];
  sessionId: string;
  setInput: (value: string) => void;
  sendMessage: (value?: string) => Promise<void>;
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("connecting");
  const [error, setError] = useState<AppError | null>(null);
  const sessionIdRef = useRef<string>(createSessionId());

  const refreshHealth = useCallback(async () => {
    try {
      const response = await getHealth();
      setAgentStatus(response.status);
    } catch {
      setAgentStatus("degraded");
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
    const interval = window.setInterval(() => {
      void refreshHealth();
    }, HEALTH_POLL_MS);
    return () => window.clearInterval(interval);
  }, [refreshHealth]);

  const sendMessage = useCallback(
    async (value?: string) => {
      const messageText = (value ?? input).trim();
      if (!messageText || isSending) {
        return;
      }

      setError(null);
      setIsSending(true);
      setMessages((current) => [
        ...current,
        createMessage({ role: "user", content: messageText }),
      ]);
      setInput("");

      try {
        const response = await postChat({
          session_id: sessionIdRef.current,
          message: messageText,
        });

        const assistantMessage = createMessage({
          role: "assistant",
          content: response.response_text ?? response.message,
          riskCard: response.risk_card ?? undefined,
          artifact: response.artifact ?? undefined,
          dataFreshnessSummary: response.data_freshness_summary ?? undefined,
          followUpPrompt: response.follow_up_prompt ?? undefined,
        });

        setMessages((current) => [...current, assistantMessage]);
      } catch (caughtError) {
        const appError = extractError(caughtError);
        setError(appError);
        setMessages((current) => [
          ...current,
          createMessage({
            role: "assistant",
            content: appError.message,
            isError: true,
          }),
        ]);
      } finally {
        setIsSending(false);
        void refreshHealth();
      }
    },
    [input, isSending, refreshHealth],
  );

  return useMemo(
    () => ({
      agentStatus,
      error,
      input,
      isSending,
      messages,
      prompts: PROMPTS,
      sessionId: sessionIdRef.current,
      setInput,
      sendMessage,
    }),
    [agentStatus, error, input, isSending, messages, sendMessage],
  );
}

export type { ArtifactPayload, RiskCardPayload };
