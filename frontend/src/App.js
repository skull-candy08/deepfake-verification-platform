import React, { useState, useCallback, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import FileUploader from './components/FileUploader';
import AnalysisDashboard from './components/AnalysisDashboard';
import Login from './components/Login';
import Register from './components/Register';
import { AuthProvider, AuthContext } from './context/AuthContext';

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
    padding: 'var(--space-3xl) var(--space-lg)',
  },
  mainDashboard: {
    flex: 1,
    padding: 'var(--space-xl) 0 var(--space-3xl)',
  },
};

function ProtectedRoute({ children }) {
  const { token, loading } = useContext(AuthContext);
  if (loading) return <div className="spinner-overlay"><div className="spinner-ring" /></div>;
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function MainDashboard() {
  const [currentView, setCurrentView] = useState('upload');       // 'upload' | 'dashboard'
  const [analysisResults, setAnalysisResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  
  const { user, logout } = useContext(AuthContext);

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

  return (
    <>
      <Header
        showNewAnalysis={currentView === 'dashboard'}
        onNewAnalysis={handleNewAnalysis}
        user={user}
        onLogout={logout}
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
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <div style={styles.app}>
          <Routes>
            <Route path="/login" element={
              <>
                <Header />
                <Login />
              </>
            } />
            <Route path="/register" element={
              <>
                <Header />
                <Register />
              </>
            } />
            <Route path="/" element={
              <ProtectedRoute>
                <MainDashboard />
              </ProtectedRoute>
            } />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}
