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
  CircularProgress,
  Alert,
  ToggleButtonGroup,
  ToggleButton,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TablePagination,
} from '@mui/material';
import { Download, Event, People } from '@mui/icons-material';
import AppHeader from './AppHeader';
import SessionSelector from './SessionSelector';
import { sessionAPI, studentAPI } from '../services/api';

const todayStr = () => new Date().toISOString().slice(0, 10);

const AttendancePage = () => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [students, setStudents] = useState([]);
  const [records, setRecords] = useState({});
  const [absenceReasons, setAbsenceReasons] = useState([]);
  const [date, setDate] = useState(todayStr());
  const [serviceType, setServiceType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [absentReport, setAbsentReport] = useState(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

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

  useEffect(() => {
    if (!currentSession?.id) return;
    sessionAPI.getAbsenceReasons().then((res) => setAbsenceReasons(res.data.results || res.data || [])).catch(() => {});
  }, [currentSession?.id]);

  useEffect(() => {
    let cancelled = false;
    if (!currentSession?.id) {
      setStudents([]);
      setRecords({});
      return () => { cancelled = true; };
    }
    setLoading(true);
    const params = { session: currentSession.id, page_size: 5000 };
    if (serviceType) params.service_type = serviceType;
    studentAPI.getStudents(currentSession.id, { ...params, active_only: 'true' })
      .then((res) => {
        if (cancelled) return;
        setStudents(res.data.results || res.data || []);
      })
      .catch((e) => {
        if (!cancelled) setError(e.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentSession?.id, serviceType]);

  useEffect(() => {
    if (!currentSession?.id || !date) {
      setRecords({});
      return;
    }
    sessionAPI.getAttendance({ session: currentSession.id, date })
      .then((res) => {
        const list = res.data.results || res.data || [];
        const byStudent = {};
        list.forEach((r) => { byStudent[r.student] = r; });
        setRecords(byStudent);
      })
      .catch(() => setRecords({}));
  }, [currentSession?.id, date]);

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

  const getRecord = (studentId) => records[studentId] || null;

  const setStatus = async (studentId, status, absenceReasonId = null) => {
    const rec = getRecord(studentId);
    const payload = {
      date,
      student: studentId,
      status,
      absence_reason: status === 'absent' ? (absenceReasonId || absenceReasons.find((r) => r.reason_code === 'UNKNOWN')?.reason_code) : null,
    };
    try {
      if (rec?.id) {
        await sessionAPI.updateAttendanceRecord(rec.id, { ...payload, student: studentId });
      } else {
        await sessionAPI.createAttendanceRecord(payload);
      }
      const res = await sessionAPI.getAttendance({ session: currentSession.id, date });
      const list = res.data.results || res.data || [];
      const byStudent = {};
      list.forEach((r) => { byStudent[r.student] = r; });
      setRecords(byStudent);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const setLateOrEarly = async (studentId, field, value) => {
    const rec = getRecord(studentId);
    const current = rec || { student: studentId, date, status: 'present' };
    const payload = {
      date,
      student: studentId,
      status: current.status,
      late_arrival_time: field === 'late' ? value : (current.late_arrival_time || null),
      early_dismissal_time: field === 'early' ? value : (current.early_dismissal_time || null),
      absence_reason: current.absence_reason || null,
    };
    try {
      if (rec?.id) {
        await sessionAPI.updateAttendanceRecord(rec.id, payload);
      } else {
        await sessionAPI.createAttendanceRecord(payload);
      }
      const res = await sessionAPI.getAttendance({ session: currentSession.id, date });
      const list = res.data.results || res.data || [];
      const byStudent = {};
      list.forEach((r) => { byStudent[r.student] = r; });
      setRecords(byStudent);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const markAllPresent = async () => {
    for (const s of students) {
      const rec = getRecord(s.id);
      if (!rec || rec.status === 'absent') {
        await setStatus(s.id, 'present');
      }
    }
  };

  const openDailyAbsentReport = async () => {
    try {
      const res = await sessionAPI.getAttendanceDailyAbsentReport({ date, session: currentSession?.id });
      setAbsentReport(res.data);
      setReportOpen(true);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const exportDailyAbsentCsv = async () => {
    try {
      const res = await sessionAPI.getAttendanceDailyAbsentReportCsv({ date, session: currentSession?.id });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `daily_absent_${date}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const paginatedStudents = students.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Box>
      <AppHeader backTo="/" rightContent={<Typography variant="subtitle1">Attendance</Typography>} />
      <Box sx={{ p: 2 }}>
        <SessionSelector sessions={sessions} currentSession={currentSession} onSessionChange={handleSessionChange} />
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mt: 2 }}>
          <TextField
            label="Date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            size="small"
            InputLabelProps={{ shrink: true }}
          />
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Service type</InputLabel>
            <Select value={serviceType} label="Service type" onChange={(e) => setServiceType(e.target.value)}>
              <MenuItem value="">All</MenuItem>
              <MenuItem value="center_based">Center-based</MenuItem>
              <MenuItem value="related_service">Related service</MenuItem>
            </Select>
          </FormControl>
          <Button variant="outlined" onClick={markAllPresent} disabled={!currentSession || loading}>
            Mark all present
          </Button>
          <Button variant="outlined" startIcon={<People />} onClick={openDailyAbsentReport} disabled={!currentSession}>
            Daily absent report
          </Button>
          {reportOpen && absentReport && (
            <Button variant="outlined" startIcon={<Download />} onClick={exportDailyAbsentCsv}>
              Export absent CSV
            </Button>
          )}
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>{error}</Alert>}
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}
        {!loading && (
          <>
            <TableContainer component={Paper} sx={{ mt: 2 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Name (Last, First)</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Late arrival</TableCell>
                    <TableCell>Early dismissal</TableCell>
                    <TableCell>Absence reason</TableCell>
                    <TableCell>Notes</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedStudents.map((s) => {
                    const rec = getRecord(s.id);
                    const status = rec?.status || 'present';
                    return (
                      <TableRow key={s.id}>
                        <TableCell>{s.last_name}, {s.first_name}</TableCell>
                        <TableCell>
                          <ToggleButtonGroup
                            size="small"
                            value={status}
                            exclusive
                            onChange={(_, v) => v != null && setStatus(s.id, v)}
                          >
                            <ToggleButton value="present">Present</ToggleButton>
                            <ToggleButton value="absent">Absent</ToggleButton>
                          </ToggleButtonGroup>
                        </TableCell>
                        <TableCell>
                          <TextField
                            type="time"
                            size="small"
                            sx={{ width: 100 }}
                            InputLabelProps={{ shrink: true }}
                            value={rec?.late_arrival_time ? rec.late_arrival_time.slice(0, 5) : ''}
                            onChange={(e) => setLateOrEarly(s.id, 'late', e.target.value || null)}
                            disabled={status === 'absent'}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            type="time"
                            size="small"
                            sx={{ width: 100 }}
                            InputLabelProps={{ shrink: true }}
                            value={rec?.early_dismissal_time ? rec.early_dismissal_time.slice(0, 5) : ''}
                            onChange={(e) => setLateOrEarly(s.id, 'early', e.target.value || null)}
                            disabled={status === 'absent'}
                          />
                        </TableCell>
                        <TableCell>
                          <Select
                            size="small"
                            sx={{ minWidth: 140 }}
                            value={rec?.absence_reason ?? ''}
                            displayEmpty
                            disabled={status === 'present'}
                            onChange={(e) => setStatus(s.id, 'absent', e.target.value)}
                          >
                            <MenuItem value="">—</MenuItem>
                            {absenceReasons.map((r) => (
                              <MenuItem key={r.reason_code} value={r.reason_code}>{r.reason_label}</MenuItem>
                            ))}
                          </Select>
                        </TableCell>
                        <TableCell>
                          <TextField size="small" placeholder="Notes" sx={{ width: 120 }} defaultValue={rec?.notes} onBlur={(e) => {
                            const v = e.target.value?.trim();
                            if (rec?.id && v !== (rec.notes || '')) {
                              sessionAPI.updateAttendanceRecord(rec.id, { ...rec, notes: v || null }).then(() => {
                                setRecords((prev) => ({ ...prev, [s.id]: { ...rec, notes: v || null } }));
                              });
                            }
                          }} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={students.length}
              page={page}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
              rowsPerPageOptions={[25, 50, 100]}
            />
          </>
        )}
        {!loading && students.length === 0 && currentSession && (
          <Typography color="text.secondary" sx={{ mt: 2 }}>No active students.</Typography>
        )}
      </Box>

      <Dialog open={reportOpen} onClose={() => setReportOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Daily absent report — {date}</DialogTitle>
        <DialogContent>
          {absentReport && (
            <Box>
              <Typography variant="subtitle2" sx={{ mt: 1 }}>Absent ({absentReport.absent?.length ?? 0})</Typography>
              <TableContainer><Table size="small">
                <TableHead><TableRow><TableCell>Student</TableCell><TableCell>District</TableCell><TableCell>Service type</TableCell><TableCell>Absence reason</TableCell><TableCell>Contact</TableCell></TableRow></TableHead>
                <TableBody>
                  {(absentReport.absent || []).map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.student_name}</TableCell>
                      <TableCell>{row.district}</TableCell>
                      <TableCell>{row.service_type}</TableCell>
                      <TableCell>{row.absence_reason}</TableCell>
                      <TableCell>{row.mother_cell || row.father_cell || row.home_phone || row.email || '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table></TableContainer>
              <Typography variant="subtitle2" sx={{ mt: 2 }}>Missing attendance entry ({absentReport.missing_attendance_entry?.length ?? 0})</Typography>
              <TableContainer><Table size="small">
                <TableHead><TableRow><TableCell>Student</TableCell><TableCell>District</TableCell><TableCell>Service type</TableCell><TableCell>Contact</TableCell></TableRow></TableHead>
                <TableBody>
                  {(absentReport.missing_attendance_entry || []).map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.student_name}</TableCell>
                      <TableCell>{row.district}</TableCell>
                      <TableCell>{row.service_type}</TableCell>
                      <TableCell>{row.mother_cell || row.father_cell || row.home_phone || row.email || '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table></TableContainer>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportOpen(false)}>Close</Button>
          {absentReport && <Button onClick={exportDailyAbsentCsv}>Export CSV</Button>}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AttendancePage;
