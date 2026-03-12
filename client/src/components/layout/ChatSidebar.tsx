import AddRoundedIcon from "@mui/icons-material/AddRounded";
import ChatBubbleOutlineRoundedIcon from "@mui/icons-material/ChatBubbleOutlineRounded";
import { Box, Button, List, ListItemButton, ListItemText, Typography } from "@mui/material";
import type { ChatSessionSummary } from "@/types/chat";

interface ChatSidebarProps {
  sessions: ChatSessionSummary[];
  selectedSessionId: string | null;
  onCreateNew: () => void;
  onSelectSession: (sessionId: string) => void;
}

function formatTime(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(timestamp);
}

export default function ChatSidebar({
  sessions,
  selectedSessionId,
  onCreateNew,
  onSelectSession,
}: ChatSidebarProps) {
  return (
    <Box
      sx={{
        width: 300,
        borderRight: "1px solid #D1DBE8",
        backgroundColor: "#F7F9FC",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
        flexShrink: 0,
      }}
    >
      <Box sx={{ p: 2, borderBottom: "1px solid #D1DBE8" }}>
        <Button variant="contained" startIcon={<AddRoundedIcon />} fullWidth onClick={onCreateNew}>
          New Chat
        </Button>
      </Box>
      <Box sx={{ px: 2, py: 1 }}>
        <Typography variant="caption" sx={{ color: "text.secondary", letterSpacing: "0.08em" }}>
          PREVIOUS CHATS
        </Typography>
      </Box>
      <List dense sx={{ px: 1, py: 0, overflowY: "auto", flex: 1, minHeight: 0 }}>
        {sessions.map((session) => (
          <ListItemButton
            key={session.session_id}
            selected={selectedSessionId === session.session_id}
            onClick={() => onSelectSession(session.session_id)}
            sx={{
              mb: 0.5,
              borderRadius: 1.5,
              alignItems: "flex-start",
            }}
          >
            <ChatBubbleOutlineRoundedIcon sx={{ mr: 1, mt: 0.3, color: "text.secondary" }} fontSize="small" />
            <ListItemText
              primary={
                <Typography variant="body2" fontWeight={600} sx={{ lineHeight: 1.3 }}>
                  {session.title}
                </Typography>
              }
              secondary={
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  {formatTime(session.last_active_at)}
                </Typography>
              }
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}
