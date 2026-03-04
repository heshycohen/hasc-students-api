import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Divider,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { COMPANY_NAME, COMPANY_NAME_PREVIOUS } from '../constants';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';
const MICROSOFT_ONLY = process.env.REACT_APP_MICROSOFT_ONLY === 'true';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const qError = searchParams.get('error');
    if (qError) {
      const messages = {
        invalid_state: 'Invalid state. Please try signing in again.',
        token_exchange_failed: 'Token exchange failed. Please try again.',
        no_id_token: 'No identity token received.',
        invalid_id_token: 'Invalid identity token.',
        wrong_tenant: 'This account is not from the allowed organization.',
        no_email: 'No email in account.',
      };
      setError(messages[qError] || qError);
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(email, password);
    if (result.success) {
      navigate('/');
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f5f5f5', py: 4 }}>
      <Container maxWidth="sm">
        <Box
          sx={{
            marginTop: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
        {/* Logo only – transparent PNG, no rectangle on any background */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            mb: 2,
            backgroundColor: 'transparent',
            '& img': {
              display: 'block',
              maxHeight: 120,
              maxWidth: '100%',
              objectFit: 'contain',
              backgroundColor: 'transparent',
              border: 'none',
              boxShadow: 'none',
              verticalAlign: 'middle',
            },
          }}
        >
          <img
            src={process.env.PUBLIC_URL + '/logo.png'}
            alt={COMPANY_NAME}
            onError={(e) => {
              const el = e.target;
              if (el.dataset.triedSvg) el.style.display = 'none';
              else { el.dataset.triedSvg = '1'; el.src = process.env.PUBLIC_URL + '/logo.svg'; }
            }}
            style={{ background: 'transparent' }}
          />
        </Box>
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Typography component="h1" variant="h6" align="center" gutterBottom sx={{ fontWeight: 600 }}>
            {COMPANY_NAME}
          </Typography>
          <Typography variant="h6" align="center" color="text.secondary" sx={{ mt: -0.5, mb: 1, fontWeight: 500 }}>
            {COMPANY_NAME_PREVIOUS}
          </Typography>
          <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 3 }}>
            HIPAA and FERPA Compliant
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Button
            fullWidth
            variant="contained"
            sx={{ mt: 1, mb: 2 }}
            href={`${API_BASE_URL}/auth/microsoft/login/`}
          >
            Sign in with Microsoft
          </Button>
          {!MICROSOFT_ONLY && (
            <>
              <Divider sx={{ my: 2 }}>or sign in with email</Divider>
              <form onSubmit={handleSubmit}>
                <TextField
                  margin="normal"
                  fullWidth
                  id="email"
                  label="Email Address"
                  name="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <TextField
                  margin="normal"
                  fullWidth
                  name="password"
                  label="Password"
                  type="password"
                  id="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <Button
                  type="submit"
                  fullWidth
                  variant="outlined"
                  sx={{ mt: 3, mb: 2 }}
                  disabled={loading}
                >
                  {loading ? 'Signing In...' : 'Sign In with email'}
                </Button>
              </form>
            </>
          )}
        </Paper>
        </Box>
      </Container>
    </Box>
  );
};

export default Login;
