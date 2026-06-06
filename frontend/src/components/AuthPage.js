import React, { useState } from 'react';
import { login, register } from '../utils/auth';

/* ─── Scoped Styles ─────────────────────────────────────────────── */
const css = `
.auth-overlay {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2xl) var(--space-lg);
  position: relative;
}

.auth-card {
  width: 100%;
  max-width: 440px;
  padding: var(--space-2xl) var(--space-2xl) var(--space-xl);
  animation: authSlideUp 0.7s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes authSlideUp {
  from {
    opacity: 0;
    transform: translateY(40px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ── Brand ───────────────────────────────────────────────────────── */
.auth-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: var(--space-xl);
}

.auth-logo {
  width: 64px;
  height: 64px;
  margin-bottom: var(--space-md);
  filter: drop-shadow(0 0 16px rgba(0, 212, 255, 0.4));
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-6px); }
}

.auth-title {
  font-size: var(--font-2xl);
  font-weight: 900;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, var(--accent-cyan) 0%, #33ddff 50%, var(--accent-purple) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.auth-subtitle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-top: 4px;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
.auth-tabs {
  display: flex;
  margin-bottom: var(--space-xl);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
  padding: 4px;
  border: 1px solid var(--border-glass);
}

.auth-tab {
  flex: 1;
  padding: 10px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-family: var(--font-family);
  font-size: var(--font-sm);
  font-weight: 600;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  letter-spacing: 0.02em;
}

.auth-tab:hover {
  color: var(--text-secondary);
}

.auth-tab.active {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(124, 92, 255, 0.1) 100%);
  color: var(--accent-cyan);
  box-shadow: 0 2px 8px rgba(0, 212, 255, 0.1);
}

/* ── Form ────────────────────────────────────────────────────────── */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.auth-field {
  position: relative;
}

.auth-field label {
  display: block;
  font-size: var(--font-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}

.auth-field input {
  width: 100%;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-family: var(--font-family);
  font-size: var(--font-base);
  outline: none;
  transition: border-color var(--transition-base), box-shadow var(--transition-base),
              background var(--transition-base);
}

.auth-field input::placeholder {
  color: var(--text-muted);
}

.auth-field input:focus {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1), var(--shadow-glow-cyan);
  background: rgba(0, 212, 255, 0.02);
}

/* ── Error ────────────────────────────────────────────────────────── */
.auth-error {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: rgba(255, 61, 113, 0.08);
  border: 1px solid rgba(255, 61, 113, 0.2);
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: var(--font-sm);
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Submit ───────────────────────────────────────────────────────── */
.auth-submit {
  margin-top: var(--space-sm);
  width: 100%;
  padding: 16px;
  font-size: var(--font-base);
  font-weight: 700;
  letter-spacing: 0.03em;
  position: relative;
  overflow: hidden;
}

.auth-submit.loading {
  pointer-events: none;
  opacity: 0.7;
}

.auth-submit .btn-spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(10, 14, 39, 0.2);
  border-top-color: var(--text-inverse);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-right: var(--space-sm);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Footer ──────────────────────────────────────────────────────── */
.auth-footer {
  margin-top: var(--space-lg);
  text-align: center;
  font-size: var(--font-xs);
  color: var(--text-muted);
}

.auth-footer a {
  color: var(--accent-cyan);
  font-weight: 600;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.auth-footer a:hover {
  color: #33ddff;
}

/* ── Decorative ──────────────────────────────────────────────────── */
.auth-glow-orb {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(80px);
  opacity: 0.4;
  z-index: -1;
}

.auth-glow-orb.cyan {
  width: 300px;
  height: 300px;
  background: rgba(0, 212, 255, 0.2);
  top: 10%;
  left: 10%;
  animation: orbDrift1 12s ease-in-out infinite alternate;
}

.auth-glow-orb.purple {
  width: 250px;
  height: 250px;
  background: rgba(124, 92, 255, 0.2);
  bottom: 15%;
  right: 10%;
  animation: orbDrift2 15s ease-in-out infinite alternate;
}

@keyframes orbDrift1 {
  from { transform: translate(0, 0); }
  to   { transform: translate(40px, -30px); }
}

@keyframes orbDrift2 {
  from { transform: translate(0, 0); }
  to   { transform: translate(-30px, 20px); }
}

@media (max-width: 480px) {
  .auth-card {
    padding: var(--space-xl) var(--space-lg) var(--space-lg);
  }
  .auth-logo {
    width: 48px;
    height: 48px;
  }
  .auth-title {
    font-size: var(--font-xl);
  }
}
`;

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(username, email, password);
      }
      onAuth();
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Authentication failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setError('');
  };

  return (
    <>
      <style>{css}</style>

      {/* Decorative background orbs */}
      <div className="auth-glow-orb cyan" />
      <div className="auth-glow-orb purple" />

      <div className="auth-overlay">
        <div className="auth-card glass-card">
          {/* Brand */}
          <div className="auth-brand">
            <svg className="auth-logo" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M24 4L6 12v12c0 11.1 7.7 21.5 18 24 10.3-2.5 18-12.9 18-24V12L24 4z"
                fill="url(#authShieldGrad)"
                stroke="url(#authShieldStroke)"
                strokeWidth="1.5"
                opacity="0.9"
              />
              <path d="M16 20h16" stroke="#00d4ff" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
              <path d="M14 24h20" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" />
              <path d="M16 28h16" stroke="#00d4ff" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
              <circle cx="24" cy="24" r="2.5" fill="#00d4ff" />
              <path d="M19 24l3.5 3.5L29 21" stroke="#00e676" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />
              <defs>
                <linearGradient id="authShieldGrad" x1="24" y1="4" x2="24" y2="48">
                  <stop offset="0%" stopColor="rgba(0,212,255,0.12)" />
                  <stop offset="100%" stopColor="rgba(124,92,255,0.08)" />
                </linearGradient>
                <linearGradient id="authShieldStroke" x1="6" y1="4" x2="42" y2="48">
                  <stop offset="0%" stopColor="#00d4ff" />
                  <stop offset="100%" stopColor="#7c5cff" />
                </linearGradient>
              </defs>
            </svg>
            <h1 className="auth-title">DeepScan</h1>
            <p className="auth-subtitle">Forensic Media Authentication</p>
          </div>

          {/* Tabs */}
          <div className="auth-tabs">
            <button
              className={`auth-tab${mode === 'login' ? ' active' : ''}`}
              onClick={() => switchMode('login')}
              type="button"
            >
              Sign In
            </button>
            <button
              className={`auth-tab${mode === 'register' ? ' active' : ''}`}
              onClick={() => switchMode('register')}
              type="button"
            >
              Create Account
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="auth-error">
              <span style={{ fontSize: '1rem' }}>⚠</span>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form className="auth-form" onSubmit={handleSubmit}>
            {mode === 'register' && (
              <div className="auth-field">
                <label htmlFor="auth-username">Username</label>
                <input
                  id="auth-username"
                  type="text"
                  placeholder="Choose a username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>
            )}

            <div className="auth-field">
              <label htmlFor="auth-email">Email</label>
              <input
                id="auth-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="auth-field">
              <label htmlFor="auth-password">Password</label>
              <input
                id="auth-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={6}
              />
            </div>

            <button
              type="submit"
              className={`btn btn-primary auth-submit${loading ? ' loading' : ''}`}
              disabled={loading}
            >
              {loading && <span className="btn-spinner" />}
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          {/* Footer */}
          <div className="auth-footer">
            {mode === 'login' ? (
              <p>
                Don't have an account?{' '}
                <a onClick={() => switchMode('register')} role="button" tabIndex={0}>
                  Create one
                </a>
              </p>
            ) : (
              <p>
                Already have an account?{' '}
                <a onClick={() => switchMode('login')} role="button" tabIndex={0}>
                  Sign in
                </a>
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
