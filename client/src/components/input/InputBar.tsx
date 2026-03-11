import SendRoundedIcon from "@mui/icons-material/SendRounded";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import { Box, Button, Stack, TextField } from "@mui/material";
import SuggestedPrompts from "@/components/chat/SuggestedPrompts";

interface InputBarProps {
  input: string;
  isSending: boolean;
  readOnlyMode: boolean;
  prompts: string[];
  showPrompts: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onSelectPrompt: (prompt: string) => void;
}

export default function InputBar({
  input,
  isSending,
  readOnlyMode,
  prompts,
  showPrompts,
  onChange,
  onSend,
  onSelectPrompt,
}: InputBarProps) {
  return (
    <Box
      sx={{
        position: "sticky",
        bottom: 0,
        borderTop: "1px solid #D1DBE8",
        backgroundColor: "rgba(255,255,255,0.95)",
        backdropFilter: "blur(12px)",
        px: { xs: 2, md: 4 },
        py: 2,
      }}
    >
      <Stack spacing={2}>
        {showPrompts && !readOnlyMode ? <SuggestedPrompts prompts={prompts} onSelect={onSelectPrompt} /> : null}
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "flex-end" }}>
          <TextField
            fullWidth
            multiline
            minRows={1}
            maxRows={4}
            value={input}
            disabled={readOnlyMode}
            placeholder="Ask about flood risk, AQI, traffic, power..."
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (readOnlyMode) {
                return;
              }
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSend();
              }
            }}
            sx={{
              "& .MuiOutlinedInput-root": {
                backgroundColor: "#F7F9FC",
                alignItems: "flex-start",
              },
            }}
          />
          <Button
            variant="contained"
            onClick={onSend}
            disabled={readOnlyMode || !input.trim() || isSending}
            startIcon={isSending ? <StopRoundedIcon /> : <SendRoundedIcon />}
            sx={{ minHeight: 44, minWidth: { xs: "100%", sm: 132 } }}
            aria-label={isSending ? "Stop response" : "Send message"}
          >
            {isSending ? "Stop" : "Send"}
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}
