import { createTheme } from "@mui/material/styles";

const metrosenseTheme = createTheme({
  palette: {
    mode: "light",
    background: {
      default: "#F7F9FC",
      paper: "#FFFFFF",
    },
    primary: {
      main: "#005F8E",
      contrastText: "#FFFFFF",
    },
    error: { main: "#C0213A" },
    warning: { main: "#B07D0A" },
    success: { main: "#16863E" },
    text: {
      primary: "#0F1F2E",
      secondary: "#4A5568",
      disabled: "#6B7B8D",
    },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: '"IBM Plex Sans", sans-serif',
    fontSize: 14,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage:
            "radial-gradient(circle at top left, rgba(0,95,142,0.08), transparent 30%), linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%)",
        },
      },
    },
    MuiButtonBase: {
      styleOverrides: {
        root: {
          "&:focus-visible": {
            outline: "2px solid #005F8E",
            outlineOffset: "2px",
          },
        },
      },
    },
  },
});

export default metrosenseTheme;
