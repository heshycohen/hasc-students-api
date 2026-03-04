import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Save, Cancel } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { studentAPI, sessionAPI } from '../services/api';
import websocketService from '../services/websocket';
import ConflictResolution from './ConflictResolution';
import { useAuth } from '../contexts/AuthContext';

const StudentEditForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [student, setStudent] = useState(null);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeUsers, setActiveUsers] = useState([]);
  const [conflict, setConflict] = useState(null);
  const [ws, setWs] = useState(null);
  const [classrooms, setClassrooms] = useState([]);

  useEffect(() => {
    loadStudent();
    return () => {
      if (ws) {
        websocketService.disconnect(`student_${id}`);
      }
    };
  }, [id]);

  const loadStudent = async () => {
    try {
      const response = await studentAPI.getStudent(id);
      const data = response.data;
      setStudent(data);
      setFormData(data);
      if (data.session) {
        try {
          const classRes = await sessionAPI.getClassrooms(data.session);
          const list = classRes.data.results || classRes.data || [];
          setClassrooms(Array.isArray(list) ? list : []);
        } catch (_) {
          setClassrooms([]);
        }
      }
      setLoading(false);

      // Connect WebSocket
      const token = localStorage.getItem('access_token');
      const websocket = websocketService.connectStudent(id, token, {
        onOpen: () => {
          console.log('WebSocket connected');
        },
        onUserJoined: (data) => {
          setActiveUsers((prev) => [...prev, data.user_email]);
        },
        onUserLeft: (data) => {
          setActiveUsers((prev) => prev.filter((email) => email !== data.user_email));
        },
        onRecordUpdated: (data) => {
          if (data.user_email !== user?.email) {
            // Another user updated the record
            setConflict({
              current_version: data.version,
              message: `Record was updated by ${data.user_email}`,
            });
            // Reload student data
            loadStudent();
          }
        },
        onConflict: (data) => {
          setConflict(data);
        },
        onError: (error) => {
          console.error('WebSocket error:', error);
        },
      });
      setWs(websocket);
    } catch (error) {
      console.error('Error loading student:', error);
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await studentAPI.updateStudent(id, {
        ...formData,
        version: student.version, // Include version for optimistic locking
      });
      setStudent(response.data);
      setSaving(false);
      navigate('/students');
    } catch (error) {
      if (error.response?.data?.version) {
        // Version conflict
        setConflict({
          current_version: error.response.data.version,
          message: 'Record was modified by another user',
        });
        // Reload student
        loadStudent();
      } else {
        alert('Error saving student: ' + (error.response?.data?.detail || error.message));
      }
      setSaving(false);
    }
  };

  const handleConflictResolve = (resolution, data) => {
    if (resolution === 'server') {
      setFormData(data);
      setStudent({ ...student, ...data });
    } else if (resolution === 'local') {
      // Retry save with current version
      handleSave();
    }
    setConflict(null);
  };

  if (loading) {
    return (
      <Container>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5">Edit Student</Typography>
          <Box>
            {activeUsers.length > 0 && (
              <Chip
                label={`${activeUsers.length} other user(s) editing`}
                color="info"
                size="small"
                sx={{ mr: 1 }}
              />
            )}
            {student.locked_by_email && student.locked_by_email !== user?.email && (
              <Chip
                label={`Locked by ${student.locked_by_email}`}
                color="warning"
                size="small"
              />
            )}
          </Box>
        </Box>

        {conflict && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {conflict.message}
          </Alert>
        )}

        <Box component="form" sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="First Name"
            value={formData.first_name || ''}
            onChange={(e) => handleChange('first_name', e.target.value)}
            fullWidth
            required
          />
          <TextField
            label="Last Name"
            value={formData.last_name || ''}
            onChange={(e) => handleChange('last_name', e.target.value)}
            fullWidth
            required
          />
          <TextField
            label="Date of Birth"
            type="date"
            value={formData.date_of_birth || ''}
            onChange={(e) => handleChange('date_of_birth', e.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
            required
          />
          <TextField
            label="Enrollment Date"
            type="date"
            value={formData.enrollment_date || ''}
            onChange={(e) => handleChange('enrollment_date', e.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
            required
          />
          <TextField
            label="Parent Email"
            type="email"
            value={formData.parent_email || ''}
            onChange={(e) => handleChange('parent_email', e.target.value)}
            fullWidth
          />
          <TextField
            label="Parent Phone"
            value={formData.parent_phone || ''}
            onChange={(e) => handleChange('parent_phone', e.target.value)}
            fullWidth
          />

          <FormControl fullWidth size="small">
            <InputLabel>Class (center-based only; leave empty for related service)</InputLabel>
            <Select
              label="Class (center-based only; leave empty for related service)"
              value={formData.class_num ?? ''}
              onChange={(e) => handleChange('class_num', e.target.value || null)}
            >
              <MenuItem value="">Related service (not on roster)</MenuItem>
              {classrooms.map((c) => (
                <MenuItem key={c.id} value={c.class_num}>
                  {c.label || `${c.class_num} / ${c.class_size || '—'}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box display="flex" gap={2} justifyContent="flex-end" sx={{ mt: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Cancel />}
              onClick={() => navigate('/students')}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              startIcon={<Save />}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </Box>
        </Box>
      </Paper>

      <ConflictResolution
        open={!!conflict}
        conflict={conflict}
        onResolve={handleConflictResolve}
        onCancel={() => setConflict(null)}
        currentData={formData}
        serverData={student}
      />
    </Container>
  );
};

export default StudentEditForm;
