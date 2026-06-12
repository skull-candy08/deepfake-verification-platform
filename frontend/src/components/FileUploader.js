import React, { useState, useRef, useCallback } from 'react';
import { uploadMedia, analyzeMedia, getAnalysisStatus } from '../utils/api';

/* ─── Scoped Styles ─────────────────────────────────────────────── */
const css = `
.uploader-wrapper {
  width: 100%;
  max-width: 680px;
  animation: fadeSlideUp 0.6s ease-out;
}

.hero-section {
  text-align: center;
  margin-bottom: var(--space-2xl);
}
.hero-title {
  font-size: var(--font-3xl);
  font-weight: 900;
  letter-spacing: -0.03em;
  margin-bottom: var(--space-sm);
  background: linear-gradient(135deg, var(--accent-cyan) 0%, #33ddff 40%, var(--accent-purple) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-desc {
  color: var(--text-secondary);
  font-size: var(--font-base);
  line-height: 1.6;
  max-width: 520px;
  margin: 0 auto var(--space-lg);
}
.hero-features {
  display: flex;
  justify-content: center;
  gap: var(--space-lg);
  flex-wrap: wrap;
}
.hero-feature {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-full);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.hero-feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-cyan);
  flex-shrink: 0;
}

.uploader-heading {
  text-align: center;
  margin-bottom: var(--space-xl);
}
.uploader-heading h2 {
  font-size: var(--font-2xl);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: var(--space-xs);
}
.uploader-heading p {
  color: var(--text-secondary);
  font-size: var(--font-base);
}

/* Dropzone */
.dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  padding: var(--space-2xl) var(--space-xl);
  border: 2px dashed rgba(0, 212, 255, 0.25);
  border-radius: var(--radius-xl);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  cursor: pointer;
  transition:
    border-color var(--transition-base),
    background var(--transition-base),
    box-shadow var(--transition-base);
  overflow: hidden;
}

.dropzone::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-xl);
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), var(--accent-cyan));
  background-size: 300% 300%;
  z-index: -1;
  opacity: 0;
  transition: opacity var(--transition-base);
  animation: gradientShift 4s ease infinite;
}

.dropzone:hover {
  border-color: rgba(0, 212, 255, 0.5);
  background: rgba(0, 212, 255, 0.04);
  box-shadow: var(--shadow-glow-cyan);
}
.dropzone:hover::before {
  opacity: 0.15;
}

.dropzone.drag-over {
  border-color: var(--accent-cyan);
  background: rgba(0, 212, 255, 0.06);
  box-shadow: var(--shadow-glow-cyan-strong);
}
.dropzone.drag-over::before {
  opacity: 0.25;
}

.dropzone-icon {
  margin-bottom: var(--space-lg);
  animation: float 3s ease-in-out infinite;
}

.dropzone-icon svg {
  width: 72px;
  height: 72px;
  filter: drop-shadow(0 0 12px rgba(0, 212, 255, 0.3));
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-8px); }
}

.dropzone-text {
  text-align: center;
}
.dropzone-text .primary-text {
  font-size: var(--font-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}
.dropzone-text .secondary-text {
  font-size: var(--font-sm);
  color: var(--text-muted);
}
.dropzone-text .browse-link {
  color: var(--accent-cyan);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.formats {
  margin-top: var(--space-lg);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  justify-content: center;
}
.format-tag {
  padding: 4px 10px;
  font-size: var(--font-xs);
  font-weight: 500;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-full);
}

/* File preview */
.file-preview {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  margin-top: var(--space-lg);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  animation: fadeSlideUp 0.3s ease-out;
}

.file-thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.15);
  flex-shrink: 0;
}
.file-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.file-thumb .icon-text {
  font-size: 1.5rem;
}

.file-info {
  flex: 1;
  min-width: 0;
}
.file-info .file-name {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-info .file-size {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

.file-remove {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px;
  transition: color var(--transition-fast);
}
.file-remove:hover {
  color: var(--color-danger);
}

/* Analyze button area */
.analyze-actions {
  margin-top: var(--space-xl);
  text-align: center;
  animation: fadeSlideUp 0.4s ease-out;
}

/* Progress ring */
.progress-ring-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: var(--space-xl);
  animation: fadeIn 0.3s ease;
}
.progress-ring-container svg {
  filter: drop-shadow(0 0 8px rgba(0, 212, 255, 0.3));
}
.progress-ring-container p {
  margin-top: var(--space-sm);
  font-size: var(--font-sm);
  color: var(--text-secondary);
}

@media (max-width: 480px) {
  .dropzone { min-height: 220px; padding: var(--space-xl) var(--space-md); }
  .dropzone-icon svg { width: 56px; height: 56px; }
}
`;

/* ─── Helpers ───────────────────────────────────────────────────── */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function getFileIcon(type) {
  if (type.startsWith('image')) return '🖼️';
  if (type.startsWith('video')) return '🎬';
  if (type.startsWith('audio')) return '🔊';
  return '📄';
}

const ACCEPTED = '.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.mkv,.webm,.mp3,.wav,.flac,.ogg';

/* ─── Component ─────────────────────────────────────────────────── */
export default function FileUploader({
  onAnalysisStart,
  onUploadProgress,
  onAnalysisComplete,
  onAnalysisError,
}) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef();

  /* ── File selection ────────────────────────────────────────────── */
  const handleFile = useCallback((selected) => {
    if (!selected) return;
    setFile(selected);

    if (selected.type.startsWith('image')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(selected);
    } else {
      setPreview(null);
    }
  }, []);

  const onInputChange = (e) => handleFile(e.target.files[0]);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragOver(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) handleFile(dropped);
    },
    [handleFile]
  );

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  const onDragLeave = () => setIsDragOver(false);

  const clearFile = () => {
    setFile(null);
    setPreview(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  /* ── Analyze ───────────────────────────────────────────────────── */
  const handleAnalyze = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    onAnalysisStart();

    try {
      /* Step 1: Upload */
      const uploadRes = await uploadMedia(file, (pct) => {
        setProgress(pct);
        onUploadProgress(pct);
      });

      /* Step 2: Trigger analysis (returns immediately with analysis_id) */
      setProgress(100);
      onUploadProgress(100);

      const fileId = uploadRes.file_id || uploadRes.fileId || uploadRes.id;
      const analyzeRes = await analyzeMedia(fileId);

      /* Step 3: Poll for completion */
      const analysisId = analyzeRes.analysis_id || analyzeRes.analysisId;
      if (!analysisId) {
        // Backend returned results synchronously (fallback)
        onAnalysisComplete(analyzeRes);
        return;
      }

      const pollInterval = 2000; // 2 seconds
      const maxAttempts = 120;   // 4 minutes max
      let attempts = 0;

      while (attempts < maxAttempts) {
        attempts++;
        const statusRes = await getAnalysisStatus(analysisId);

        if (statusRes.status === 'completed') {
          onAnalysisComplete(statusRes);
          return;
        }

        if (statusRes.status === 'failed') {
          throw new Error(statusRes.error || 'Analysis failed on the server.');
        }

        await new Promise((resolve) => setTimeout(resolve, pollInterval));
      }

      throw new Error('Analysis timed out. Please try again.');
    } catch (err) {
      onAnalysisError(err);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  }, [file, onAnalysisStart, onUploadProgress, onAnalysisComplete, onAnalysisError]);

  /* ── Progress ring SVG ─────────────────────────────────────────── */
  const ringSize = 80;
  const strokeWidth = 4;
  const radius = (ringSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const ringOffset = circumference - (progress / 100) * circumference;

  /* ── Render ────────────────────────────────────────────────────── */
  return (
    <>
      <style>{css}</style>
      <div className="uploader-wrapper">
        {/* Hero Section */}
        <div className="hero-section">
          <h1 className="hero-title">Detect Deepfakes with Forensic Precision</h1>
          <p className="hero-desc">
            Our platform uses explainable forensic techniques — not black-box AI — to analyze images, videos, and audio for signs of manipulation or AI generation.
          </p>
          <div className="hero-features">
            <span className="hero-feature"><span className="hero-feature-dot" />ELA Analysis</span>
            <span className="hero-feature"><span className="hero-feature-dot" />Metadata Inspection</span>
            <span className="hero-feature"><span className="hero-feature-dot" />Compression Forensics</span>
            <span className="hero-feature"><span className="hero-feature-dot" />PDF Reports</span>
          </div>
        </div>

        <div className="uploader-heading">
          <h2>Verify Your Media</h2>
          <p>Upload an image, video, or audio file for forensic analysis</p>
        </div>

        {/* Dropzone */}
        <div
          className={`dropzone${isDragOver ? ' drag-over' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          role="button"
          tabIndex={0}
          aria-label="Upload media file"
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            onChange={onInputChange}
            style={{ display: 'none' }}
          />

          {/* Upload icon */}
          <div className="dropzone-icon">
            <svg viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="4" width="64" height="64" rx="16" stroke="url(#uploadGrad)" strokeWidth="1.5" fill="rgba(0,212,255,0.03)"/>
              <path d="M36 46V26" stroke="#00d4ff" strokeWidth="2.5" strokeLinecap="round"/>
              <path d="M28 34l8-8 8 8" stroke="#00d4ff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M22 44h28" stroke="rgba(0,212,255,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
              <defs>
                <linearGradient id="uploadGrad" x1="4" y1="4" x2="68" y2="68">
                  <stop offset="0%" stopColor="rgba(0,212,255,0.4)"/>
                  <stop offset="100%" stopColor="rgba(124,92,255,0.3)"/>
                </linearGradient>
              </defs>
            </svg>
          </div>

          <div className="dropzone-text">
            <p className="primary-text">Drop your media file here</p>
            <p className="secondary-text">
              or <span className="browse-link">click to browse</span>
            </p>
          </div>

          <div className="formats">
            {['JPG', 'PNG', 'GIF', 'WEBP', 'MP4', 'AVI', 'MOV', 'MP3', 'WAV'].map((fmt) => (
              <span className="format-tag" key={fmt}>{fmt}</span>
            ))}
          </div>
        </div>

        {/* File preview */}
        {file && !uploading && (
          <div className="file-preview">
            <div className="file-thumb">
              {preview ? (
                <img src={preview} alt="Preview" />
              ) : (
                <span className="icon-text">{getFileIcon(file.type)}</span>
              )}
            </div>
            <div className="file-info">
              <div className="file-name">{file.name}</div>
              <div className="file-size">{formatFileSize(file.size)}</div>
            </div>
            <button className="file-remove" onClick={(e) => { e.stopPropagation(); clearFile(); }} aria-label="Remove file">
              ✕
            </button>
          </div>
        )}

        {/* Progress ring while uploading */}
        {uploading && (
          <div className="progress-ring-container">
            <svg width={ringSize} height={ringSize}>
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={radius}
                fill="none"
                stroke="rgba(0,212,255,0.1)"
                strokeWidth={strokeWidth}
              />
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={radius}
                fill="none"
                stroke="var(--accent-cyan)"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={ringOffset}
                transform={`rotate(-90 ${ringSize / 2} ${ringSize / 2})`}
                style={{ transition: 'stroke-dashoffset 0.3s ease' }}
              />
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="central"
                fill="var(--accent-cyan)"
                fontSize="14"
                fontWeight="700"
                fontFamily="var(--font-family)"
              >
                {progress}%
              </text>
            </svg>
            <p>{progress < 100 ? 'Uploading…' : 'Analyzing…'}</p>
          </div>
        )}

        {/* Analyze button */}
        {file && !uploading && (
          <div className="analyze-actions">
            <button className="btn btn-primary btn-lg" onClick={handleAnalyze}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{ marginRight: 4 }}>
                <path d="M9 2a7 7 0 105.468 11.37l3.581 3.581a1 1 0 001.414-1.414l-3.581-3.581A7 7 0 009 2zm0 2a5 5 0 110 10A5 5 0 019 4z" fill="currentColor"/>
              </svg>
              Start Analysis
            </button>
          </div>
        )}
      </div>
    </>
  );
}
