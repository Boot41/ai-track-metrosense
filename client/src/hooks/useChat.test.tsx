import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getHealth, postChat } from "@/lib/api";
import { useChat } from "@/hooks/useChat";

vi.mock("@/lib/api", () => ({
  getHealth: vi.fn(),
  postChat: vi.fn(),
}));

describe("useChat", () => {
  beforeEach(() => {
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
