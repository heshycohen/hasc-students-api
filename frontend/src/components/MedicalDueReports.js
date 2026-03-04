import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
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
  Typography,
  Checkbox,
  FormControlLabel,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import { Download } from '@mui/icons-material';
import AppHeader from './AppHeader';
import SessionSelector from './SessionSelector';
import { sessionAPI } from '../services/api';

const DAYS_OPTIONS = [7, 14, 30, 60];
const COLS = ['Last name', 'First name', 'DOB', 'District', 'Service type', 'Medical start', 'Medical end', 'Days until due', 'Home phone', 'Mother cell', 'Father cell', 'Email'];

const MedicalDueReports = () => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);
  const [serviceType, setServiceType] = useState('');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [tab, setTab] = useState(0);

  const loadSessions = async () => {
    try {
      const res = await sessionAPI.getSessions();
      const list = res.data.results || res.data || [];
      setSessions(list);
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

  useEffect(() => {
    let cancelled = false;
    if (!currentSession?.id) {
      setReport(null);
      return () => { cancelled = true; };
    }
    setLoading(true);
    const params = { session: currentSession.id, days };
    if (serviceType) params.service_type = serviceType;
    if (includeInactive) params.include_inactive = 'true';
    sessionAPI.getMedicalDueReport(params)
      .then((res) => {
        if (!cancelled) setReport(res.data);
      })
      .catch((e) => {
        if (!cancelled) setError(e.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentSession?.id, days, serviceType, includeInactive]);

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

  const handleExportCsv = async () => {
    const params = { session: currentSession?.id, days };
    if (serviceType) params.service_type = serviceType;
    if (includeInactive) params.include_inactive = 'true';
    try {
      const res = await sessionAPI.getMedicalDueReportCsv(params);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'medical_due_report.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const formatDate = (d) => (d ? d.split('T')[0] : '');
  const serviceLabel = (v) => (v === 'center_based' ? 'Center-based' : v === 'related_service' ? 'Related service' : v || '');

  const renderTable = (rows) => (
    <TableContainer component={Paper} sx={{ overflowX: 'auto' }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {COLS.map((c) => (
              <TableCell key={c}>{c}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {(rows || []).map((row, idx) => (
            <TableRow key={row.id ?? idx}>
              <TableCell>{row.last_name ?? ''}</TableCell>
              <TableCell>{row.first_name ?? ''}</TableCell>
              <TableCell>{formatDate(row.date_of_birth)}</TableCell>
              <TableCell>{row.district ?? ''}</TableCell>
              <TableCell>{serviceLabel(row.service_type)}</TableCell>
              <TableCell>{formatDate(row.medical_start_date)}</TableCell>
              <TableCell>{formatDate(row.medical_end_date)}</TableCell>
              <TableCell>{row.days_until_due != null ? row.days_until_due : ''}</TableCell>
              <TableCell>{row.home_phone ?? ''}</TableCell>
              <TableCell>{row.mother_cell ?? ''}</TableCell>
              <TableCell>{row.father_cell ?? ''}</TableCell>
              <TableCell>{row.email ?? ''}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box>
      <AppHeader backTo="/" rightContent={<Typography variant="subtitle1">Medical Due Reports</Typography>} />
      <Box sx={{ p: 2 }}>
        <SessionSelector
          sessions={sessions}
          currentSession={currentSession}
          onSessionChange={handleSessionChange}
        />
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mt: 2 }}>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Due within</InputLabel>
            <Select value={days} label="Due within" onChange={(e) => setDays(Number(e.target.value))}>
              {DAYS_OPTIONS.map((d) => (
                <MenuItem key={d} value={d}>{d} days</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Service type</InputLabel>
            <Select value={serviceType} label="Service type" onChange={(e) => setServiceType(e.target.value)}>
              <MenuItem value="">All</MenuItem>
              <MenuItem value="center_based">Center-based</MenuItem>
              <MenuItem value="related_service">Related service</MenuItem>
            </Select>
          </FormControl>
          <FormControlLabel
            control={<Checkbox checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />}
            label="Include inactive"
          />
          <Button startIcon={<Download />} variant="outlined" onClick={handleExportCsv} disabled={!currentSession || loading}>
            Export CSV
          </Button>
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>{error}</Alert>}
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}
        {!loading && report && (
          <>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mt: 2 }}>
              <Tab label={`Overdue (${report.overdue?.length ?? 0})`} />
              <Tab label={`Due soon (${report.due_soon?.length ?? 0})`} />
              <Tab label={`Missing dates (${report.missing?.length ?? 0})`} />
            </Tabs>
            {tab === 0 && renderTable(report.overdue)}
            {tab === 1 && renderTable(report.due_soon)}
            {tab === 2 && renderTable(report.missing)}
          </>
        )}
        {!loading && currentSession && !report && <Typography color="text.secondary" sx={{ mt: 2 }}>No report data.</Typography>}
      </Box>
    </Box>
  );
};

export default MedicalDueReports;
