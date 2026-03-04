import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { complianceAPI } from '../services/api';
import AppHeader from './AppHeader';

const ComplianceReports = () => {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [accessLogs, setAccessLogs] = useState([]);
  const [disclosures, setDisclosures] = useState([]);
  const [securityEvents, setSecurityEvents] = useState([]);

  useEffect(() => {
    if (tabValue === 0) loadAccessLogs();
    if (tabValue === 1) loadDisclosures();
    if (tabValue === 2) loadSecurityEvents();
  }, [tabValue]);

  const loadAccessLogs = async () => {
    try {
      const response = await complianceAPI.getAccessLogs();
      setAccessLogs(response.data.results || response.data);
    } catch (error) {
      console.error('Error loading access logs:', error);
    }
  };

  const loadDisclosures = async () => {
    try {
      const response = await complianceAPI.getDisclosures();
      setDisclosures(response.data.results || response.data);
    } catch (error) {
      console.error('Error loading disclosures:', error);
    }
  };

  const loadSecurityEvents = async () => {
    try {
      const response = await complianceAPI.getSecurityEvents();
      setSecurityEvents(response.data.results || response.data);
    } catch (error) {
      console.error('Error loading security events:', error);
    }
  };

  return (
    <Box>
      <AppHeader backTo="/" rightContent={<Typography variant="subtitle1">Compliance Reports</Typography>} />

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="Access Logs" />
            <Tab label="Disclosures" />
            <Tab label="Security Events" />
          </Tabs>

          <Box sx={{ p: 3 }}>
            {tabValue === 0 && (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell>Record Type</TableCell>
                      <TableCell>Action</TableCell>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>IP Address</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {accessLogs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell>{log.user_email}</TableCell>
                        <TableCell>{log.record_type}</TableCell>
                        <TableCell>{log.action}</TableCell>
                        <TableCell>{log.timestamp}</TableCell>
                        <TableCell>{log.ip_address}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {tabValue === 1 && (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Student</TableCell>
                      <TableCell>Disclosed To</TableCell>
                      <TableCell>Purpose</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Consent Obtained</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {disclosures.map((disclosure) => (
                      <TableRow key={disclosure.id}>
                        <TableCell>
                          {disclosure.student?.first_name}{' '}
                          {disclosure.student?.last_name}
                        </TableCell>
                        <TableCell>{disclosure.disclosed_to}</TableCell>
                        <TableCell>{disclosure.purpose}</TableCell>
                        <TableCell>{disclosure.date_disclosed}</TableCell>
                        <TableCell>
                          {disclosure.consent_obtained ? 'Yes' : 'No'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {tabValue === 2 && (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Event Type</TableCell>
                      <TableCell>User</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Resolved</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {securityEvents.map((event) => (
                      <TableRow key={event.id}>
                        <TableCell>{event.event_type}</TableCell>
                        <TableCell>{event.user_email || '-'}</TableCell>
                        <TableCell>{event.severity}</TableCell>
                        <TableCell>{event.timestamp}</TableCell>
                        <TableCell>{event.resolved ? 'Yes' : 'No'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default ComplianceReports;
