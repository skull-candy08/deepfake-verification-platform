import React from 'react';

const css = `
.report-viewer {
  display: inline-flex;
}

.report-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 14px 32px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(124, 92, 255, 0.1) 100%);
  border: 1px solid var(--border-active);
  border-radius: var(--radius-md);
  color: var(--accent-cyan);
  font-family: var(--font-family);
  font-size: var(--font-base);
  font-weight: 600;
  cursor: pointer;
  transition:
    background var(--transition-base),
    box-shadow var(--transition-base),
    transform var(--transition-fast);
  text-decoration: none;
  letter-spacing: 0.02em;
}
.report-btn:hover {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.16) 0%, rgba(124, 92, 255, 0.16) 100%);
  box-shadow: var(--shadow-glow-cyan);
  transform: translateY(-2px);
}
.report-btn:active {
  transform: scale(0.97);
}

.report-btn svg {
  flex-shrink: 0;
}
`;

export default function ReportViewer({ reportUrl }) {
  if (!reportUrl) return null;

  return (
    <>
      <style>{css}</style>
      <div className="report-viewer">
        <a
          href={reportUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="report-btn"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414a1 1 0 00-.293-.707l-3.414-3.414A1 1 0 0011.586 3H6zm0 1h5v3a1 1 0 001 1h3v9a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1zm6 .707L14.293 6H12V3.707zM7 10v1h6v-1H7zm0 3v1h4v-1H7z"
              fill="currentColor"
            />
          </svg>
          Download Full Report
        </a>
      </div>
    </>
  );
}
