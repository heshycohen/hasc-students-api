import React, { useState, useEffect } from 'react';
import { Container, Grid, Paper, Typography, Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { sessionAPI } from '../services/api';
import SessionSelector from './SessionSelector';
import AppHeader from './AppHeader';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const sessRes = await sessionAPI.getSessions();
        const list = sessRes.data.results || sessRes.data || [];
        if (cancelled) return;
        setSessions(list);

        let current = null;
        try {
          const curRes = await sessionAPI.getCurrentSession();
          current = curRes.data;
        } catch (_) {
          // No active session (404) or error
        }
        if (cancelled) return;
        setCurrentSession(current);

        // If we have sessions but no current session, set the first one as active so it shows automatically
        if (list.length > 0 && !current?.id) {
          try {
            await sessionAPI.setActiveSession(list[0].id);
            const curRes = await sessionAPI.getCurrentSession();
            if (!cancelled) setCurrentSession(curRes.data);
          } catch (err) {
            console.error('Error auto-setting session:', err);
          }
        }
      } catch (error) {
        console.error('Error loading sessions:', error);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const loadCurrentSession = async () => {
    try {
      const response = await sessionAPI.getCurrentSession();
      setCurrentSession(response.data);
    } catch (error) {
      setCurrentSession(null);
    }
  };

  const handleSessionChange = async (sessionId) => {
    if (sessionId === '') return;
    try {
      await sessionAPI.setActiveSession(sessionId);
      await loadCurrentSession();
    } catch (error) {
      console.error('Error setting active session:', error);
    }
  };

  return (
    <Box>
      <AppHeader
        rightContent={
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', width: '100%' }}>
            <Typography variant="body2" sx={{ mr: 2 }}>
              {user?.email} ({user?.role})
            </Typography>
            <Button color="inherit" onClick={logout} sx={{ color: '#fff' }}>
              Logout
            </Button>
          </Box>
        }
      />

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <SessionSelector
              sessions={sessions}
              currentSession={currentSession}
              onSessionChange={handleSessionChange}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/students')}>
              <Typography variant="h5" gutterBottom>
                Students
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Manage student records and enrollment
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/students/roster-list')}>
              <Typography variant="h5" gutterBottom>
                Student Roster
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Full alphabetical roster (Center-based / Related service), export CSV
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/reports/medical-due')}>
              <Typography variant="h5" gutterBottom>
                Medical Due Reports
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Overdue, due soon, missing medical dates; export CSV
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/incidents')}>
              <Typography variant="h5" gutterBottom>
                Incident Log
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Log and filter incidents; export CSV
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/attendance')}>
              <Typography variant="h5" gutterBottom>
                Attendance
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Daily attendance, late/early, absence reasons, daily absent report
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/employees')}>
              <Typography variant="h5" gutterBottom>
                Employees
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Manage employee records and assignments
              </Typography>
            </Paper>
          </Grid>

          {user?.role === 'admin' && (
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, cursor: 'pointer' }} onClick={() => navigate('/compliance')}>
                <Typography variant="h5" gutterBottom>
                  Compliance Reports
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  View access logs and disclosure reports
                </Typography>
              </Paper>
            </Grid>
          )}
        </Grid>
      </Container>
    </Box>
  );
};

export default Dashboard;
