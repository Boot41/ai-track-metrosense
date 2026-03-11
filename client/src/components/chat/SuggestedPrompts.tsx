import { Stack, Chip } from "@mui/material";

interface SuggestedPromptsProps {
  prompts: string[];
  onSelect: (prompt: string) => void;
}

export default function SuggestedPrompts({ prompts, onSelect }: SuggestedPromptsProps) {
  return (
    <Stack direction="row" flexWrap="wrap" gap={1} aria-label="Suggested prompts">
      {prompts.map((prompt) => (
        <Chip
          key={prompt}
          label={prompt}
          onClick={() => onSelect(prompt)}
          sx={{
            height: "auto",
            minHeight: 44,
            alignItems: "flex-start",
            borderRadius: 3,
            border: "1px solid #C9D6E3",
            backgroundColor: "#fff",
            "& .MuiChip-label": {
              whiteSpace: "normal",
              paddingBlock: 1,
            },
          }}
        />
      ))}
    </Stack>
  );
}
