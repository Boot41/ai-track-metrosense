import { useEffect, useMemo, useRef, useState } from "react";
import { Box, Stack, Typography } from "@mui/material";
import MessageBubble from "@/components/chat/MessageBubble";
import ThinkingIndicator from "@/components/chat/ThinkingIndicator";
import type { Message } from "@/types/chat";

interface MessageListProps {
  isSending: boolean;
  messages: Message[];
  readOnlyMode?: boolean;
}

export default function MessageList({ isSending, messages, readOnlyMode = false }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || !stickToBottom) {
      return;
    }
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages, isSending, stickToBottom]);

  const emptyState = useMemo(
    () => (
      <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
        <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
          Bengaluru climate intelligence, one question at a time.
        </Typography>
        <Typography>
          Ask about flood risk, air quality, traffic disruption, or infrastructure readiness.
        </Typography>
      </Box>
    ),
    [],
  );

  return (
    <Box
      ref={containerRef}
      role="log"
      aria-live="polite"
      aria-label="Conversation"
      onScroll={(event) => {
        const node = event.currentTarget;
        const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 48;
        setStickToBottom(nearBottom);
      }}
      sx={{ flex: 1, overflowY: "auto", px: { xs: 2, md: 4 }, py: 3 }}
    >
      {messages.length === 0 ? emptyState : <Stack spacing={2}>{messages.map((message) => <MessageBubble key={message.id} message={message} />)}</Stack>}
      {readOnlyMode ? (
        <Box
          sx={{
            mt: 2,
            border: "1px solid #E5C56A",
            backgroundColor: "#FFF8E1",
            borderRadius: 2,
            px: 2,
            py: 1.5,
          }}
        >
          <Typography variant="body2" fontWeight={600} color="#7A5A00">
            Viewing previous chat (read-only). Start a new chat to send messages.
          </Typography>
        </Box>
      ) : null}
      {isSending ? <ThinkingIndicator /> : null}
    </Box>
  );
}
