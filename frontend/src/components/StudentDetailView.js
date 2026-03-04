import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { ArrowBack, Edit, PictureAsPdf, Upload, Delete } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { studentAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Field = ({ label, value }) => (
  <Box sx={{ mb: 1.5 }}>
    <Typography variant="caption" color="text.secondary" display="block">
      {label}
    </Typography>
    <Typography variant="body1">{value ?? '—'}</Typography>
  </Box>
);

const formatDate = (d) => {
  if (!d) return '—';
  const s = typeof d === 'string' ? d.split('T')[0] : '';
  const [y, m, day] = s.split('-');
  return y && m && day ? `${Number(m)}/${Number(day)}/${y}` : '—';
};

const StudentDetailView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pdfUploading, setPdfUploading] = useState(false);
  const [pdfError, setPdfError] = useState(null);
  const fileInputRef = React.useRef(null);

  useEffect(() => {
    let cancelled = false;
    studentAPI
      .getStudent(id)
      .then((res) => {
        if (!cancelled) setStudent(res.data);
      })
      .catch(() => {
        if (!cancelled) setStudent(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  const canEdit = user?.role === 'admin' || user?.role === 'editor';
  const isFloater = (student?.last_name || '').toLowerCase() === 'floater';

  const handleViewPdf = () => {
    setPdfError(null);
    studentAPI.openPdf(id).catch((err) => {
      setPdfError(err.message || 'Could not open PDF');
    });
  };

  const handleUploadPdf = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setPdfError('Please select a PDF file.');
      return;
    }
    setPdfError(null);
    setPdfUploading(true);
    studentAPI
      .uploadPdf(id, file)
      .then((res) => {
        setStudent(res.data);
        if (fileInputRef.current) fileInputRef.current.value = '';
      })
      .catch((err) => {
        setPdfError(err.response?.data?.detail || err.message || 'Upload failed');
      })
      .finally(() => setPdfUploading(false));
  };

  const handleRemovePdf = () => {
    if (!window.confirm('Remove the attached PDF from this record?')) return;
    setPdfError(null);
    studentAPI
      .deletePdf(id)
      .then(() => setStudent((s) => (s ? { ...s, uploaded_pdf_url: null } : null)))
      .catch((err) => setPdfError(err.response?.data?.detail || err.message || 'Remove failed'));
  };

  if (loading) {
    return (
      <Box>
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Typography>Loading…</Typography>
        </Container>
      </Box>
    );
  }

  if (!student) {
    return (
      <Box>
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Typography color="error">Student not found.</Typography>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/students')} sx={{ mt: 2 }}>
            Back to Search
          </Button>
        </Container>
      </Box>
    );
  }

  const districtDisplay = student.district_display || student.district || student.school_district || '—';
  const dischargeDisplay = student.discharge_date ? formatDate(student.discharge_date) : (student.discharge_notes || '—');

  return (
    <Box>
      <Paper elevation={0} sx={{ px: 2, py: 1.5, mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/students')}>
          Back to Search
        </Button>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Edit />}
            onClick={() => navigate(`/students/${id}/edit`)}
          >
            Edit
          </Button>
        )}
      </Paper>

      <Container maxWidth="md" sx={{ pb: 4 }}>
        {student.duplicate_warning && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Possible duplicate record detected. Another student in this session has the same name and DOB.
          </Alert>
        )}
        {isFloater && (
          <Alert severity="info" sx={{ mb: 2 }}>
            This record is marked as a non-student placeholder (floater).
          </Alert>
        )}

        <Typography variant="h5" gutterBottom>
          {student.first_name} {student.last_name}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Session: {student.session_name} · Student ID: {student.id}
        </Typography>
        <Chip label={student.status} size="small" sx={{ mt: 1 }} />

        {/* A) Demographics / Contact */}
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Demographics / Contact
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}><Field label="Last name" value={student.last_name} /></Grid>
            <Grid item xs={12} sm={6}><Field label="First name" value={student.first_name} /></Grid>
            <Grid item xs={12} sm={6}><Field label="DOB" value={formatDate(student.date_of_birth)} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Student ID" value={student.id} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Phone / Home phone" value={student.home_phone || student.parent_phone} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Mother cell" value={student.mother_cell} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Father cell" value={student.father_cell} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Email" value={student.email || student.parent_email} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Discharge" value={dischargeDisplay} /></Grid>
            <Grid item xs={12} sm={6}><Field label="District (Schooldist)" value={districtDisplay} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Address" value={student.address} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Class" value={student.class_num} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Funding code" value={student.funding_code} /></Grid>
            <Grid item xs={12} sm={6}><Field label="1:1 Aide" value={student.aide_1to1} /></Grid>
          </Grid>
        </Paper>

        {/* B) Medical */}
        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Medical
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}><Field label="Vaccines" value={student.vaccines_status || student.vaccines_notes} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Vaccines last reviewed" value={formatDate(student.vaccines_last_reviewed)} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Medical start date" value={formatDate(student.medical_start_date)} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Medical end date" value={formatDate(student.medical_end_date)} /></Grid>
            <Grid item xs={12} sm={6}><Field label="Medical due" value={formatDate(student.medical_due_date)} /></Grid>
            {(student.medical_info != null && student.medical_info !== '') && (
              <Grid item xs={12}><Field label="Nurses medical notes (restricted)" value="*** on file ***" /></Grid>
            )}
          </Grid>
        </Paper>

        {/* C) SPED / Program / IFSP-IEP */}
        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            SPED / Program / IFSP-IEP
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}><Field label="SPED INDIV Code" value={student.sped_indiv_code} /></Grid>
          </Grid>
        </Paper>

        {/* D) Services */}
        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Services
          </Typography>
          {Array.isArray(student.services) && student.services.length > 0 ? (
            <TableContainer><Table size="small">
              <TableHead><TableRow><TableCell>Service</TableCell><TableCell>Provider</TableCell><TableCell>Start</TableCell><TableCell>Due</TableCell></TableRow></TableHead>
              <TableBody>
                {student.services.map((svc, i) => (
                  <TableRow key={i}>
                    <TableCell>{svc.service_type}</TableCell>
                    <TableCell>{svc.provider}</TableCell>
                    <TableCell>{formatDate(svc.start_date)}</TableCell>
                    <TableCell>{formatDate(svc.due_date)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table></TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">No services recorded.</Typography>
          )}
        </Paper>

        {/* E) Reporting */}
        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Reporting
          </Typography>
          {student.reports && typeof student.reports === 'object' && Object.keys(student.reports).length > 0 ? (
            <Typography variant="body2">{JSON.stringify(student.reports)}</Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">No report data.</Typography>
          )}
        </Paper>

        {/* F) Meetings */}
        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Meetings
          </Typography>
          {Array.isArray(student.meetings) && student.meetings.length > 0 ? (
            <TableContainer><Table size="small">
              <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Time</TableCell><TableCell>Place</TableCell><TableCell>Packet sent</TableCell><TableCell>Packet received</TableCell></TableRow></TableHead>
              <TableBody>
                {student.meetings.map((m, i) => (
                  <TableRow key={i}>
                    <TableCell>{formatDate(m.date)}</TableCell>
                    <TableCell>{m.time}</TableCell>
                    <TableCell>{m.place}</TableCell>
                    <TableCell>{m.packet_sent ? 'Yes' : '—'}</TableCell>
                    <TableCell>{m.packet_received ? 'Yes' : '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table></TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">No meetings recorded.</Typography>
          )}
        </Paper>

        {/* G) Notes + Incidents */}
        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Notes
          </Typography>
          <Field label="Notes (general)" value={student.notes} />
          {student.phi_encrypted && (
            <Typography variant="caption" color="text.secondary" display="block">PHI/PII on file (restricted)</Typography>
          )}
        </Paper>

        {Array.isArray(student.incidents) && student.incidents.length > 0 && (
          <Paper sx={{ p: 3, mt: 2 }}>
            <Typography variant="h6" color="primary" gutterBottom>
              Incidents
            </Typography>
            <TableContainer><Table size="small">
              <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Time</TableCell><TableCell>Location</TableCell><TableCell>Type</TableCell><TableCell>Description</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
              <TableBody>
                {student.incidents.map((inc) => (
                  <TableRow key={inc.id}>
                    <TableCell>{inc.incident_date}</TableCell>
                    <TableCell>{inc.incident_time || '—'}</TableCell>
                    <TableCell>{inc.location || '—'}</TableCell>
                    <TableCell>{inc.incident_type || '—'}</TableCell>
                    <TableCell>{(inc.description || '').slice(0, 80)}{(inc.description || '').length > 80 ? '…' : ''}</TableCell>
                    <TableCell>{inc.status}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table></TableContainer>
          </Paper>
        )}

        <Paper sx={{ p: 3, mt: 2 }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Attached PDF
          </Typography>
          {student.uploaded_pdf_url ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
              <Button variant="contained" startIcon={<PictureAsPdf />} onClick={handleViewPdf} size="small">Open PDF</Button>
              {canEdit && (
                <>
                  <Button variant="outlined" startIcon={<Upload />} onClick={() => fileInputRef.current?.click()} disabled={pdfUploading} size="small">{pdfUploading ? 'Uploading…' : 'Replace PDF'}</Button>
                  <Button variant="outlined" color="error" startIcon={<Delete />} onClick={handleRemovePdf} size="small">Remove PDF</Button>
                </>
              )}
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">No PDF attached.</Typography>
              {canEdit && (
                <Button variant="outlined" startIcon={pdfUploading ? <CircularProgress size={16} /> : <Upload />} onClick={() => fileInputRef.current?.click()} disabled={pdfUploading} size="small">{pdfUploading ? 'Uploading…' : 'Upload PDF'}</Button>
              )}
            </Box>
          )}
          {canEdit && <input ref={fileInputRef} type="file" accept=".pdf,application/pdf" onChange={handleUploadPdf} style={{ display: 'none' }} />}
          {pdfError && <Typography variant="body2" color="error" sx={{ mt: 1 }}>{pdfError}</Typography>}
        </Paper>

        {user?.role === 'admin' && (student.ssn != null || student.medical_info != null) && (
          <Paper sx={{ p: 3, mt: 2 }}>
            <Typography variant="h6" color="primary" gutterBottom>Sensitive (admin only)</Typography>
            <Field label="SSN" value={student.ssn ? '*** on file ***' : null} />
            <Field label="Medical info" value={student.medical_info ? '*** on file ***' : null} />
          </Paper>
        )}
      </Container>
    </Box>
  );
};

export default StudentDetailView;
