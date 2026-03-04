import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography, Button } from '@mui/material';

/**
 * Handles redirect from backend after Microsoft SSO: reads access_token and
 * refresh_token from URL fragment (preferred) or query params, stores in localStorage,
 * then redirects to /. AuthContext will load current user when the app renders.
 */
function parseFragmentParams() {
  const hash = window.location.hash.replace(/^#/, '');
  if (!hash) return {};
  return Object.fromEntries(new URLSearchParams(hash));
}

const LoginCallback = () => {
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const fragment = parseFragmentParams();
    const q = new URLSearchParams(window.location.search);
    const access = fragment.access_token || q.get('access_token');
    const refresh = fragment.refresh_token || q.get('refresh_token');
    const err = fragment.error || q.get('error');

    if (err) {
      setError(err);
      return;
    }
    if (!access || !refresh) {
      setError('Missing tokens');
      return;
    }

    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    window.history.replaceState({}, document.title, window.location.pathname);
    navigate('/', { replace: true });
  }, [navigate]);

  const errorMessages = {
    unauthorized_tenant: 'This account is not from the allowed organization.',
    wrong_tenant: 'This account is not from the allowed organization.',
    invalid_state: 'Invalid state. Please try signing in again.',
    token_exchange_failed: 'Token exchange failed. Please try again.',
    no_id_token: 'No identity token received.',
    invalid_id_token: 'Invalid identity token.',
    no_email: 'No email in account.',
  };

  if (error) {
    const message = errorMessages[error] || error;
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', p: 2 }}>
        <Typography color="error" sx={{ mb: 2 }}>
          Sign-in failed: {message}
        </Typography>
        <Button variant="contained" href="/login" sx={{ mt: 1 }}>
          Try again
        </Button>
        <Typography component="a" href="/login" sx={{ color: 'primary.main', mt: 2, display: 'block' }}>
          Return to login
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <CircularProgress />
      <Typography sx={{ mt: 2 }}>Signing you in...</Typography>
    </Box>
  );
};

export default LoginCallback;
