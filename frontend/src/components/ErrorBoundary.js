import React from 'react';

/* ─── Scoped Styles ─────────────────────────────────────────────── */
const css = `
.error-boundary-overlay {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2xl) var(--space-lg);
}

.error-boundary-card {
  max-width: 480px;
  width: 100%;
  padding: var(--space-2xl);
  text-align: center;
  animation: fadeSlideUp 0.6s ease-out;
}

.error-boundary-icon {
  margin-bottom: var(--space-lg);
}

.error-boundary-icon svg {
  width: 64px;
  height: 64px;
  filter: drop-shadow(0 0 16px rgba(255, 159, 28, 0.35));
}

.error-boundary-title {
  font-size: var(--font-2xl);
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: var(--space-sm);
  letter-spacing: -0.02em;
}

.error-boundary-message {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-xl);
  padding: var(--space-md);
  background: rgba(255, 159, 28, 0.06);
  border: 1px solid rgba(255, 159, 28, 0.15);
  border-radius: var(--radius-md);
  word-break: break-word;
}

.error-boundary-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
}
`;

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <>
          <style>{css}</style>
          <div className="error-boundary-overlay">
            <div className="error-boundary-card glass-card">
              <div className="error-boundary-icon">
                <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="32" cy="32" r="30" stroke="url(#warnGrad)" strokeWidth="2" fill="rgba(255,159,28,0.06)" />
                  <path d="M32 18v18" stroke="#ff9f1c" strokeWidth="3" strokeLinecap="round" />
                  <circle cx="32" cy="44" r="2.5" fill="#ff9f1c" />
                  <defs>
                    <linearGradient id="warnGrad" x1="2" y1="2" x2="62" y2="62">
                      <stop offset="0%" stopColor="#ff9f1c" />
                      <stop offset="100%" stopColor="#ff3d71" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <h2 className="error-boundary-title">Something went wrong</h2>
              <div className="error-boundary-message">
                An unexpected error occurred. Our team has been notified. Please try again.
              </div>
              <button
                className="btn btn-primary error-boundary-btn"
                onClick={this.handleReset}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M13.65 2.35A8 8 0 1 0 16 8h-2a6 6 0 1 1-1.76-4.24L10 6h6V0l-2.35 2.35z" />
                </svg>
                Try Again
              </button>
            </div>
          </div>
        </>
      );
    }

    return this.props.children;
  }
}
