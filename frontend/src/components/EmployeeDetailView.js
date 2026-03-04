import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Grid,
} from '@mui/material';
import { ArrowBack, Edit } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { employeeAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Field = ({ label, value }) => (
  <Box sx={{ mb: 1.5 }}>
    <Typography variant="caption" color="text.secondary" display="block">
      {label}
    </Typography>
    <Typography variant="body1">{value ?? '—'}</Typography>
  </Box>
);

const EmployeeDetailView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    employeeAPI
      .getEmployee(id)
      .then((res) => {
        if (!cancelled) setEmployee(res.data);
      })
      .catch(() => {
        if (!cancelled) setEmployee(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  const canEdit = user?.role === 'admin' || user?.role === 'editor';

  if (loading) {
    return (
      <Box>
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Typography>Loading…</Typography>
        </Container>
      </Box>
    );
  }

  if (!employee) {
    return (
      <Box>
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Typography color="error">Employee not found.</Typography>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/employees')} sx={{ mt: 2 }}>
            Back to list
          </Button>
        </Container>
      </Box>
    );
  }

  return (
    <Box>
      <Paper elevation={0} sx={{ px: 2, py: 1.5, mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/employees')}>
          Back to list
        </Button>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Edit />}
            onClick={() => navigate(`/employees/${id}/edit`)}
          >
            Edit
          </Button>
        )}
      </Paper>

      <Container maxWidth="md" sx={{ pb: 4 }}>
        <Typography variant="h5" gutterBottom>
          {employee.first_name} {employee.last_name}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Session: {employee.session_name}
        </Typography>

        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Contact &amp; role
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <Field label="Email" value={employee.email} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Home phone" value={employee.phone} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Mobile phone" value={employee.mobile_phone} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Position" value={employee.position} />
            </Grid>
          </Grid>
        </Paper>

        {(employee.notes != null && employee.notes !== '') && (
          <Paper sx={{ p: 3, mt: 2 }}>
            <Typography variant="h6" color="primary" gutterBottom>
              Notes
            </Typography>
            <Field label="Notes" value={employee.notes} />
          </Paper>
        )}

        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Record info
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <Field label="Created" value={employee.created_at} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Last updated" value={employee.updated_at} />
            </Grid>
            {employee.locked_by_email && (
              <Grid item xs={12} sm={6}>
                <Field label="Currently edited by" value={employee.locked_by_email} />
              </Grid>
            )}
          </Grid>
        </Paper>
      </Container>
    </Box>
  );
};

export default EmployeeDetailView;
