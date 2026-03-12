import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AxiosError } from "axios";
import { useAuth } from "@/auth/AuthContext";
import { getChatSession, getChatSessions, getHealth, postChat } from "@/lib/api";
import type {
  AgentStatus,
  AppError,
  ArtifactPayload,
  ChatSessionSummary,
  ChatTranscriptMessage,
  Message,
  RiskCardPayload,
} from "@/types/chat";

const HEALTH_POLL_MS = 30_000;
const ACTIVE_SESSION_STORAGE_KEY = "metrosense_active_session_id";
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

function readActiveSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
}

function writeActiveSessionId(sessionId: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  if (sessionId) {
    window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sessionId);
    return;
  }
  window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
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
  isHistoryLoading: boolean;
  input: string;
  isSending: boolean;
  mode: "live" | "history_readonly";
  messages: Message[];
  prompts: string[];
  selectedHistorySessionId: string | null;
  sessionId: string;
  sessions: ChatSessionSummary[];
  createNewChat: () => void;
  loadHistorySession: (sessionId: string) => Promise<void>;
  setInput: (value: string) => void;
  sendMessage: (value?: string) => Promise<void>;
}

function fromTranscriptMessage(message: ChatTranscriptMessage): Message {
  return {
    id: `${message.timestamp}-${Math.random().toString(16).slice(2)}`,
    role: message.role,
    content: message.message,
    timestamp: new Date(message.timestamp),
  };
}

export function useChat(): UseChatResult {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("connecting");
  const [error, setError] = useState<AppError | null>(null);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [mode, setMode] = useState<"live" | "history_readonly">("live");
  const [selectedHistorySessionId, setSelectedHistorySessionId] = useState<string | null>(null);
  const sessionIdRef = useRef<string>(createSessionId());
  const didAttemptRestoreRef = useRef(false);

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

  const refreshSessions = useCallback(async () => {
    try {
      const response = await getChatSessions();
      setSessions(response.sessions);
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      setMessages([]);
      setInput("");
      setError(null);
      setSessions([]);
      setMode("live");
      setSelectedHistorySessionId(null);
      sessionIdRef.current = createSessionId();
      didAttemptRestoreRef.current = false;
      return;
    }

    didAttemptRestoreRef.current = false;
    void refreshSessions();
  }, [refreshSessions, user]);

  const createNewChat = useCallback(() => {
    setMode("live");
    setSelectedHistorySessionId(null);
    sessionIdRef.current = createSessionId();
    setMessages([]);
    setInput("");
    setError(null);
    writeActiveSessionId(null);
  }, []);

  const hydrateSession = useCallback(
    async (sessionId: string, nextMode: "live" | "history_readonly") => {
      setError(null);
      setIsHistoryLoading(true);
      try {
        const transcript = await getChatSession(sessionId);
        setMessages(transcript.messages.map(fromTranscriptMessage));
        sessionIdRef.current = transcript.session_id;
        setSelectedHistorySessionId(transcript.session_id);
        setMode(nextMode);
        if (nextMode === "live") {
          writeActiveSessionId(transcript.session_id);
        }
      } catch (caughtError) {
        setError(extractError(caughtError));
      } finally {
        setIsHistoryLoading(false);
      }
    },
    [],
  );

  const loadHistorySession = useCallback(async (sessionId: string) => {
    await hydrateSession(sessionId, "history_readonly");
  }, [hydrateSession]);

  useEffect(() => {
    if (!user || didAttemptRestoreRef.current || sessions.length === 0) {
      return;
    }
    didAttemptRestoreRef.current = true;
    const storedSessionId = readActiveSessionId();
    if (!storedSessionId) {
      return;
    }
    const knownSession = sessions.find((item) => item.session_id === storedSessionId);
    if (!knownSession) {
      writeActiveSessionId(null);
      return;
    }
    void hydrateSession(storedSessionId, "live");
  }, [hydrateSession, sessions, user]);

  const sendMessage = useCallback(
    async (value?: string) => {
      const messageText = (value ?? input).trim();
      if (mode !== "live" || !messageText || isSending) {
        return;
      }

      setError(null);
      setIsSending(true);
      setSelectedHistorySessionId(sessionIdRef.current);
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

        writeActiveSessionId(sessionIdRef.current);
        setMessages((current) => [...current, assistantMessage]);
        await refreshSessions();
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
    [input, isSending, mode, refreshHealth, refreshSessions],
  );

  return useMemo(
    () => ({
      agentStatus,
      createNewChat,
      error,
      isHistoryLoading,
      input,
      isSending,
      loadHistorySession,
      mode,
      messages,
      prompts: PROMPTS,
      selectedHistorySessionId,
      sessionId: sessionIdRef.current,
      sessions,
      setInput,
      sendMessage,
    }),
    [
      agentStatus,
      createNewChat,
      error,
      isHistoryLoading,
      input,
      isSending,
      loadHistorySession,
      mode,
      messages,
      selectedHistorySessionId,
      sessions,
      sendMessage,
    ],
  );
}

export type { ArtifactPayload, RiskCardPayload };
