import React, { useState, useEffect, useMemo } from 'react';
import ModuleScoreCard from './ModuleScoreCard';
import ReportViewer from './ReportViewer';
import { getReportUrl } from '../utils/api';

/* ─── Scoped Styles ─────────────────────────────────────────────── */
const css = `
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

/* ── Score Gauge Section ─────────────────────────────────────────── */
.gauge-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-2xl) 0 var(--space-xl);
  animation: fadeSlideUp 0.6s ease-out;
}

.gauge-wrapper {
  position: relative;
  width: 220px;
  height: 220px;
}

.gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.gauge-track {
  fill: none;
  stroke: rgba(255, 255, 255, 0.05);
  stroke-width: 10;
}

.gauge-fill {
  fill: none;
  stroke-width: 10;
  stroke-linecap: round;
  transition: stroke-dashoffset 1.8s cubic-bezier(0.34, 1.56, 0.64, 1),
              stroke 0.5s ease;
  filter: drop-shadow(0 0 8px currentColor);
}

.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.gauge-score {
  font-size: var(--font-4xl);
  font-weight: 900;
  letter-spacing: -0.03em;
  line-height: 1;
  animation: countUp 0.8s ease-out;
  font-variant-numeric: tabular-nums;
}

.gauge-label {
  font-size: var(--font-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 4px;
}

.verdict-text {
  margin-top: var(--space-lg);
  font-size: var(--font-xl);
  font-weight: 700;
  text-align: center;
}

.verdict-description {
  margin-top: var(--space-xs);
  font-size: var(--font-sm);
  color: var(--text-secondary);
  text-align: center;
  max-width: 400px;
}

/* ── Tier Badge ──────────────────────────────────────────────────── */
.tier-section {
  display: flex;
  justify-content: center;
  margin: var(--space-lg) 0;
  animation: fadeSlideUp 0.7s ease-out;
}

.tier-badge {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-xl);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border-radius: var(--radius-full);
  border: 1px solid var(--border-glass);
}

.tier-number {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: var(--font-lg);
  font-weight: 900;
  border: 2px solid;
}

.tier-info {
  display: flex;
  flex-direction: column;
}
.tier-info .tier-label {
  font-size: var(--font-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.tier-info .tier-name {
  font-size: var(--font-base);
  font-weight: 700;
}

/* ── Module Grid ─────────────────────────────────────────────────── */
.modules-section {
  margin-top: var(--space-xl);
}

.modules-section-title {
  font-size: var(--font-lg);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--space-lg);
  padding-left: var(--space-xs);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.modules-section-title::before {
  content: '';
  width: 3px;
  height: 20px;
  background: var(--accent-cyan);
  border-radius: 2px;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-lg);
}

/* ── Report Section ──────────────────────────────────────────────── */
.report-section {
  display: flex;
  justify-content: center;
  margin-top: var(--space-2xl);
  padding-bottom: var(--space-xl);
  animation: fadeSlideUp 1s ease-out;
}

/* ── Divider ─────────────────────────────────────────────────────── */
.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-glass), transparent);
  margin: var(--space-xl) 0;
}

@media (max-width: 768px) {
  .modules-grid {
    grid-template-columns: 1fr;
  }
  .gauge-wrapper {
    width: 180px;
    height: 180px;
  }
}
`;

/** Map backend tier labels to colors */
function getVerdictColor(tierLabel) {
  if (!tierLabel) return 'var(--color-warning)';
  const label = tierLabel.toLowerCase();
  if (label.includes('authentic')) return 'var(--color-success)';
  if (label.includes('suspicious')) return 'var(--color-warning)';
  if (label.includes('manipulated') || label.includes('forgery')) return 'var(--color-danger)';
  return 'var(--color-warning)';
}

/** Description text based on tier label */
function getVerdictDesc(tierLabel) {
  if (!tierLabel) return 'Analysis complete.';
  const label = tierLabel.toLowerCase();
  if (label.includes('authentic')) return 'No significant signs of manipulation detected.';
  if (label.includes('suspicious')) return 'Multiple forensic signals suggest possible manipulation.';
  if (label.includes('manipulated')) return 'Strong indicators of digital manipulation detected.';
  if (label.includes('forgery')) return 'Overwhelming evidence of deepfake or forgery.';
  return 'Analysis complete. Review module details below.';
}

/* ─── Component ─────────────────────────────────────────────────── */
export default function AnalysisDashboard({ results }) {
  const [animatedScore, setAnimatedScore] = useState(0);

  // When polling /api/status, the full result_json is inside results.results
  const finalResults = results?.results || results;

  /* Normalize overall score: fused_score is 0-1 from backend */
  const rawScore = finalResults?.fused_score ?? finalResults?.overall_score ?? finalResults?.overallScore ?? finalResults?.score ?? 0;
  const overallScore = rawScore > 1 ? rawScore / 100 : rawScore;

  /* Use backend verdict & tier as single source of truth */
  const verdictText = finalResults?.verdict || 'Analysis Complete';
  const tierData = finalResults?.tier || { label: verdictText, level: 2 };
  const tierLabel = tierData.label || verdictText;
  const tierLevel = tierData.level ?? 2;

  /* Modules */
  const modules = useMemo(() => {
    const raw = finalResults?.modules || finalResults?.module_results || [];
    return Array.isArray(raw) ? raw : Object.entries(raw).map(([name, data]) => ({
      name: data?.name || name,
      score: data?.score ?? data?.confidence ?? 0,
      details: data?.details || data?.findings || [],
      evidence: data?.evidence || data?.evidence_url || null,
    }));
  }, [finalResults]);

  /* Report URL — use report_id to build the Flask download URL */
  const reportUrl = useMemo(() => {
    const id = finalResults?.report_id || finalResults?.reportId;
    if (id) return getReportUrl(id);
    return finalResults?.report_url || finalResults?.reportUrl || null;
  }, [finalResults]);

  /* Animate gauge */
  useEffect(() => {
    const target = overallScore;
    const duration = 1800;
    const start = performance.now();

    function animate(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(eased * target);
      if (progress < 1) requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
  }, [overallScore]);

  /* SVG gauge calc */
  const gaugeRadius = 95;
  const gaugeCircumference = 2 * Math.PI * gaugeRadius;
  const gaugeOffset = gaugeCircumference - animatedScore * gaugeCircumference;
  const scoreColor = getVerdictColor(tierLabel);
  const verdictDesc = getVerdictDesc(tierLabel);

  return (
    <>
      <style>{css}</style>
      <div className="dashboard">
        {/* ── Score Gauge ────────────────────────────────────────── */}
        <section className="gauge-section">
          <div className="gauge-wrapper">
            <svg className="gauge-svg" viewBox="0 0 220 220">
              <circle className="gauge-track" cx="110" cy="110" r={gaugeRadius} />
              <circle
                className="gauge-fill"
                cx="110"
                cy="110"
                r={gaugeRadius}
                stroke={scoreColor}
                strokeDasharray={gaugeCircumference}
                strokeDashoffset={gaugeOffset}
              />
            </svg>
            <div className="gauge-center">
              <span className="gauge-score" style={{ color: scoreColor }}>
                {Math.round(animatedScore * 100)}
              </span>
              <span className="gauge-label">Risk Score</span>
            </div>
          </div>

          <div className="verdict-text" style={{ color: scoreColor }}>
            {verdictText}
          </div>
          <p className="verdict-description">{verdictDesc}</p>
        </section>

        {/* ── Tier Badge ─────────────────────────────────────────── */}
        <section className="tier-section">
          <div className={`tier-badge`}>
            <div
              className="tier-number"
              style={{ color: scoreColor, borderColor: scoreColor, background: `${scoreColor}15` }}
            >
              {tierLevel}
            </div>
            <div className="tier-info">
              <span className="tier-label">Threat Tier</span>
              <span className="tier-name" style={{ color: scoreColor }}>{tierLabel}</span>
            </div>
          </div>
        </section>

        <div className="section-divider" />

        {/* ── Module Breakdown ───────────────────────────────────── */}
        {modules.length > 0 && (
          <section className="modules-section">
            <h3 className="modules-section-title">Forensic Module Breakdown</h3>
            <div className="modules-grid stagger-children">
              {modules.map((mod, i) => (
                <ModuleScoreCard
                  key={mod.name || i}
                  moduleName={mod.name || mod.moduleName || `Module ${i + 1}`}
                  score={mod.score ?? mod.confidence ?? 0}
                  details={mod.details || mod.findings || []}
                  evidence={mod.evidence || mod.evidence_url || null}
                />
              ))}
            </div>
          </section>
        )}

        <div className="section-divider" />

        {/* ── Report Download ────────────────────────────────────── */}
        {reportUrl && (
          <section className="report-section" style={{ flexDirection: 'column', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-sm)', marginBottom: 'var(--space-sm)' }}>Full forensic analysis report with detailed findings</p>
            <ReportViewer reportUrl={reportUrl} />
          </section>
        )}
      </div>
    </>
  );
}
