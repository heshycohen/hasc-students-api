import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button, Typography, Box } from '@mui/material';
import { Print } from '@mui/icons-material';
import { sessionAPI } from '../services/api';
import './StudentRosterPage.css';

/**
 * Student roster report: one page per class.
 * Header: "Student Roster School Year 2025-2026" + run date + "Printed" (thick top/bottom border).
 * Class section (2 columns): left = CLASS NUMBER, CLASS SIZE; right = Teacher, ASSISTANT 1, ASSISTANT 2.
 * Table: LAST NAME, FIRST NAME, DOB, SCHOOLDIST, FUNDING, 1:1AIDE, Phone Number.
 * Footer: Page X of Y, HASC Rockland.
 */
const StudentRosterPage = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  const [roster, setRoster] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await sessionAPI.getRoster(sessionId || undefined);
        if (!cancelled) setRoster(res.data);
      } catch (e) {
        if (!cancelled) {
          const msg = e.response?.data?.detail
            || (typeof e.response?.data === 'string' ? e.response.data : null)
            || e.message
            || 'Failed to load roster';
          setError(msg);
          setRoster(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [sessionId]);

  // Format ISO date-only (YYYY-MM-DD) as M/D/YYYY without timezone shift (avoids showing previous day in US tz)
  const formatDateLocal = (d) => {
    if (!d) return '';
    const s = typeof d === 'string' ? d.split('T')[0] : '';
    const [y, m, day] = s.split('-');
    if (!y || !m || !day) return '';
    return `${Number(m)}/${Number(day)}/${y}`;
  };

  const formatDate = (d) => {
    if (!d) return '';
    const s = typeof d === 'string' ? d.split('T')[0] : '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return formatDateLocal(d);
    const dt = new Date(d);
    return dt.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' });
  };

  const formatPhoneCell = (phone) => {
    const p = (phone ?? '').trim();
    if (!p) return '';
    return p.startsWith('(') ? p : `(${p})`;
  };

  if (loading) return <Box sx={{ p: 3 }}>Loading roster…</Box>;
  if (error) return <Box sx={{ p: 3 }} color="error">Error: {error}</Box>;
  if (!roster) return <Box sx={{ p: 3 }}>No roster data.</Box>;

  const headerDate = roster?.generated_date ? formatDateLocal(roster.generated_date) : '';
  const sessionTitle = roster?.session_name ? `Student Roster ${roster.session_name}` : 'Student Roster';
  const classrooms = Array.isArray(roster?.classrooms) ? roster.classrooms : [];
  const totalPages = Math.max(1, classrooms.length);

  // Empty roster: one printable page with session header and message
  if (classrooms.length === 0) {
    return (
      <Box className="roster-print-container">
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, p: 1, '@media print': { display: 'none' } }}>
          <Button variant="contained" startIcon={<Print />} onClick={() => window.print()}>
            Print / Save as PDF
          </Button>
        </Box>
        <Box className="roster-section">
          <div className="roster-header-block">
            <span className="roster-header-title">{sessionTitle}</span>
            <span className="roster-header-printed">Printed {headerDate}</span>
          </div>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography>No students with class assignment for this session.</Typography>
          </Box>
          <div className="roster-footer">
            <span>Page 1 of 1</span>
            <span>HASC Rockland</span>
          </div>
        </Box>
      </Box>
    );
  }

  return (
    <Box className="roster-print-container">
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, p: 1, '@media print': { display: 'none' } }}>
        <Button variant="contained" startIcon={<Print />} onClick={() => window.print()}>
          Print / Save as PDF
        </Button>
      </Box>
      {classrooms.map((section, pageIndex) => (
        <Box key={section.class_num + pageIndex} className="roster-section">
          <div className="roster-header-block">
            <span className="roster-header-title">{sessionTitle}</span>
            <span className="roster-header-printed">Printed {headerDate}</span>
          </div>
          <div className="roster-class-block">
            <div className="roster-class-left">
              <div className="roster-class-row">
                <span className="roster-class-label">CLASS NUMBER:</span>
                <span className="roster-class-value">{section.class_num ?? ''}</span>
              </div>
              <div className="roster-class-row" title="e.g. 12:1:2 = 12 students, 1 teacher, 2 assistants; 8:1:2 = 8,1,2; 6:1:2 = 6,1,2. With 1:1 aide, class may exceed ratio with special approval.">
                <span className="roster-class-label">CLASS SIZE:</span>
                <span className="roster-class-value">{section.class_size ?? ''}</span>
              </div>
            </div>
            <div className="roster-class-right">
              <div className="roster-class-row">
                <span className="roster-class-label roster-teacher-label">Teacher:</span>
                <span className="roster-class-value">{section.teacher ?? ''}</span>
              </div>
              <div className="roster-class-row">
                <span className="roster-class-label">ASSISTANT 1:</span>
                <span className="roster-class-value">{section.assistant1 ?? ''}</span>
              </div>
              <div className="roster-class-row">
                <span className="roster-class-label">ASSISTANT 2:</span>
                <span className="roster-class-value">{section.assistant2 ?? ''}</span>
              </div>
            </div>
          </div>
          <table className="roster-table">
            <thead>
              <tr>
                <th>LAST NAME</th>
                <th>FIRST NAME</th>
                <th>DOB</th>
                <th>SCHOOLDIST</th>
                <th>FUNDING</th>
                <th>1:1AIDE</th>
                <th>Phone Number</th>
              </tr>
            </thead>
            <tbody>
              {(section.students || []).map((s, idx) => (
                <tr key={idx}>
                  <td>{s.last_name ?? ''}</td>
                  <td>{s.first_name ?? ''}</td>
                  <td>{formatDate(s.date_of_birth)}</td>
                  <td>{s.school_district ?? ''}</td>
                  <td>{s.funding_code ?? ''}</td>
                  <td>{s.aide_1to1 ?? ''}</td>
                  <td>{formatPhoneCell(s.parent_phone)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="roster-footer">
            <span>Page {pageIndex + 1} of {totalPages}</span>
            <span>HASC Rockland</span>
          </div>
        </Box>
      ))}
    </Box>
  );
};

export default StudentRosterPage;
