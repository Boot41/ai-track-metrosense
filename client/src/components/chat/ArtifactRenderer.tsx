import { useMemo, useState } from "react";
import OpenInFullRoundedIcon from "@mui/icons-material/OpenInFullRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { buildArtifactSrcDoc, sanitizeArtifactHtml } from "@/lib/artifactSandbox";
import type { ArtifactPayload } from "@/types/chat";

interface ArtifactRendererProps {
  artifact: ArtifactPayload;
}

export default function ArtifactRenderer({ artifact }: ArtifactRendererProps) {
  const [open, setOpen] = useState(false);

  const sanitized = useMemo(
    () => (artifact.type === "html" ? sanitizeArtifactHtml(artifact.source) : ""),
    [artifact],
  );
  const srcDoc = useMemo(
    () => (artifact.type === "html" ? buildArtifactSrcDoc(sanitized, artifact.title) : ""),
    [artifact, sanitized],
  );
  const hasRenderableContent = artifact.type === "html" && sanitized.length > 0;

  const frame =
    artifact.type === "table" ? (
      <TableContainer>
        <Table size="small" aria-label={artifact.title}>
          <TableHead>
            <TableRow sx={{ backgroundColor: "#F7F9FC" }}>
              {artifact.columns.map((column) => (
                <TableCell key={column} sx={{ fontWeight: 700, borderBottom: "2px solid #D1DBE8", fontSize: 12 }}>
                  {column}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {artifact.rows.map((row, index) => (
              <TableRow key={`${artifact.title}-${index}`} sx={{ backgroundColor: index % 2 === 0 ? "#FFFFFF" : "#F7F9FC" }}>
                {row.map((cell, cellIndex) => (
                  <TableCell key={`${artifact.title}-${index}-${cellIndex}`} sx={{ fontSize: 13, verticalAlign: "top" }}>
                    {cell == null ? "-" : String(cell)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    ) : hasRenderableContent ? (
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
          <Typography color="text.secondary">
            {artifact.description ?? "The artifact did not contain safe renderable HTML."}
          </Typography>
        </Box>
      </Stack>
    );

  return (
    <Box role="figure" aria-label={artifact.title} sx={{ border: "1px solid #D1DBE8", borderRadius: 2, overflow: "hidden", backgroundColor: "#fff" }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 2, py: 1.25, backgroundColor: "#F7F9FC", borderBottom: "1px solid #D1DBE8" }}>
        <Typography fontSize={13} fontWeight={600}>
          {artifact.title}
        </Typography>
        {artifact.type === "table" ? (
          <Button
            size="small"
            startIcon={<OpenInFullRoundedIcon fontSize="small" />}
            onClick={() => setOpen(true)}
            sx={{ textTransform: "none" }}
          >
            Open table
          </Button>
        ) : (
          <IconButton aria-label={`Expand artifact: ${artifact.title}`} onClick={() => setOpen(true)}>
            <OpenInFullRoundedIcon fontSize="small" />
          </IconButton>
        )}
      </Stack>
      <Box sx={{ p: 2, minHeight: 200 }}>
        {artifact.type === "table" || artifact.source ? frame : <Skeleton variant="rounded" height={220} />}
      </Box>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="lg" aria-modal="true">
        <DialogTitle>{artifact.title}</DialogTitle>
        <DialogContent>{frame}</DialogContent>
      </Dialog>
    </Box>
  );
}
