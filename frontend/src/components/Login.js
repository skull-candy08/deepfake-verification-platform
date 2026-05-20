import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

export default function Login() {
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <div className="dropzone" style={{ padding: 'var(--space-2xl)', minHeight: 'auto', width: '100%', maxWidth: '400px', cursor: 'default' }}>
        <div className="uploader-heading" style={{ marginBottom: 'var(--space-xl)' }}>
          <h2>Welcome Back</h2>
          <p>Login to access the verification platform</p>
        </div>

        {error && <div className="error-banner" style={{ marginBottom: 'var(--space-lg)' }}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div>
            <label style={{ display: 'block', marginBottom: 'var(--space-xs)', color: 'var(--text-secondary)' }}>Username</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{
                width: '100%', padding: '12px', borderRadius: 'var(--radius-md)', 
                background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)', outline: 'none'
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 'var(--space-xs)', color: 'var(--text-secondary)' }}>Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: '100%', padding: '12px', borderRadius: 'var(--radius-md)', 
                background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)', outline: 'none'
              }}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 'var(--space-sm)' }}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p style={{ marginTop: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>
          Don't have an account? <Link to="/register" style={{ color: 'var(--accent-cyan)' }}>Register</Link>
        </p>
      </div>
    </div>
  );
}
