import { Link, useNavigate } from "react-router-dom";
import { Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useAuth } from "@/auth/AuthContext";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signup({ email, password });
      navigate("/", { replace: true });
    } catch {
      setError("Unable to create account. Try a different email.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", px: 2 }}>
      <Paper sx={{ width: "100%", maxWidth: 420, p: 4 }}>
        <Stack spacing={2}>
          <Typography variant="h4" fontWeight={700}>
            Create account
          </Typography>
          <Typography color="text.secondary">Sign up to access MetroSense.</Typography>
          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={2}>
              <TextField
                label="Email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                fullWidth
              />
              <TextField
                label="Password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                helperText="Minimum 8 characters"
                fullWidth
              />
              {error && <Typography color="error">{error}</Typography>}
              <Button type="submit" variant="contained" disabled={isSubmitting}>
                Sign up
              </Button>
              <Typography variant="body2">
                Already have an account? <Link to="/login">Sign in</Link>
              </Typography>
            </Stack>
          </Box>
        </Stack>
      </Paper>
    </Box>
  );
}
