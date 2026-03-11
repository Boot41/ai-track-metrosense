import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getChatSession, getChatSessions, getHealth, postChat } from "@/lib/api";
import { useChat } from "@/hooks/useChat";

vi.mock("@/lib/api", () => ({
  getChatSession: vi.fn(),
  getChatSessions: vi.fn(),
  getHealth: vi.fn(),
  postChat: vi.fn(),
}));

describe("useChat", () => {
  beforeEach(() => {
    vi.mocked(getChatSession).mockResolvedValue({
      session_id: "s-1",
      title: "Old chat",
      last_active_at: "2026-03-10T12:00:00Z",
      messages: [],
    });
    vi.mocked(getChatSessions).mockResolvedValue({ sessions: [] });
    vi.mocked(getHealth).mockResolvedValue({ backend: "ok", agent: "ok", status: "online" });
  });

  it("appends user and assistant messages on success", async () => {
    vi.mocked(postChat).mockResolvedValue({
      response_text: "Agent reply",
      message: "Agent reply",
      risk_card: null,
      artifact: null,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages[0]?.content).toBe("Hello");
    expect(result.current.messages[1]?.content).toBe("Agent reply");
    expect(result.current.agentStatus).toBe("online");
  });

  it("falls back to degraded status when health polling fails", async () => {
    vi.mocked(getHealth).mockRejectedValueOnce(new Error("down"));

    const { result } = renderHook(() => useChat());

    await waitFor(() => expect(result.current.agentStatus).toBe("degraded"));
  });
});
