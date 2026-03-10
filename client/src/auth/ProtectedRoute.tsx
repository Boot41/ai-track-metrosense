import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "@/auth/AuthContext";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { loading, user } = useAuth();

  if (loading) {
    return (
      <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
