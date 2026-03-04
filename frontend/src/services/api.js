import axios from 'axios';
import DOMPurify from 'dompurify';

// Use relative /api in dev so the dev server proxy (see package.json "proxy") forwards to backend; no CORS.
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        });

        const { access } = response.data;
        localStorage.setItem('access_token', access);
        originalRequest.headers.Authorization = `Bearer ${access}`;

        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Sanitize input to prevent XSS
export const sanitizeInput = (input) => {
  if (typeof input === 'string') {
    return DOMPurify.sanitize(input);
  }
  return input;
};

// API methods
export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/auth/token/', {
      email: sanitizeInput(email),
      password,
    });
    if (response.data.access) {
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
    }
    return response.data;
  },
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
  getCurrentUser: async () => {
    const response = await api.get('/auth/users/me/');
    return response.data;
  },
};

export const sessionAPI = {
  getSessions: () => api.get('/sessions/sessions/'),
  getCurrentSession: () => api.get('/sessions/current-session/'),
  setActiveSession: (sessionId) =>
    api.post(`/sessions/sessions/${sessionId}/set_active/`),
  copySession: (targetId, sourceId) =>
    api.post(`/sessions/sessions/${targetId}/copy/`, {
      source_session_id: sourceId,
    }),
  getClassrooms: (sessionId) =>
    api.get('/sessions/classrooms/', {
      params: sessionId ? { session: sessionId } : {},
    }),
  getFundingCodes: (sessionId) =>
    api.get('/sessions/funding-codes/', {
      params: sessionId ? { session: sessionId } : {},
    }),
  getSchoolDistricts: (sessionId) =>
    api.get('/sessions/school-districts/', {
      params: sessionId ? { session: sessionId } : {},
    }),
  getRoster: (sessionId) =>
    api.get('/sessions/roster/', {
      params: sessionId ? { session: sessionId } : {},
    }),
  getMedicalDueReport: (params) =>
    api.get('/sessions/medical-due-report/', { params }),
  getMedicalDueReportCsv: (params) =>
    api.get('/sessions/medical-due-report/', { params: { ...params, export: 'csv' }, responseType: 'blob' }),
  getIncidents: (params) =>
    api.get('/sessions/incidents/', { params }),
  getIncident: (id) => api.get(`/sessions/incidents/${id}/`),
  createIncident: (data) => api.post('/sessions/incidents/', data),
  updateIncident: (id, data) => api.patch(`/sessions/incidents/${id}/`, data),
  deleteIncident: (id) => api.delete(`/sessions/incidents/${id}/`),
  getAbsenceReasons: () => api.get('/sessions/absence-reasons/'),
  getAttendance: (params) => api.get('/sessions/attendance/', { params }),
  getAttendanceDailyAbsentReport: (params) =>
    api.get('/sessions/attendance/daily-absent-report/', { params }),
  getAttendanceDailyAbsentReportCsv: (params) =>
    api.get('/sessions/attendance/daily-absent-report/', { params: { ...params, export: 'csv' }, responseType: 'blob' }),
  createAttendanceRecord: (data) => api.post('/sessions/attendance/', data),
  updateAttendanceRecord: (id, data) => api.patch(`/sessions/attendance/${id}/`, data),
};

export const studentAPI = {
  getStudents: (sessionId, params = {}) =>
    api.get('/sessions/students/', {
      params: {
        ...(sessionId ? { session: sessionId } : {}),
        page_size: 2000,
        ...params,
      },
    }),
  downloadRosterCsv: async (sessionId, params = {}) => {
    const res = await api.get('/sessions/students/', {
      params: { session: sessionId || '', page_size: 5000, export: 'csv', ...params },
      responseType: 'blob',
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'student_roster.csv';
    a.click();
    URL.revokeObjectURL(url);
  },
  getStudent: (id) => api.get(`/sessions/students/${id}/`),
  createStudent: (data) => api.post('/sessions/students/', sanitizeInput(data)),
  updateStudent: (id, data) =>
    api.patch(`/sessions/students/${id}/`, sanitizeInput(data)),
  deleteStudent: (id) => api.delete(`/sessions/students/${id}/`),
  uploadPdf: (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/sessions/students/${id}/upload-pdf/`, formData);
  },
  deletePdf: (id) => api.delete(`/sessions/students/${id}/uploaded-pdf/`),
  openPdf: async (id) => {
    const res = await api.get(`/sessions/students/${id}/pdf/`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },
};

export const employeeAPI = {
  getEmployees: (sessionId) =>
    api.get('/sessions/employees/', {
      params: {
        ...(sessionId ? { session: sessionId } : {}),
        page_size: 2000,
      },
    }),
  getEmployee: (id) => api.get(`/sessions/employees/${id}/`),
  createEmployee: (data) => api.post('/sessions/employees/', sanitizeInput(data)),
  updateEmployee: (id, data) =>
    api.patch(`/sessions/employees/${id}/`, sanitizeInput(data)),
  deleteEmployee: (id) => api.delete(`/sessions/employees/${id}/`),
};

export const complianceAPI = {
  getAccessLogs: (params) => api.get('/compliance/access-logs/', { params }),
  getDisclosures: (params) => api.get('/compliance/disclosures/', { params }),
  getSecurityEvents: (params) =>
    api.get('/compliance/security-events/', { params }),
  getAccessReport: (params) =>
    api.get('/compliance/reports/access/', { params }),
  getDisclosureReport: (params) =>
    api.get('/compliance/reports/disclosures/', { params }),
};

export default api;
