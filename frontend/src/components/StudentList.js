import React, { useState, useEffect, useMemo } from 'react';
import {
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Autocomplete,
} from '@mui/material';
import { Add, FilterList, Clear, Search, Description } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { studentAPI, sessionAPI } from '../services/api';
import { passesMedicalDueFilter, MEDICAL_DUE_OPTIONS } from '../utils/medicalDueFilter';
import AppHeader from './AppHeader';

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'graduated', label: 'Graduated' },
  { value: 'transferred', label: 'Transferred' },
];

const StudentList = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [filterLastName, setFilterLastName] = useState('');
  const [filterFirstName, setFilterFirstName] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterClass, setFilterClass] = useState('');
  const [filterFunding, setFilterFunding] = useState('');
  const [filterSchoolDistrict, setFilterSchoolDistrict] = useState('');
  const [filterMedicalDue, setFilterMedicalDue] = useState('');
  const [classrooms, setClassrooms] = useState([]);
  const [fundingCodes, setFundingCodes] = useState([]);
  const [schoolDistricts, setSchoolDistricts] = useState([]);

  useEffect(() => {
    loadSession();
  }, []);

  useEffect(() => {
    if (!currentSession?.id) return;
    const load = async () => {
      try {
        const [classRes, fundingRes, districtRes] = await Promise.all([
          sessionAPI.getClassrooms(currentSession.id),
          sessionAPI.getFundingCodes(currentSession.id),
          sessionAPI.getSchoolDistricts(currentSession.id),
        ]);
        setClassrooms(classRes.data.results || classRes.data || []);
        setFundingCodes(fundingRes.data.results || fundingRes.data || []);
        setSchoolDistricts(districtRes.data.results || districtRes.data || []);
      } catch (e) {
        console.error('Error loading classrooms/funding codes/school districts:', e);
      }
    };
    load();
  }, [currentSession?.id]);

  const loadSession = async () => {
    try {
      let session = null;
      try {
        const sessionResponse = await sessionAPI.getCurrentSession();
        session = sessionResponse.data;
      } catch (_) {
        const sessRes = await sessionAPI.getSessions();
        const list = sessRes.data.results || sessRes.data || [];
        if (list.length > 0) {
          await sessionAPI.setActiveSession(list[0].id);
          const curRes = await sessionAPI.getCurrentSession();
          session = curRes.data;
        }
      }
      setCurrentSession(session);
    } catch (error) {
      console.error('Error loading session:', error);
    } finally {
      setSessionLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!currentSession?.id) return;
    setSearchLoading(true);
    try {
      const studentsResponse = await studentAPI.getStudents(currentSession.id);
      const list = studentsResponse.data.results || studentsResponse.data || [];
      setStudents(list);
      setHasSearched(true);
    } catch (error) {
      console.error('Error searching students:', error);
      setStudents([]);
      setHasSearched(true);
    } finally {
      setSearchLoading(false);
    }
  };

  const canEdit = user?.role === 'admin' || user?.role === 'editor';

  const normalizeDistrict = (str) =>
    (str || '').trim().replace(/\s+/g, ' ').toLowerCase();

  const districtMatches = (studentDistrict, selectedDistrict) => {
    const s = normalizeDistrict(studentDistrict);
    const d = normalizeDistrict(selectedDistrict);
    if (!d) return true;
    if (!s) return false;
    return s === d || s.startsWith(d) || d.startsWith(s);
  };

  const filteredStudents = useMemo(() => {
    if (!students.length) return [];
    const last = (filterLastName || '').trim().toLowerCase();
    const first = (filterFirstName || '').trim().toLowerCase();
    const status = (filterStatus || '').trim();
    const cls = (filterClass || '').trim();
    const funding = (filterFunding || '').trim();
    const district = (filterSchoolDistrict || '').trim();
    return students.filter((s) => {
      if (last && !(s.last_name || '').toLowerCase().startsWith(last)) return false;
      if (first && !(s.first_name || '').toLowerCase().startsWith(first)) return false;
      if (status && s.status !== status) return false;
      if (cls === '__related_service__') {
        if ((s.class_num || '').trim()) return false;
      } else if (cls && (s.class_num || '').trim() !== cls) return false;
      if (funding && (s.funding_code || '').trim() !== funding) return false;
      if (district && !districtMatches(s.school_district, district)) return false;
      if (filterMedicalDue && !passesMedicalDueFilter(s, filterMedicalDue)) return false;
      return true;
    });
  }, [students, filterLastName, filterFirstName, filterStatus, filterClass, filterFunding, filterSchoolDistrict, filterMedicalDue]);

  const clearFilters = () => {
    setFilterLastName('');
    setFilterFirstName('');
    setFilterStatus('');
    setFilterClass('');
    setFilterFunding('');
    setFilterSchoolDistrict('');
    setFilterMedicalDue('');
  };

  const hasActiveFilters = filterLastName || filterFirstName || filterStatus || filterClass || filterFunding || filterSchoolDistrict || filterMedicalDue;

  const lastNames = useMemo(() => {
    const set = new Set();
    students.forEach((s) => {
      const n = (s.last_name || '').trim();
      if (n) set.add(n);
    });
    return [...set].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  }, [students]);

  const firstNames = useMemo(() => {
    const set = new Set();
    students.forEach((s) => {
      const n = (s.first_name || '').trim();
      if (n) set.add(n);
    });
    return [...set].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  }, [students]);

  // Prefix filter: same for last name and first name — type "H" → names starting with H, "He" → starting with He
  const filterOptionsByPrefix = (options, state) => {
    const input = (state.inputValue || '').trim().toLowerCase();
    if (!input) return options;
    return options.filter((opt) => String(opt || '').toLowerCase().startsWith(input));
  };

  return (
    <Box>
      <AppHeader
        backTo="/"
        rightContent={
          <>
            <Typography variant="subtitle1" component="span" sx={{ flexGrow: 1, textAlign: 'left' }}>
              Students - {currentSession?.name || 'Loading...'}
            </Typography>
            {canEdit && (
              <Button color="inherit" startIcon={<Add />} onClick={() => navigate('/students/new')}>
                Add Student
              </Button>
            )}
          </>
        }
      />

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        {sessionLoading ? (
          <Typography sx={{ py: 3 }}>Loading…</Typography>
        ) : (
        <>
        <Paper sx={{ p: 2, mb: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <FilterList sx={{ color: 'text.secondary', mr: 1 }} />
          <Autocomplete
            size="small"
            sx={{ minWidth: 180 }}
            options={lastNames}
            value={filterLastName || null}
            onChange={(_, v) => setFilterLastName(v || '')}
            inputValue={filterLastName}
            onInputChange={(_, v) => setFilterLastName(v || '')}
            filterOptions={filterOptionsByPrefix}
            getOptionLabel={(o) => (o ?? '')}
            renderInput={(params) => <TextField {...params} label="Last name" placeholder="e.g. H then He to narrow" />}
            freeSolo
            handleHomeEndKeys
          />
          <Autocomplete
            size="small"
            sx={{ minWidth: 180 }}
            options={firstNames}
            value={filterFirstName || null}
            onChange={(_, v) => setFilterFirstName(v || '')}
            inputValue={filterFirstName}
            onInputChange={(_, v) => setFilterFirstName(v || '')}
            filterOptions={filterOptionsByPrefix}
            getOptionLabel={(o) => (o ?? '')}
            renderInput={(params) => <TextField {...params} label="First name" placeholder="e.g. H then He to narrow" />}
            freeSolo
            handleHomeEndKeys
          />
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Status</InputLabel>
            <Select
              label="Status"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <MenuItem key={opt.value || 'all'} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Class</InputLabel>
            <Select
              label="Class"
              value={filterClass}
              onChange={(e) => setFilterClass(e.target.value)}
            >
              <MenuItem value="">All classes</MenuItem>
              <MenuItem value="__related_service__">Related service only</MenuItem>
              {classrooms.map((c) => (
                <MenuItem key={c.id} value={c.class_num}>
                  {c.label || `${c.class_num} / ${c.class_size || '—'}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Funding code</InputLabel>
            <Select
              label="Funding code"
              value={filterFunding}
              onChange={(e) => setFilterFunding(e.target.value)}
            >
              <MenuItem value="">All funding codes</MenuItem>
              {fundingCodes.map((fc) => (
                <MenuItem key={fc.id} value={fc.code}>{fc.code}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>School district</InputLabel>
            <Select
              label="School district"
              value={filterSchoolDistrict}
              onChange={(e) => setFilterSchoolDistrict(e.target.value)}
            >
              <MenuItem value="">All school districts</MenuItem>
              {schoolDistricts.map((sd) => (
                <MenuItem key={sd.id} value={sd.name}>{sd.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Medical due</InputLabel>
            <Select
              label="Medical due"
              value={filterMedicalDue}
              onChange={(e) => setFilterMedicalDue(e.target.value)}
            >
              {MEDICAL_DUE_OPTIONS.map((opt) => (
                <MenuItem key={opt.value || 'all'} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            startIcon={<Search />}
            onClick={handleSearch}
            disabled={searchLoading}
          >
            {searchLoading ? 'Searching…' : 'Search'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Description />}
            onClick={() => window.open(`/students/roster${currentSession?.id ? `?session=${currentSession.id}` : ''}`, '_blank', 'noopener,noreferrer')}
            disabled={!currentSession?.id}
          >
            Student roster
          </Button>
          {hasActiveFilters && (
            <Button size="small" startIcon={<Clear />} onClick={clearFilters}>
              Clear filters
            </Button>
          )}
          {hasSearched && (
            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              Showing {filteredStudents.length} of {students.length} matches
            </Typography>
          )}
        </Paper>

        {hasSearched && (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Class</TableCell>
                  <TableCell>Funding</TableCell>
                  <TableCell>School district</TableCell>
                  <TableCell>Medical due</TableCell>
                  <TableCell>Date of Birth</TableCell>
                  <TableCell>Enrollment Date</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Parent Email</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredStudents.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                      {students.length === 0
                        ? `No students in ${currentSession?.name || 'this session'}.`
                        : 'No students match the current filters.'}
                    </TableCell>
                  </TableRow>
                ) : filteredStudents.map((student) => (
                  <TableRow
                    key={student.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/students/${student.id}`)}
                  >
                    <TableCell>
                      {student.first_name} {student.last_name}
                    </TableCell>
                    <TableCell>{student.class_num ? student.class_num : 'Related service'}</TableCell>
                    <TableCell>{student.funding_code || '-'}</TableCell>
                    <TableCell>{student.school_district || '-'}</TableCell>
                    <TableCell>{student.medical_due_date || '-'}</TableCell>
                    <TableCell>{student.date_of_birth}</TableCell>
                    <TableCell>{student.enrollment_date}</TableCell>
                    <TableCell>{student.status}</TableCell>
                    <TableCell>{student.parent_email || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {!hasSearched && (
          <Typography color="text.secondary" sx={{ py: 3 }}>
            Enter filters if desired, then click <strong>Search</strong> to see children. Click a child to view full details.
          </Typography>
        )}
        </>
        )}
      </Container>
    </Box>
  );
};

export default StudentList;
