import React from 'react';

/* ─── Scoped Styles ─────────────────────────────────────────────── */
const css = `
.header {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  background: rgba(10, 14, 39, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-glass);
  padding: 0 var(--space-lg);
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.header-logo {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
}

.header-logo svg {
  width: 44px;
  height: 44px;
  filter: drop-shadow(0 0 8px rgba(0, 212, 255, 0.4));
}

.header-title {
  font-size: var(--font-xl);
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, var(--accent-cyan) 0%, #33ddff 50%, var(--accent-purple) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: none;
}

.header-subtitle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 2px;
}

.header-gradient-line {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--accent-cyan) 20%,
    var(--accent-purple) 50%,
    var(--accent-cyan) 80%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: headerGradient 4s ease infinite;
  opacity: 0.6;
}

@keyframes headerGradient {
  0%, 100% { background-position: 0% 0%; }
  50%      { background-position: 100% 0%; }
}

@media (max-width: 480px) {
  .header-subtitle { display: none; }
  .header-title { font-size: var(--font-lg); }
}
`;

export default function Header({ showNewAnalysis, onNewAnalysis, user, onLogout }) {
  return (
    <>
      <style>{css}</style>
      <header className="header">
        <div className="header-inner">
          {/* Brand */}
          <div className="header-brand">
            <div className="header-logo">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                {/* Shield shape */}
                <path
                  d="M24 4L6 12v12c0 11.1 7.7 21.5 18 24 10.3-2.5 18-12.9 18-24V12L24 4z"
                  fill="url(#shieldGrad)"
                  stroke="url(#shieldStroke)"
                  strokeWidth="1.5"
                  opacity="0.9"
                />
                {/* Scan lines */}
                <path d="M16 20h16" stroke="#00d4ff" strokeWidth="1.5" strokeLinecap="round" opacity="0.7"/>
                <path d="M14 24h20" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round"/>
                <path d="M16 28h16" stroke="#00d4ff" strokeWidth="1.5" strokeLinecap="round" opacity="0.7"/>
                {/* Center dot */}
                <circle cx="24" cy="24" r="2.5" fill="#00d4ff"/>
                {/* Checkmark */}
                <path d="M19 24l3.5 3.5L29 21" stroke="#00e676" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.85"/>
                <defs>
                  <linearGradient id="shieldGrad" x1="24" y1="4" x2="24" y2="48">
                    <stop offset="0%" stopColor="rgba(0,212,255,0.12)"/>
                    <stop offset="100%" stopColor="rgba(124,92,255,0.08)"/>
                  </linearGradient>
                  <linearGradient id="shieldStroke" x1="6" y1="4" x2="42" y2="48">
                    <stop offset="0%" stopColor="#00d4ff"/>
                    <stop offset="100%" stopColor="#7c5cff"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <div>
              <div className="header-title">DeepScan</div>
              <div className="header-subtitle">Forensic Media Authentication</div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
            {showNewAnalysis && (
              <button className="btn btn-secondary btn-sm" onClick={onNewAnalysis}>
                <span style={{ fontSize: '1.1em' }}>⊕</span>
                New Analysis
              </button>
            )}
            {user && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-sm)' }}>
                  {user.username}
                </span>
                <button className="btn btn-secondary btn-sm" onClick={onLogout}>
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="header-gradient-line" />
      </header>
    </>
  );
}
