import API from './api';

export const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
};

export const isAuthenticated = () => {
  // If we have a CSRF access token, we assume we are authenticated
  // (the backend will ultimately validate the HttpOnly cookie)
  return !!getCookie('csrf_access_token');
};

export const login = async (email, password) => {
  const res = await API.post('/auth/login', { email, password });
  return res.data;
};

export const register = async (username, email, password) => {
  const res = await API.post('/auth/register', { username, email, password });
  return res.data;
};

export const logout = async () => {
  try {
    // Call the server to blocklist the token and clear HttpOnly cookies
    await API.post('/auth/logout');
  } catch (error) {
    console.error("Logout error:", error);
  }
};

export const refreshAccessToken = async () => {
  // The refresh token is in an HttpOnly cookie, but we must provide its CSRF token
  const csrfRefresh = getCookie('csrf_refresh_token');
  if (!csrfRefresh) throw new Error('No refresh token available');
  
  const res = await API.post('/auth/refresh', {}, {
    headers: { 'X-CSRF-TOKEN': csrfRefresh }
  });
  return res.data;
};
