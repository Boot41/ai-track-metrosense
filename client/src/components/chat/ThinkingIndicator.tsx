import { Box, Stack, Typography } from "@mui/material";

export default function ThinkingIndicator() {
  return (
    <Stack
      direction="row"
      spacing={1.5}
      alignItems="center"
      role="status"
      aria-live="polite"
      aria-label="Agent is analyzing sensor data"
      sx={{ color: "text.secondary", px: 1, py: 1 }}
    >
      <Stack direction="row" spacing={0.5}>
        {[0, 1, 2].map((dot) => (
          <Box
            key={dot}
            sx={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "primary.main",
              animation: "pulse 1.2s ease-in-out infinite",
              animationDelay: `${dot * 0.12}s`,
              "@keyframes pulse": {
                "0%, 80%, 100%": { opacity: 0.25, transform: "scale(0.8)" },
                "40%": { opacity: 1, transform: "scale(1)" },
              },
              "@media (prefers-reduced-motion: reduce)": {
                animation: "none",
              },
            }}
          />
        ))}
      </Stack>
      <Typography fontSize={13}>Analyzing sensor data...</Typography>
    </Stack>
  );
}
