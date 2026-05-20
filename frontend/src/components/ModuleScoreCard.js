import React, { useState, useEffect } from 'react';

/* ─── Scoped Styles ─────────────────────────────────────────────── */
const css = `
.module-card {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.module-card-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.module-card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.module-card-title {
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}

.module-card-score-value {
  font-size: var(--font-lg);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

/* Score bar */
.module-score-bar-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.module-score-labels {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-xs);
  color: var(--text-muted);
}

/* Findings */
.module-findings {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: var(--space-xs);
}

.module-findings li {
  position: relative;
  padding-left: 16px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}
.module-findings li::before {
  content: '›';
  position: absolute;
  left: 0;
  color: var(--accent-cyan);
  font-weight: 700;
}

/* Evidence thumbnail */
.module-evidence-thumb {
  margin-top: var(--space-xs);
  width: 100%;
  max-height: 120px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}
.module-evidence-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
`;

/* ─── Icon map ──────────────────────────────────────────────────── */
const MODULE_ICONS = {
  metadata:    '🔍',
  compression: '📦',
  ela:         '🔬',
  frame:       '🎬',
  audio:       '🔊',
  noise:       '📊',
  face:        '👤',
  frequency:   '〰️',
  default:     '🧪',
};

function getIcon(moduleName) {
  const lower = (moduleName || '').toLowerCase();
  for (const [key, icon] of Object.entries(MODULE_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return MODULE_ICONS.default;
}

function scoreColor(score) {
  if (score < 40) return 'var(--color-success)';
  if (score < 70) return 'var(--color-warning)';
  return 'var(--color-danger)';
}

function scoreBarClass(score) {
  if (score < 40) return 'score-green';
  if (score < 70) return 'score-amber';
  return 'score-red';
}

/* ─── Component ─────────────────────────────────────────────────── */
export default function ModuleScoreCard({ moduleName, score, details, evidence }) {
  const [animatedWidth, setAnimatedWidth] = useState(0);
  const displayScore = Math.round(score * 100) / 100;
  const pctScore = Math.min(100, Math.max(0, score > 1 ? score : score * 100));

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedWidth(pctScore), 100);
    return () => clearTimeout(timer);
  }, [pctScore]);

  const findings = Array.isArray(details)
    ? details
    : typeof details === 'object' && details !== null
      ? Object.entries(details).map(([k, v]) => `${k}: ${v}`)
      : details
        ? [String(details)]
        : [];

  return (
    <>
      <style>{css}</style>
      <div className="glass-card module-card">
        {/* Header */}
        <div className="module-card-header">
          <div className="module-card-icon">{getIcon(moduleName)}</div>
          <span className="module-card-title">{moduleName}</span>
          <span className="module-card-score-value" style={{ color: scoreColor(pctScore) }}>
            {pctScore.toFixed(1)}%
          </span>
        </div>

        {/* Score bar */}
        <div className="module-score-bar-wrapper">
          <div className="score-bar-track">
            <div
              className={`score-bar-fill ${scoreBarClass(pctScore)}`}
              style={{ width: `${animatedWidth}%` }}
            />
          </div>
          <div className="module-score-labels">
            <span>Authentic</span>
            <span>Manipulated</span>
          </div>
        </div>

        {/* Findings */}
        {findings.length > 0 && (
          <ul className="module-findings">
            {findings.slice(0, 5).map((finding, i) => (
              <li key={i}>{finding}</li>
            ))}
          </ul>
        )}

        {/* Evidence thumbnail */}
        {evidence && (
          <div className="module-evidence-thumb">
            <img src={evidence} alt={`${moduleName} evidence`} loading="lazy" />
          </div>
        )}
      </div>
    </>
  );
}
