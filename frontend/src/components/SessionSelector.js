import React, { useState, useEffect } from 'react';
import {
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { format } from 'date-fns';

const SessionSelector = ({ sessions, currentSession, onSessionChange }) => {
  const [timeoutWarning, setTimeoutWarning] = useState(false);

  useEffect(() => {
    // Check for session timeout warning (14 minutes = 840 seconds)
    const checkTimeout = () => {
      const lastActivity = localStorage.getItem('last_activity');
      if (lastActivity) {
        const elapsed = (Date.now() - parseInt(lastActivity)) / 1000;
        if (elapsed > 840) {
          setTimeoutWarning(true);
        }
      }
    };

    const interval = setInterval(checkTimeout, 60000); // Check every minute
    checkTimeout();

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Update last activity on user interaction
    const updateActivity = () => {
      localStorage.setItem('last_activity', Date.now().toString());
      setTimeoutWarning(false);
    };

    window.addEventListener('mousedown', updateActivity);
    window.addEventListener('keypress', updateActivity);

    return () => {
      window.removeEventListener('mousedown', updateActivity);
      window.removeEventListener('keypress', updateActivity);
    };
  }, []);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Current Session
      </Typography>

      {timeoutWarning && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Your session will expire soon. Please save your work.
        </Alert>
      )}

      <FormControl fullWidth size="small" sx={{ minWidth: 280 }}>
        <InputLabel id="session-select-label">Select Session</InputLabel>
        <Select
          labelId="session-select-label"
          value={currentSession?.id != null ? String(currentSession.id) : ''}
          label="Select Session"
          onChange={(e) => onSessionChange(e.target.value)}
          displayEmpty
          notched
        >
          <MenuItem value="">
            <em>Select a session</em>
          </MenuItem>
          {sessions.map((session) => (
            <MenuItem key={session.id} value={String(session.id)}>
              {session.name} ({session.session_type}) -{' '}
              {format(new Date(session.start_date), 'MMM yyyy')} to{' '}
              {format(new Date(session.end_date), 'MMM yyyy')}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {currentSession && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Students: {currentSession.student_count || 0} | Employees:{' '}
            {currentSession.employee_count || 0}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default SessionSelector;
