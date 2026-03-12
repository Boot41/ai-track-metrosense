import { Box, Stack, Typography } from "@mui/material";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
        {isUser || message.isError ? (
          <Typography sx={{ whiteSpace: "pre-wrap", color: message.isError ? "error.main" : "text.primary" }}>
            {message.content}
          </Typography>
        ) : (
          <Box
            sx={{
              color: "text.primary",
              fontSize: 14,
              lineHeight: 1.7,
              "& p": { mt: 0, mb: 1 },
              "& p:last-child": { mb: 0 },
              "& strong": { fontWeight: 700 },
              "& ul, & ol": { mt: 0.5, mb: 1, pl: 2.5 },
              "& li": { mb: 0.5 },
              "& h1, & h2, & h3": { mt: 1.5, mb: 0.75, fontWeight: 700, lineHeight: 1.3 },
              "& h1": { fontSize: 17 },
              "& h2": { fontSize: 15 },
              "& h3": { fontSize: 14 },
              "& table": {
                borderCollapse: "collapse",
                width: "100%",
                mt: 1,
                mb: 1,
                fontSize: 13,
              },
              "& th": {
                backgroundColor: "#F0F4F8",
                fontWeight: 700,
                px: 1.5,
                py: 0.75,
                textAlign: "left",
                border: "1px solid #D1DBE8",
              },
              "& td": {
                px: 1.5,
                py: 0.75,
                border: "1px solid #D1DBE8",
                verticalAlign: "top",
              },
              "& tr:nth-of-type(even)": { backgroundColor: "#F7F9FC" },
              "& blockquote": {
                borderLeft: "3px solid #005F8E",
                m: 0,
                pl: 1.5,
                color: "text.secondary",
              },
              "& code": {
                fontFamily: '"IBM Plex Mono", monospace',
                fontSize: 12,
                backgroundColor: "#EEF2F7",
                px: 0.5,
                py: 0.2,
                borderRadius: 0.5,
              },
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </Box>
        )}
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
