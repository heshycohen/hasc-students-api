import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    if (token) {
      authAPI
        .getCurrentUser()
        .then((userData) => {
          setUser(userData);
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    try {
      await authAPI.login(email, password);
      const userData = await authAPI.getCurrentUser();
      setUser(userData);
      return { success: true };
    } catch (error) {
      const apiBase = process.env.REACT_APP_API_URL || '/api';
      const networkUnreachable =
        error.response?.status === 0 ||
        !error.response ||
        (error.message && error.message.toLowerCase().includes('network error'));
      if (networkUnreachable) {
        return {
          success: false,
          error: 'Cannot reach backend. Is it running on http://localhost:8000? (Frontend proxies /api to the backend.)',
        };
      }
      const data = error.response?.data;
      const detail = data?.detail;
      let msg = typeof detail === 'string' ? detail : (Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join(' ') : null);
      if (!msg && data) msg = typeof data === 'string' ? data : JSON.stringify(data);
      if (!msg) msg = error.message || (error.response?.status === 401 ? 'Invalid email or password.' : 'Login failed');
      return {
        success: false,
        error: msg,
      };
    }
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
