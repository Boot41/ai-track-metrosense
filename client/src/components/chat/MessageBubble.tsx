import { Box, Stack, Typography } from "@mui/material";
import ArtifactRenderer from "@/components/chat/ArtifactRenderer";
import RiskCard from "@/components/chat/RiskCard";
import type { Message } from "@/types/chat";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <Stack alignItems={isUser ? "flex-end" : "flex-start"} spacing={0.75}>
      <Box
        sx={{
          maxWidth: { xs: "100%", md: isUser ? "72%" : "80%" },
          width: "fit-content",
          borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
          border: isUser ? "1px solid #C9D6E3" : "1px solid #D1DBE8",
          borderLeft: isUser ? undefined : "3px solid #005F8E",
          backgroundColor: isUser ? "#EEF2F7" : "#FFFFFF",
          px: 2,
          py: 1.5,
        }}
      >
        <Typography sx={{ whiteSpace: "pre-wrap", color: message.isError ? "error.main" : "text.primary" }}>
          {message.content}
        </Typography>
        {!isUser && message.riskCard ? (
          <Box sx={{ mt: 1.5 }}>
            <RiskCard riskCard={message.riskCard} />
          </Box>
        ) : null}
        {!isUser && message.artifact ? (
          <Box sx={{ mt: 1.5 }}>
            <ArtifactRenderer artifact={message.artifact} />
          </Box>
        ) : null}
      </Box>
      <Typography sx={{ color: "text.secondary", fontFamily: '"IBM Plex Mono", monospace', fontSize: 11 }}>
        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </Typography>
    </Stack>
  );
}
