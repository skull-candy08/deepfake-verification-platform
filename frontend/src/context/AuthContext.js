import React, { createContext, useState, useEffect } from 'react';
import apiClient from '../utils/api';
import { jwtDecode } from 'jwt-decode';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      localStorage.removeItem('token');
      delete apiClient.defaults.headers.common['Authorization'];
      setUser(null);
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const res = await apiClient.get('/api/auth/me');
      setUser(res.data.user);
    } catch (err) {
      console.error("Failed to fetch user:", err);
      setToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const res = await apiClient.post('/api/auth/login', { username, password });
    setToken(res.data.token);
    setUser(res.data.user);
  };

  const register = async (username, password) => {
    const res = await apiClient.post('/api/auth/register', { username, password });
    setToken(res.data.token);
    setUser(res.data.user);
  };

  const logout = () => {
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
