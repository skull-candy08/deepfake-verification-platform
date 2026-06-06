import API from './api';

const TOKEN_KEY = 'deepscan_access_token';
const REFRESH_KEY = 'deepscan_refresh_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY);

export const setTokens = (access, refresh) => {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
};

export const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
};

export const isAuthenticated = () => {
  const token = getToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
};

export const login = async (email, password) => {
  const res = await API.post('/auth/login', { email, password });
  setTokens(res.data.access_token, res.data.refresh_token);
  return res.data;
};

export const register = async (username, email, password) => {
  const res = await API.post('/auth/register', { username, email, password });
  setTokens(res.data.access_token, res.data.refresh_token);
  return res.data;
};

export const logout = () => {
  clearTokens();
};

export const refreshAccessToken = async () => {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error('No refresh token');
  const res = await API.post('/auth/refresh', {}, {
    headers: { Authorization: `Bearer ${refresh}` }
  });
  localStorage.setItem(TOKEN_KEY, res.data.access_token);
  return res.data.access_token;
};
