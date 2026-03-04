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
  IconButton,
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Autocomplete,
} from '@mui/material';
import { Add, Edit, Delete, FilterList, Clear } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { employeeAPI, sessionAPI } from '../services/api';
import { passesMedicalDueFilter, MEDICAL_DUE_OPTIONS } from '../utils/medicalDueFilter';
import AppHeader from './AppHeader';

const EmployeeList = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [employees, setEmployees] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterLastName, setFilterLastName] = useState('');
  const [filterFirstName, setFilterFirstName] = useState('');
  const [filterPosition, setFilterPosition] = useState('');
  const [filterMedicalDue, setFilterMedicalDue] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
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
      const employeesResponse = await employeeAPI.getEmployees(session?.id);
      setEmployees(employeesResponse.data.results || employeesResponse.data || []);
    } catch (error) {
      console.error('Error loading data:', error);
      setEmployees([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this employee?')) {
      try {
        await employeeAPI.deleteEmployee(id);
        loadData();
      } catch (error) {
        console.error('Error deleting employee:', error);
        alert('Error deleting employee');
      }
    }
  };

  const canEdit = user?.role === 'admin' || user?.role === 'editor';

  const positionOptions = useMemo(() => {
    const set = new Set();
    employees.forEach((e) => {
      if (e.position && String(e.position).trim()) set.add(String(e.position).trim());
    });
    return ['', ...Array.from(set).sort()];
  }, [employees]);

  const lastNames = useMemo(() => {
    const set = new Set();
    employees.forEach((e) => {
      const n = (e.last_name || '').trim();
      if (n) set.add(n);
    });
    return [...set].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  }, [employees]);

  const firstNames = useMemo(() => {
    const set = new Set();
    employees.forEach((e) => {
      const n = (e.first_name || '').trim();
      if (n) set.add(n);
    });
    return [...set].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  }, [employees]);

  // Prefix filter: same for last name and first name — type "H" → names starting with H, "He" → starting with He
  const filterOptionsByPrefix = (options, state) => {
    const input = (state.inputValue || '').trim().toLowerCase();
    if (!input) return options;
    return options.filter((opt) => String(opt || '').toLowerCase().startsWith(input));
  };

  const filteredEmployees = useMemo(() => {
    if (!employees.length) return [];
    const last = (filterLastName || '').trim().toLowerCase();
    const first = (filterFirstName || '').trim().toLowerCase();
    const position = (filterPosition || '').trim();
    return employees.filter((e) => {
      if (last && !(e.last_name || '').toLowerCase().startsWith(last)) return false;
      if (first && !(e.first_name || '').toLowerCase().startsWith(first)) return false;
      if (position && (e.position || '').trim() !== position) return false;
      if (filterMedicalDue && !passesMedicalDueFilter(e, filterMedicalDue)) return false;
      return true;
    });
  }, [employees, filterLastName, filterFirstName, filterPosition, filterMedicalDue]);

  const clearFilters = () => {
    setFilterLastName('');
    setFilterFirstName('');
    setFilterPosition('');
    setFilterMedicalDue('');
  };

  const hasActiveFilters = filterLastName || filterFirstName || filterPosition || filterMedicalDue;

  return (
    <Box>
      <AppHeader
        backTo="/"
        rightContent={
          <>
            <Typography variant="subtitle1" component="span" sx={{ flexGrow: 1, textAlign: 'left' }}>
              Employees - {currentSession?.name || 'Loading...'}
            </Typography>
            {canEdit && (
              <Button
                color="inherit"
                startIcon={<Add />}
                onClick={() => navigate('/employees/new')}
              >
                Add Employee
              </Button>
            )}
          </>
        }
      />

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        {loading ? (
          <Typography sx={{ py: 3 }}>Loading employees…</Typography>
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
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Position</InputLabel>
            <Select
              label="Position"
              value={filterPosition}
              onChange={(e) => setFilterPosition(e.target.value)}
            >
              <MenuItem value="">All positions</MenuItem>
              {positionOptions.filter(Boolean).map((pos) => (
                <MenuItem key={pos} value={pos}>{pos}</MenuItem>
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
          {hasActiveFilters && (
            <Button size="small" startIcon={<Clear />} onClick={clearFilters}>
              Clear filters
            </Button>
          )}
          <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            Showing {filteredEmployees.length} of {employees.length}
          </Typography>
        </Paper>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Position</TableCell>
                <TableCell>Medical due</TableCell>
                <TableCell>Home phone</TableCell>
                <TableCell>Mobile</TableCell>
                {canEdit && <TableCell>Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredEmployees.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={canEdit ? 7 : 6} align="center" sx={{ py: 4 }}>
                    {employees.length === 0
                      ? `No employees in ${currentSession?.name || 'this session'}.`
                      : 'No employees match the current filters.'}
                  </TableCell>
                </TableRow>
              ) : filteredEmployees.map((employee) => (
                <TableRow
                  key={employee.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/employees/${employee.id}`)}
                >
                  <TableCell>
                    {employee.first_name} {employee.last_name}
                  </TableCell>
                  <TableCell>{employee.email}</TableCell>
                  <TableCell>{employee.position}</TableCell>
                  <TableCell>{employee.medical_due_date || '-'}</TableCell>
                  <TableCell>{employee.phone || '-'}</TableCell>
                  <TableCell>{employee.mobile_phone || '-'}</TableCell>
                  {canEdit && (
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <IconButton
                        size="small"
                        onClick={() => navigate(`/employees/${employee.id}/edit`)}
                        aria-label="Edit"
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(employee.id)}
                        aria-label="Delete"
                      >
                        <Delete />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        </>
        )}
      </Container>
    </Box>
  );
};

export default EmployeeList;
