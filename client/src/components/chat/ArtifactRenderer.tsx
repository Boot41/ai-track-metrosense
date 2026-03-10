import { useMemo, useState } from "react";
import OpenInFullRoundedIcon from "@mui/icons-material/OpenInFullRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { Box, Dialog, DialogContent, DialogTitle, IconButton, Skeleton, Stack, Typography } from "@mui/material";
import { buildArtifactSrcDoc, sanitizeArtifactHtml } from "@/lib/artifactSandbox";
import type { ArtifactPayload } from "@/types/chat";

interface ArtifactRendererProps {
  artifact: ArtifactPayload;
}

export default function ArtifactRenderer({ artifact }: ArtifactRendererProps) {
  const [open, setOpen] = useState(false);

  const sanitized = useMemo(() => sanitizeArtifactHtml(artifact.source), [artifact.source]);
  const srcDoc = useMemo(() => buildArtifactSrcDoc(sanitized, artifact.title), [sanitized, artifact.title]);
  const hasRenderableContent = sanitized.length > 0;

  const frame = hasRenderableContent ? (
    <Box
      component="iframe"
      title={artifact.title}
      srcDoc={srcDoc}
      sandbox=""
      sx={{ width: "100%", height: 280, border: 0, display: "block", backgroundColor: "#fff" }}
    />
  ) : (
    <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ border: "1px solid #F2C7CE", borderRadius: 2, backgroundColor: "#FFF0F2", p: 2 }}>
      <WarningAmberRoundedIcon color="error" />
      <Box>
        <Typography fontWeight={700}>Chart could not be rendered</Typography>
        <Typography color="text.secondary">{artifact.description ?? "The artifact did not contain safe renderable HTML."}</Typography>
      </Box>
    </Stack>
  );

  return (
    <Box role="figure" aria-label={artifact.title} sx={{ border: "1px solid #D1DBE8", borderRadius: 2, overflow: "hidden", backgroundColor: "#fff" }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 2, py: 1.25, backgroundColor: "#F7F9FC", borderBottom: "1px solid #D1DBE8" }}>
        <Typography fontSize={13} fontWeight={600}>
          {artifact.title}
        </Typography>
        <IconButton aria-label={`Expand chart: ${artifact.title}`} onClick={() => setOpen(true)}>
          <OpenInFullRoundedIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Box sx={{ p: 2, minHeight: 200 }}>
        {artifact.source ? frame : <Skeleton variant="rounded" height={220} />}
      </Box>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="lg" aria-modal="true">
        <DialogTitle>{artifact.title}</DialogTitle>
        <DialogContent>{frame}</DialogContent>
      </Dialog>
    </Box>
  );
}
