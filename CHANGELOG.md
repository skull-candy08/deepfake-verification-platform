# Changelog

All notable changes to the Deepfake Verification Platform are documented here.

## [2.0.0] — 2026-06-06

### 🔴 Security Fixes (Phase 1)

#### Credential Removal
- **Removed hardcoded Cloudinary API credentials** from `app.py` (cloud_name, api_key, api_secret) — [CRITICAL]
- Removed all Cloudinary imports (`import cloudinary`, `import cloudinary.uploader`, `from cloudinary.utils`)
- Removed `cloudinary>=1.41.0` from `requirements.txt`
- Created `.env.example` documenting all required environment variables
- All secrets now loaded exclusively from environment variables

#### JWT Authentication
- **NEW** `backend/extensions.py` — Centralized Flask extension instances (SQLAlchemy, JWTManager, Bcrypt, Limiter)
- **NEW** `backend/auth.py` — Auth blueprint with `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me` endpoints
- **NEW** `backend/models.py` — SQLAlchemy models: `User`, `Upload`, `Analysis`
- All `/api/*` endpoints now require `@jwt_required()` decorator
- Ownership verification on all data access (uploads, analyses, reports)

#### Traceback Leakage
- Replaced raw `traceback.format_exc()` exposure with generic `"An internal error occurred during analysis."` message
- Full tracebacks now logged server-side only via `logger.exception()`
- Added global error handlers: `@app.errorhandler(404)`, `@app.errorhandler(500)`, `@app.errorhandler(Exception)`

#### Path Traversal Prevention
- Report ID validated with strict regex: `^[a-f0-9]{32}$`
- `os.path.realpath()` check ensures file path stays within `OUTPUT_DIR`
- Ownership check prevents unauthorized report downloads

#### CORS Restriction
- Changed `CORS(app)` (wildcard) to `CORS(app, origins=config.CORS_ORIGINS)` — configurable via `CORS_ORIGINS` env var

#### Rate Limiting
- Added `Flask-Limiter` with per-endpoint limits:
  - `/auth/register`: 5/hour
  - `/auth/login`: 10/minute
  - `/api/upload`: 20/hour
  - `/api/analyze`: 10/hour
  - `/api/report`: 30/minute

#### MIME Type Validation
- Added `python-magic-bin` for magic-byte file type verification
- Uploaded files are validated: extension must match actual file content
- Mismatched files are rejected and deleted

---

### 🟠 Bug Fixes (Phase 2)

- **Fixed `file_id` always returning `null`**: Removed broken `_uploads_file_id_for()` function. `file_id` now flows directly from the Upload database record through the pipeline to the report generator.
- **Fixed original filename missing from reports**: `original_filename` now passed through the analysis payload to `generator.py`.
- **Fixed GIF upload mismatch**: Added `'gif'` to `ALLOWED_EXTENSIONS['image']` in `config.py` — frontend and backend now accept the same file types.
- **Removed dead code**:
  - `import requests` (unused) from `app.py`
  - `import tempfile` (unused) from `app.py`
  - `cloudinary.config()` block from `app.py`
  - `_uploads_file_id_for()` (always returned None) from `app.py`
  - `getBadgeClass()` (never called) from `AnalysisDashboard.js`
  - `getScoreColor()` (replaced by `getVerdictColor()`) from `AnalysisDashboard.js`
- **Fixed verdict/tier mismatch**: Frontend no longer reimplements verdict logic with different thresholds. Uses backend's `verdict` and `tier` from API response as single source of truth.

---

### 🟢 Architecture Improvements (Phase 3)

#### Database Persistence
- Replaced in-memory `_uploads = {}` and `_analyses = {}` dicts with SQLAlchemy models
- All data persists across server restarts
- Full analysis results stored as JSON in `Analysis.result_json` column

#### Background Processing
- Analysis pipeline now runs in a background `threading.Thread`
- `/api/analyze` returns `202 Accepted` immediately with `analysis_id`
- Frontend polls `/api/status/<analysis_id>` every 2 seconds until completion

---

### 🔵 Frontend Fixes (Phase 4)

- **NEW** `ErrorBoundary.js` — React Error Boundary class component prevents white-screen crashes
- **NEW** `AuthPage.js` — Premium glassmorphic login/register page matching existing design
- **NEW** `auth.js` — Auth utility module (login, register, logout, token management, JWT expiry check)
- **Modified** `api.js` — Added Axios request/response interceptors for automatic JWT attachment and 401 refresh token flow
- **Modified** `App.js` — Wrapped app in `<ErrorBoundary>`, added auth gate showing `<AuthPage>` when not logged in
- **Modified** `Header.js` — Added logout button
- **Modified** `FileUploader.js` — Updated to handle async analysis polling via `getAnalysisStatus()`
- **Modified** `AnalysisDashboard.js` — Removed duplicate verdict/tier logic, uses backend values

---

### 🟡 Storage & Cleanup (Phase 5)

- **NEW** `backend/cleanup.py` — Cleanup service with configurable retention
  - `cleanup_old_files(directory, max_age_hours)` — removes files older than retention period
  - `run_cleanup()` — runs on both uploads and outputs directories
  - Safe deletion with logging, removes empty directories

---

### ⚙️ DevOps & Hardening (Phase 6)

- **Disabled debug mode**: Changed `app.run(debug=True)` to `app.run(debug=os.environ.get('FLASK_ENV') == 'development')` — defaults to production
- **Updated `config.py`**: Added `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `CLEANUP_MAX_AGE_HOURS` from env vars with safe defaults
- **Updated `.gitignore`**: Added `*.db`, `*.sqlite3`, `instance/`, `outputs/`, `*.pyc`

---

### Files Changed Summary

| Action | File | 
|--------|------|
| MODIFIED | `backend/app.py` |
| MODIFIED | `backend/config.py` |
| MODIFIED | `backend/requirements.txt` |
| MODIFIED | `.gitignore` |
| MODIFIED | `frontend/src/App.js` |
| MODIFIED | `frontend/src/utils/api.js` |
| MODIFIED | `frontend/src/components/AnalysisDashboard.js` |
| MODIFIED | `frontend/src/components/FileUploader.js` |
| MODIFIED | `frontend/src/components/Header.js` |
| NEW | `.env.example` |
| NEW | `backend/extensions.py` |
| NEW | `backend/models.py` |
| NEW | `backend/auth.py` |
| NEW | `backend/cleanup.py` |
| NEW | `frontend/src/components/ErrorBoundary.js` |
| NEW | `frontend/src/components/AuthPage.js` |
| NEW | `frontend/src/utils/auth.js` |
| NEW | `CHANGELOG.md` |
