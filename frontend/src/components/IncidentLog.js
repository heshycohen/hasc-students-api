import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Typography,
  CircularProgress,
  Alert,
  IconButton,
} from '@mui/material';
import { Add, Download, Edit, Delete } from '@mui/icons-material';
import AppHeader from './AppHeader';
import SessionSelector from './SessionSelector';
import { sessionAPI } from '../services/api';

const formatDate = (d) => (d ? d.split('T')[0] : '');
const formatDateTime = (d) => (d ? new Date(d).toLocaleString() : '');

const IncidentLog = () => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    incident_date: '',
    incident_time: '',
    student: null,
    student_name_freeform: '',
    location: '',
    incident_type: '',
    description: '',
    reported_by: '',
    actions_taken: '',
    parent_notified: false,
    follow_up_required: false,
    status: 'open',
  });

  const loadSessions = async () => {
    try {
      const res = await sessionAPI.getSessions();
      setSessions(res.data.results || res.data || []);
      let cur = null;
      try {
        const curRes = await sessionAPI.getCurrentSession();
        cur = curRes.data;
      } catch (_) {}
      setCurrentSession(cur);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const loadIncidents = () => {
    if (!currentSession?.id) {
      setIncidents([]);
      return;
    }
    setLoading(true);
    sessionAPI.getIncidents({ session: currentSession.id })
      .then((res) => setIncidents(res.data.results || res.data || []))
      .catch((e) => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadIncidents();
  }, [currentSession?.id]);

  const handleSessionChange = async (sessionId) => {
    if (!sessionId) return;
    try {
      await sessionAPI.setActiveSession(sessionId);
      const res = await sessionAPI.getCurrentSession();
      setCurrentSession(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleOpen = (incident = null) => {
    if (incident) {
      setEditing(incident);
      setForm({
        incident_date: formatDate(incident.incident_date),
        incident_time: incident.incident_time ? incident.incident_time.slice(0, 5) : '',
        student: incident.student,
        student_name_freeform: incident.student_name_freeform || '',
        location: incident.location || '',
        incident_type: incident.incident_type || '',
        description: incident.description || '',
        reported_by: incident.reported_by || '',
        actions_taken: incident.actions_taken || '',
        parent_notified: incident.parent_notified || false,
        follow_up_required: incident.follow_up_required || false,
        status: incident.status || 'open',
      });
    } else {
      setEditing(null);
      setForm({
        incident_date: new Date().toISOString().slice(0, 10),
        incident_time: '',
        student: null,
        student_name_freeform: '',
        location: '',
        incident_type: '',
        description: '',
        reported_by: '',
        actions_taken: '',
        parent_notified: false,
        follow_up_required: false,
        status: 'open',
      });
    }
    setOpen(true);
  };

  const handleSave = async () => {
    const payload = {
      session: currentSession?.id,
      incident_date: form.incident_date,
      incident_time: form.incident_time || null,
      student: form.student || null,
      student_name_freeform: form.student_name_freeform || null,
      location: form.location || null,
      incident_type: form.incident_type || null,
      description: form.description,
      reported_by: form.reported_by || null,
      actions_taken: form.actions_taken || null,
      parent_notified: form.parent_notified,
      follow_up_required: form.follow_up_required,
      status: form.status,
    };
    try {
      if (editing) {
        await sessionAPI.updateIncident(editing.id, payload);
      } else {
        await sessionAPI.createIncident(payload);
      }
      setOpen(false);
      loadIncidents();
    } catch (e) {
      setError(e.response?.data?.detail || JSON.stringify(e.response?.data) || e.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this incident?')) return;
    try {
      await sessionAPI.deleteIncident(id);
      loadIncidents();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const handleExportCsv = () => {
    const headers = ['Date', 'Time', 'Student', 'Location', 'Type', 'Description', 'Reported by', 'Status'];
    const rows = incidents.map((i) => [
      formatDate(i.incident_date),
      i.incident_time || '',
      i.student_name || i.student_name_freeform || '',
      i.location || '',
      i.incident_type || '',
      (i.description || '').replace(/\r?\n/g, ' '),
      i.reported_by || '',
      i.status || '',
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'incident_log.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      <AppHeader backTo="/" rightContent={<Typography variant="subtitle1">Incident Log</Typography>} />
      <Box sx={{ p: 2 }}>
        <SessionSelector sessions={sessions} currentSession={currentSession} onSessionChange={handleSessionChange} />
        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <Button startIcon={<Add />} variant="contained" onClick={() => handleOpen()} disabled={!currentSession}>
            Add incident
          </Button>
          <Button startIcon={<Download />} variant="outlined" onClick={handleExportCsv} disabled={!incidents.length}>
            Export CSV
          </Button>
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>{error}</Alert>}
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}
        {!loading && (
          <TableContainer component={Paper} sx={{ mt: 2, overflowX: 'auto' }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Time</TableCell>
                  <TableCell>Student</TableCell>
                  <TableCell>Location</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Reported by</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {incidents.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{formatDate(row.incident_date)}</TableCell>
                    <TableCell>{row.incident_time ? row.incident_time.slice(0, 5) : ''}</TableCell>
                    <TableCell>{row.student_name || row.student_name_freeform || '—'}</TableCell>
                    <TableCell>{row.location || '—'}</TableCell>
                    <TableCell>{row.incident_type || '—'}</TableCell>
                    <TableCell sx={{ maxWidth: 200 }}>{(row.description || '').slice(0, 80)}{(row.description || '').length > 80 ? '…' : ''}</TableCell>
                    <TableCell>{row.reported_by || '—'}</TableCell>
                    <TableCell>{row.status || '—'}</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleOpen(row)}><Edit /></IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDelete(row.id)}><Delete /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {!loading && incidents.length === 0 && currentSession && (
          <Typography color="text.secondary" sx={{ mt: 2 }}>No incidents.</Typography>
        )}
      </Box>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? 'Edit incident' : 'Add incident'}</DialogTitle>
        <DialogContent>
          <TextField margin="dense" fullWidth label="Date" type="date" value={form.incident_date} onChange={(e) => setForm({ ...form, incident_date: e.target.value })} InputLabelProps={{ shrink: true }} />
          <TextField margin="dense" fullWidth label="Time" type="time" value={form.incident_time} onChange={(e) => setForm({ ...form, incident_time: e.target.value })} InputLabelProps={{ shrink: true }} />
          <TextField margin="dense" fullWidth label="Student (freeform if no match)" value={form.student_name_freeform} onChange={(e) => setForm({ ...form, student_name_freeform: e.target.value })} />
          <TextField margin="dense" fullWidth label="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <TextField margin="dense" fullWidth label="Type" value={form.incident_type} onChange={(e) => setForm({ ...form, incident_type: e.target.value })} />
          <TextField margin="dense" fullWidth label="Description" required multiline rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <TextField margin="dense" fullWidth label="Reported by" value={form.reported_by} onChange={(e) => setForm({ ...form, reported_by: e.target.value })} />
          <TextField margin="dense" fullWidth label="Actions taken" multiline value={form.actions_taken} onChange={(e) => setForm({ ...form, actions_taken: e.target.value })} />
          <FormControl fullWidth margin="dense">
            <InputLabel>Status</InputLabel>
            <Select value={form.status} label="Status" onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <MenuItem value="open">Open</MenuItem>
              <MenuItem value="closed">Closed</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={!form.description?.trim()}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default IncidentLog;
