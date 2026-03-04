import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Login from './components/Login';
import LoginCallback from './components/LoginCallback';
import Dashboard from './components/Dashboard';
import StudentList from './components/StudentList';
import StudentDetailView from './components/StudentDetailView';
import StudentEditForm from './components/StudentEditForm';
import StudentRosterPage from './components/StudentRosterPage';
import StudentRosterList from './components/StudentRosterList';
import MedicalDueReports from './components/MedicalDueReports';
import IncidentLog from './components/IncidentLog';
import AttendancePage from './components/AttendancePage';
import EmployeeList from './components/EmployeeList';
import EmployeeDetailView from './components/EmployeeDetailView';
import ComplianceReports from './components/ComplianceReports';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import './App.css';

const theme = createTheme({
  palette: {
    primary: {
      main: '#37474f',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
      <Route path="/login/callback" element={<LoginCallback />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
      <Route
        path="/students"
        element={
          <PrivateRoute>
            <StudentList />
          </PrivateRoute>
        }
      />
      <Route
        path="/students/roster"
        element={
          <PrivateRoute>
            <StudentRosterPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/students/roster-list"
        element={
          <PrivateRoute>
            <StudentRosterList />
          </PrivateRoute>
        }
      />
      <Route
        path="/reports/medical-due"
        element={
          <PrivateRoute>
            <MedicalDueReports />
          </PrivateRoute>
        }
      />
      <Route
        path="/incidents"
        element={
          <PrivateRoute>
            <IncidentLog />
          </PrivateRoute>
        }
      />
      <Route
        path="/attendance"
        element={
          <PrivateRoute>
            <AttendancePage />
          </PrivateRoute>
        }
      />
      <Route
        path="/students/:id"
        element={
          <PrivateRoute>
            <StudentDetailView />
          </PrivateRoute>
        }
      />
      <Route
        path="/students/:id/edit"
        element={
          <PrivateRoute>
            <StudentEditForm />
          </PrivateRoute>
        }
      />
      <Route
        path="/employees"
        element={
          <PrivateRoute>
            <EmployeeList />
          </PrivateRoute>
        }
      />
      <Route
        path="/employees/:id"
        element={
          <PrivateRoute>
            <EmployeeDetailView />
          </PrivateRoute>
        }
      />
      <Route
        path="/compliance"
        element={
          <PrivateRoute requiredRole="admin">
            <ComplianceReports />
          </PrivateRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <AppRoutes />
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
