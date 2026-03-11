import { useMemo } from "react";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import SyncRoundedIcon from "@mui/icons-material/SyncRounded";
import { Box, Button, ButtonBase, IconButton, Stack, Typography } from "@mui/material";
import type { AgentStatus } from "@/types/chat";
import { useAuth } from "@/auth/AuthContext";

interface HeaderProps {
  agentStatus: AgentStatus;
  sessionId: string;
  onOpenSidebar?: () => void;
}

const STATUS_CONFIG: Record<AgentStatus, { bg: string; border: string; color: string; label: string }> = {
  online: {
    bg: "#F0FDF4",
    border: "#16A34A",
    color: "#14532D",
    label: "Agent Online",
  },
  connecting: {
    bg: "#FFF9EB",
    border: "#CA8A04",
    color: "#6B4C00",
    label: "Connecting...",
  },
  degraded: {
    bg: "#FFF0F2",
    border: "#DC2626",
    color: "#9B1D2A",
    label: "Degraded",
  },
};

function StatusIcon({ status }: { status: AgentStatus }) {
  if (status === "online") {
    return <CheckCircleOutlineRoundedIcon fontSize="small" />;
  }
  if (status === "degraded") {
    return <ErrorOutlineRoundedIcon fontSize="small" />;
  }
  return (
    <SyncRoundedIcon
      fontSize="small"
      sx={{
        animation: "spin 1.2s linear infinite",
        "@keyframes spin": { from: { transform: "rotate(0deg)" }, to: { transform: "rotate(360deg)" } },
        "@media (prefers-reduced-motion: reduce)": { animation: "none" },
      }}
    />
  );
}

export default function Header({ agentStatus, sessionId, onOpenSidebar }: HeaderProps) {
  const statusConfig = STATUS_CONFIG[agentStatus];
  const compactSession = useMemo(() => sessionId.slice(0, 8), [sessionId]);
  const { user, logout } = useAuth();

  return (
    <Box
      component="header"
      sx={{
        position: "sticky",
        top: 0,
        zIndex: 10,
        borderBottom: "1px solid #D1DBE8",
        backgroundColor: "rgba(255,255,255,0.92)",
        backdropFilter: "blur(12px)",
        boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        alignItems={{ xs: "flex-start", md: "center" }}
        justifyContent="space-between"
        sx={{ px: { xs: 2, md: 4 }, py: 2 }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          {onOpenSidebar ? (
            <IconButton
              aria-label="Open chat history"
              onClick={onOpenSidebar}
              sx={{ display: { xs: "inline-flex", md: "none" } }}
            >
              <MenuRoundedIcon />
            </IconButton>
          ) : null}
          <Box>
          <Typography variant="h5" fontWeight={700} letterSpacing="0.08em">
            METROSENSE
          </Typography>
          <Typography
            sx={{
              color: "text.secondary",
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: 11,
              letterSpacing: "0.12em",
            }}
          >
            BENGALURU CLIMATE INTELLIGENCE
          </Typography>
          </Box>
        </Stack>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ xs: "stretch", sm: "center" }}>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{
              borderLeft: `4px solid ${statusConfig.border}`,
              borderRadius: 2,
              backgroundColor: statusConfig.bg,
              color: statusConfig.color,
              px: 1.5,
              py: 1,
            }}
          >
            <StatusIcon status={agentStatus} />
            <Typography fontWeight={600}>{statusConfig.label}</Typography>
          </Stack>

          <ButtonBase
            aria-label="Copy session ID"
            onClick={() => navigator.clipboard?.writeText(sessionId)}
            sx={{
              borderRadius: 2,
              border: "1px solid #D1DBE8",
              px: 1.5,
              py: 1,
              justifyContent: "flex-start",
            }}
          >
            <Typography
              sx={{
                color: "text.secondary",
                fontFamily: '"IBM Plex Mono", monospace',
                fontSize: 11,
                letterSpacing: "0.08em",
              }}
            >
              SESSION · {compactSession}
            </Typography>
          </ButtonBase>
          {user && (
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="body2" color="text.secondary">
                {user.email}
              </Typography>
              <Button variant="outlined" size="small" onClick={() => void logout()}>
                Logout
              </Button>
            </Stack>
          )}
        </Stack>
      </Stack>
    </Box>
  );
}
