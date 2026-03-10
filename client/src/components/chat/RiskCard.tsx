import { Box, Divider, LinearProgress, Stack, Typography } from "@mui/material";
import type { RiskCardPayload } from "@/types/chat";

interface RiskCardProps {
  riskCard: RiskCardPayload;
}

const severityStyles = {
  CRITICAL: { bg: "#FFF0F2", text: "#9B1D2A", bar: "#C0213A" },
  HIGH: { bg: "#FFF4ED", text: "#7C3005", bar: "#C2520C" },
  MODERATE: { bg: "#FFFBEB", text: "#6B4C00", bar: "#B07D0A" },
  LOW: { bg: "#F0FDF4", text: "#14532D", bar: "#16863E" },
} as const;

function MetricRow({ label, value, severity, progress }: { label: string; value: string; severity: keyof typeof severityStyles; progress: number }) {
  const palette = severityStyles[severity];
  return (
    <Stack spacing={0.75}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" gap={2}>
        <Typography fontFamily='"IBM Plex Mono", monospace' fontSize={12} letterSpacing="0.08em">
          {label}
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography fontWeight={600}>{value}</Typography>
          <Box sx={{ backgroundColor: palette.bg, color: palette.text, px: 1, py: 0.3, borderRadius: 10, fontSize: 12, fontWeight: 700 }}>
            {severity}
          </Box>
        </Stack>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={Math.max(0, Math.min(100, progress))}
        sx={{
          height: 8,
          borderRadius: 999,
          backgroundColor: "#EEF2F7",
          "& .MuiLinearProgress-bar": { backgroundColor: palette.bar },
        }}
      />
    </Stack>
  );
}

export default function RiskCard({ riskCard }: RiskCardProps) {
  return (
    <Box sx={{ border: "1px solid #D1DBE8", borderRadius: 2, overflow: "hidden", backgroundColor: "#FFFFFF", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 2, py: 1.5, backgroundColor: "#F7F9FC" }}>
        <Typography fontFamily='"IBM Plex Mono", monospace' fontWeight={700}>
          {riskCard.neighborhood}
        </Typography>
        <Typography fontWeight={700}>Risk Score: {riskCard.overall_risk_score.toFixed(1)}</Typography>
      </Stack>

      <Stack spacing={1.5} sx={{ px: 2, py: 2 }}>
        {riskCard.flood_risk ? (
          <MetricRow
            label="FLOOD"
            value={`${Math.round((riskCard.flood_risk.probability ?? 0) * 100)}%`}
            severity={(riskCard.flood_risk.severity ?? "LOW") as keyof typeof severityStyles}
            progress={(riskCard.flood_risk.probability ?? 0) * 100}
          />
        ) : null}
        {riskCard.power_outage_risk ? (
          <MetricRow
            label="POWER OUTAGE"
            value={`${Math.round((riskCard.power_outage_risk.probability ?? 0) * 100)}%`}
            severity={(riskCard.power_outage_risk.severity ?? "LOW") as keyof typeof severityStyles}
            progress={(riskCard.power_outage_risk.probability ?? 0) * 100}
          />
        ) : null}
        {riskCard.traffic_delay_index ? (
          <MetricRow
            label="TRAFFIC"
            value={`${(riskCard.traffic_delay_index.congestion_score ?? 0).toFixed(1)}`}
            severity={(riskCard.traffic_delay_index.severity ?? "LOW") as keyof typeof severityStyles}
            progress={((riskCard.traffic_delay_index.congestion_score ?? 0) / 10) * 100}
          />
        ) : null}
        {riskCard.health_advisory ? (
          <MetricRow
            label="AQI"
            value={`${riskCard.health_advisory.aqi ?? 0}`}
            severity={riskCard.health_advisory.aqi && riskCard.health_advisory.aqi >= 150 ? "HIGH" : riskCard.health_advisory.aqi && riskCard.health_advisory.aqi >= 100 ? "MODERATE" : "LOW"}
            progress={Math.min(100, ((riskCard.health_advisory.aqi ?? 0) / 300) * 100)}
          />
        ) : null}
      </Stack>

      {riskCard.emergency_readiness ? (
        <>
          <Divider />
          <Box sx={{ px: 2, py: 1.5, backgroundColor: "#F0F6FF" }}>
            <Typography fontWeight={600}>{riskCard.emergency_readiness.recommendation}</Typography>
            {riskCard.emergency_readiness.actions?.length ? (
              <Box component="ul" sx={{ mb: 0, mt: 1, pl: 2.5 }}>
                {riskCard.emergency_readiness.actions.map((action) => (
                  <Typography key={action} component="li" sx={{ mb: 0.5 }}>
                    {action}
                  </Typography>
                ))}
              </Box>
            ) : null}
          </Box>
        </>
      ) : null}
    </Box>
  );
}
