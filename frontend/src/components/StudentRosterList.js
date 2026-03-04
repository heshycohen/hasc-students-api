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
} from '@mui/material';
import { Download } from '@mui/icons-material';
import AppHeader from './AppHeader';
import SessionSelector from './SessionSelector';
import { sessionAPI, studentAPI } from '../services/api';

const ROSTER_COLUMNS = [
  { id: 'last_name', label: 'Last name' },
  { id: 'first_name', label: 'First name' },
  { id: 'date_of_birth', label: 'DOB' },
  { id: 'address', label: 'Address' },
  { id: 'home_phone', label: 'Home phone' },
  { id: 'mother_cell', label: 'Mother cell' },
  { id: 'father_cell', label: 'Father cell' },
  { id: 'email', label: 'Email' },
  { id: 'discharge_date', label: 'Discharge' },
  { id: 'district_display', label: 'District' },
  { id: 'vaccines_status', label: 'Vaccines' },
  { id: 'medical_start_date', label: 'Medical start date' },
  { id: 'medical_end_date', label: 'Medical end date' },
  { id: 'sped_indiv_code', label: 'SPED INDIV Code' },
  { id: 'service_type', label: 'Service type' },
];

const COLUMN_STYLES = {
  home_phone:   { minWidth: 140, maxWidth: 180, whiteSpace: 'nowrap' },
  mother_cell:  { minWidth: 140, maxWidth: 180, whiteSpace: 'nowrap' },
  father_cell:  { minWidth: 140, maxWidth: 180, whiteSpace: 'nowrap' },
  email:        { minWidth: 180, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  parent_email: { minWidth: 180, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
};

const formatDate = (d) => {
  if (!d) return '';
  const s = typeof d === 'string' ? d.split('T')[0] : '';
  const [y, m, day] = s.split('-');
  return y && m && day ? `${Number(m)}/${Number(day)}/${y}` : '';
};

const StudentRosterList = () => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [serviceType, setServiceType] = useState('');
  const [discharge, setDischarge] = useState('all');
  const [spedIndiv, setSpedIndiv] = useState('');
  const [district, setDistrict] = useState('');
  const [debugInfo, setDebugInfo] = useState(null);

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
      setStudents([]);
      setLoading(false);
      setDebugInfo(null);
      return () => { cancelled = true; };
    }
    setLoading(true);
    const params = { session: currentSession.id, page_size: 5000 };
    // Unified filters: discharge, SPED INDIV code, service_type, district
    params.discharge = discharge || 'all';
    if (spedIndiv) params.sped_indiv_code = spedIndiv;
    if (serviceType && serviceType !== 'all') params.service_type = serviceType;
    if (district) params.district = district;
    studentAPI.getStudents(currentSession.id, params)
      .then((res) => {
        if (cancelled) return;
        const list = res.data.results || res.data || [];
        setStudents(list);
        if (process.env.NODE_ENV === 'development') {
          setDebugInfo({
            filterState: {
              serviceType: serviceType || '(all)',
              discharge: discharge || 'all',
              spedIndiv: spedIndiv || '(all)',
              district: district || '(all)',
            },
            paramsSent: { ...params },
            countReturned: list.length,
            countDisplayed: list.length,
            totalCount: res.data.count ?? list.length,
          });
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.response?.data?.detail || e.message);
        if (process.env.NODE_ENV === 'development') setDebugInfo({ error: e.message });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentSession?.id, serviceType, discharge, spedIndiv, district]);

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
    const params = {};
    params.discharge = discharge || 'all';
    if (spedIndiv) params.sped_indiv_code = spedIndiv;
    if (serviceType && serviceType !== 'all') params.service_type = serviceType;
    if (district) params.district = district;
    try {
      await studentAPI.downloadRosterCsv(currentSession?.id, params);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const serviceTypeLabel = (v) => {
    if (v === 'center_based') return 'Center-based';
    if (v === 'related_service') return 'Related service';
    if (v === 'seit') return 'SEIT';
    return (v && v !== 'unknown') ? v : 'Unknown';
  };

  return (
    <Box>
      <AppHeader backTo="/" rightContent={<Typography variant="subtitle1">Student Roster</Typography>} />
      <Box sx={{ p: 2 }}>
        <SessionSelector
          sessions={sessions}
          currentSession={currentSession}
          onSessionChange={handleSessionChange}
        />
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mt: 2 }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Service type</InputLabel>
            <Select
              value={serviceType}
              label="Service type"
              onChange={(e) => setServiceType(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="center_based">Center-based</MenuItem>
              <MenuItem value="related_service">Related service</MenuItem>
              <MenuItem value="seit">SEIT</MenuItem>
              <MenuItem value="unknown">Unknown</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Discharge</InputLabel>
            <Select
              value={discharge}
              label="Discharge"
              onChange={(e) => setDischarge(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="active">Active only</MenuItem>
              <MenuItem value="discharged">Discharged only</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>SPEDINDIV</InputLabel>
            <Select
              value={spedIndiv}
              label="SPEDINDIV"
              onChange={(e) => setSpedIndiv(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              {[...new Set(students.map((s) => (s.sped_indiv_code || '').trim()).filter(Boolean))].sort().map((code) => (
                <MenuItem key={code} value={code}>{code}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>District</InputLabel>
            <Select
              value={district}
              label="District"
              onChange={(e) => setDistrict(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              {[...new Set(students.map((s) => s.district_display || s.district || s.school_district).filter(Boolean))].sort().map((d) => (
                <MenuItem key={d} value={d}>{d}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button startIcon={<Download />} variant="outlined" onClick={handleExportCsv} disabled={!currentSession || loading}>
            Export CSV
          </Button>
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>{error}</Alert>}
        {process.env.NODE_ENV === 'development' && debugInfo && !debugInfo.error && (
          <Paper variant="outlined" sx={{ p: 1.5, mt: 2, bgcolor: 'grey.50' }}>
            <Typography variant="caption" fontWeight="bold">Roster debug</Typography>
            <Typography variant="caption" component="pre" sx={{ display: 'block', fontSize: 11 }}>
              {JSON.stringify(debugInfo, null, 2)}
            </Typography>
          </Paper>
        )}
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}
        {!loading && students.length > 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Service type breakdown: Center-based: {students.filter((s) => (s.service_type || '').toLowerCase() === 'center_based').length}
            {' | '}Related services: {students.filter((s) => (s.service_type || '').toLowerCase() === 'related_service').length}
            {' | '}SEIT: {students.filter((s) => (s.service_type || '').toLowerCase() === 'seit').length}
            {' | '}Unknown: {students.filter((s) => !s.service_type || !['center_based', 'related_service', 'seit'].includes((s.service_type || '').toLowerCase())).length}
          </Typography>
        )}
        {!loading && (
          <TableContainer component={Paper} sx={{ mt: 2, overflowX: 'auto' }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {ROSTER_COLUMNS.map((col) => (
                    <TableCell key={col.id}>{col.label}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {students.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.last_name ?? ''}</TableCell>
                    <TableCell>{row.first_name ?? ''}</TableCell>
                    <TableCell>{formatDate(row.date_of_birth)}</TableCell>
                    <TableCell>{row.address ?? ''}</TableCell>
                    <TableCell style={COLUMN_STYLES.home_phone}>{row.home_phone ?? row.parent_phone ?? ''}</TableCell>
                    <TableCell style={COLUMN_STYLES.mother_cell}>{row.mother_cell ?? ''}</TableCell>
                    <TableCell style={COLUMN_STYLES.father_cell}>{row.father_cell ?? ''}</TableCell>
                    <TableCell style={COLUMN_STYLES.email}>{row.email ?? row.parent_email ?? ''}</TableCell>
                    <TableCell>
                      {row.is_active === false ? 'Yes' : 'No'}
                      {row.discharge_date && ` (${formatDate(row.discharge_date)})`}
                      {row.discharge_notes && !row.discharge_date ? ` ${row.discharge_notes}` : ''}
                    </TableCell>
                    <TableCell>{row.district_display ?? row.district ?? row.school_district ?? ''}</TableCell>
                    <TableCell>{row.vaccines_display ?? ''}</TableCell>
                    <TableCell>{formatDate(row.medical_start_date)}</TableCell>
                    <TableCell>{formatDate(row.medical_end_date)}</TableCell>
                    <TableCell>{row.sped_indiv_code ?? ''}</TableCell>
                    <TableCell>{serviceTypeLabel(row.service_type)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {!loading && students.length === 0 && currentSession && (
          <Typography color="text.secondary" sx={{ mt: 2 }}>No students match the filters.</Typography>
        )}
      </Box>
    </Box>
  );
};

export default StudentRosterList;
