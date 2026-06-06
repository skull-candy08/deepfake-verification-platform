import React, { useState, useCallback } from 'react';
import Header from './components/Header';
import FileUploader from './components/FileUploader';
import AnalysisDashboard from './components/AnalysisDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import AuthPage from './components/AuthPage';
import { isAuthenticated, logout } from './utils/auth';

/* ─── Inline Styles (component-scoped) ──────────────────────────── */
const styles = {
  app: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  mainUpload: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 'var(--space-2xl) var(--space-lg)',
  },
  mainDashboard: {
    flex: 1,
    padding: 'var(--space-xl) 0 var(--space-3xl)',
  },
};

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [currentView, setCurrentView] = useState('upload');
  const [analysisResults, setAnalysisResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);

  /* ── Auth Handlers ─────────────────────────────────────────────── */
  const handleAuth = useCallback(() => {
    setAuthed(true);
  }, []);

  const handleLogout = useCallback(() => {
    logout();
    setAuthed(false);
    setCurrentView('upload');
    setAnalysisResults(null);
  }, []);

  /* ── Handlers ──────────────────────────────────────────────────── */
  const handleAnalysisStart = useCallback(() => {
    setIsAnalyzing(true);
    setError(null);
  }, []);

  const handleUploadProgress = useCallback((pct) => {
    setUploadProgress(pct);
  }, []);

  const handleAnalysisComplete = useCallback((results) => {
    setAnalysisResults(results);
    setIsAnalyzing(false);
    setUploadProgress(0);
    setCurrentView('dashboard');
  }, []);

  const handleAnalysisError = useCallback((err) => {
    setError(err.message || 'Analysis failed. Please try again.');
    setIsAnalyzing(false);
    setUploadProgress(0);
  }, []);

  const handleNewAnalysis = useCallback(() => {
    setCurrentView('upload');
    setAnalysisResults(null);
    setError(null);
    setUploadProgress(0);
  }, []);

  const dismissError = useCallback(() => setError(null), []);

  /* ── Render ────────────────────────────────────────────────────── */
  if (!authed) {
    return (
      <ErrorBoundary>
        <AuthPage onAuth={handleAuth} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div style={styles.app}>
        <Header
          showNewAnalysis={currentView === 'dashboard'}
          onNewAnalysis={handleNewAnalysis}
          onLogout={handleLogout}
        />

        {/* Error banner */}
        {error && (
          <div className="container" style={{ marginTop: 'var(--space-md)' }}>
            <div className="error-banner">
              <span style={{ fontSize: '1.2rem' }}>⚠</span>
              <span>{error}</span>
              <button onClick={dismissError} aria-label="Dismiss error">✕</button>
            </div>
          </div>
        )}

        {/* Analyzing overlay */}
        {isAnalyzing && (
          <div className="spinner-overlay">
            <div className="spinner-ring" />
            <p className="spinner-text">
              {uploadProgress > 0 && uploadProgress < 100
                ? `Uploading… ${uploadProgress}%`
                : 'Running forensic analysis…'}
            </p>
          </div>
        )}

        {/* Views */}
        {currentView === 'upload' && (
          <main style={styles.mainUpload} className="animate-in">
            <FileUploader
              onAnalysisStart={handleAnalysisStart}
              onUploadProgress={handleUploadProgress}
              onAnalysisComplete={handleAnalysisComplete}
              onAnalysisError={handleAnalysisError}
            />
          </main>
        )}

        {currentView === 'dashboard' && analysisResults && (
          <main style={styles.mainDashboard} className="animate-in">
            <AnalysisDashboard results={analysisResults} />
          </main>
        )}
      </div>
    </ErrorBoundary>
  );
}
