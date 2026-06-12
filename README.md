# DeepScan — Deepfake Verification Platform

An explainable, forensic-based media authentication system that analyzes images, videos, and audio to determine authenticity using transparent forensic signals and probabilistic confidence scoring.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![React](https://img.shields.io/badge/React-18-cyan)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Architecture

```
Media Upload → Preprocessing → Forensic Analysis (5 Modules) → Score Fusion → Tier Classification → Report
```

### Forensic Modules

| Module | Signal | Technique |
|--------|--------|-----------|
| **Metadata Analysis** | EXIF tampering | EXIF inspection, software detection, timestamp validation |
| **Compression Analysis** | Re-encoding traces | JPEG quantization tables, DCT coefficient analysis |
| **Error Level Analysis (ELA)** | Manipulated regions | Recompression difference: `ELA(x,y) = \|I_orig - I_recomp\|` |
| **Frame Consistency** | Temporal anomalies | MediaPipe face jitter, histogram shift detection |
| **Audio Forensics** | Cloned/spliced audio | Noise floor variance, mel-spectrogram gaps, MFCC transitions |

### Scoring Formula

```
Score = w₁·Metadata + w₂·Compression + w₃·ELA + w₄·Frame + w₅·Audio
```

Default weights: `0.20, 0.25, 0.25, 0.15, 0.15`

### Forgery Tiers

| Tier | Score Range | Description |
|------|-------------|-------------|
| Tier 1 | 0.00 – 0.39 | Simple edits (cropping, color shifts, metadata removal) |
| Tier 2 | 0.40 – 0.69 | Medium edits (splicing, audio cuts, cheap face-swaps) |
| Tier 3 | 0.70 – 1.00 | Advanced AI deepfakes (GAN/Diffusion, voice cloning) |

---

## Project Structure

```
├── backend/
│   ├── app.py                          # Flask API (upload, analyze, report, status)
│   ├── config.py                       # Weights, thresholds, paths
│   ├── requirements.txt                # Python dependencies
│   ├── utils/
│   │   ├── preprocessing.py            # Frame extraction, audio demux, normalization
│   │   └── scoring.py                  # Weighted fusion & tier classification
│   ├── modules/
│   │   ├── metadata_analysis.py        # EXIF / metadata inspection
│   │   ├── compression_analysis.py     # JPEG quantization / DCT
│   │   ├── ela_analysis.py             # Error Level Analysis
│   │   ├── frame_consistency.py        # Temporal / face jitter
│   │   └── audio_forensics.py          # Noise floor & spectrogram
│   ├── reports/
│   │   └── generator.py               # PDF report generation (ReportLab)
│   ├── uploads/                        # Temporary uploaded media
│   └── outputs/                        # Generated reports & artifacts
│
├── frontend/
│   ├── package.json
│   ├── public/index.html
│   └── src/
│       ├── index.js                    # React 18 entry point
│       ├── index.css                   # Premium dark-mode design system
│       ├── App.js                      # Root component
│       ├── components/
│       │   ├── Header.js               # Glassmorphic navbar
│       │   ├── FileUploader.js         # Drag-and-drop upload
│       │   ├── AnalysisDashboard.js    # Score gauge, tier badge, module grid
│       │   ├── ModuleScoreCard.js      # Per-module score card
│       │   └── ReportViewer.js         # PDF report viewer/download
│       └── utils/
│           └── api.js                  # Axios API helpers
│
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (for video audio extraction)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m backend.app
# or
python app.py
```

The Flask API runs at **http://localhost:5000**

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The React app runs at **http://localhost:3000** and connects to the backend at port 5000.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload media file (multipart/form-data) |
| `POST` | `/api/analyze` | Run forensic pipeline `{"file_id": "..."}` |
| `GET`  | `/api/report/<id>` | Download generated PDF report |
| `GET`  | `/api/status/<id>` | Check analysis status |

### Example: Upload & Analyze

```bash
# Upload
curl -X POST -F "file=@photo.jpg" http://localhost:5000/api/upload

# Analyze (use file_id from upload response)
curl -X POST -H "Content-Type: application/json" \
     -d '{"file_id": "abc123"}' \
     http://localhost:5000/api/analyze
```

---

## Security & DevOps Hardening

### Authentication Flow (JWT)
The application uses **Flask-JWT-Extended** for authentication.
- **Login/Register**: Returns an `HttpOnly` access cookie and a CSRF protection cookie. This prevents Cross-Site Scripting (XSS) attacks from accessing tokens.
- **Token Invalidation**: When a user logs out, their token's unique identifier (JTI) is saved to the database `TokenBlocklist`. Any subsequent requests with this token are rejected.
- **Refresh Flow**: Refresh tokens can be implemented securely using a similar `HttpOnly` cookie strategy if extended session lifetimes are needed.

### Production Deployment & Configuration

For production (`FLASK_ENV=production`), the application strictly enforces the following rules to prevent accidental misconfigurations:

1. **Database Integration**: SQLite (`sqlite://`) is blocked in production. Set `DATABASE_URL` to a robust database like PostgreSQL (e.g., `postgresql://user:pass@localhost/db`).
2. **Secrets Management**: `FLASK_SECRET_KEY` and `JWT_SECRET_KEY` must be strong, unique 32+ character strings. Placeholders are actively blocked.
3. **Rate Limiting**: `Flask-Limiter` requires a shared Redis instance in production to sync limits across multiple Gunicorn workers. Ensure `REDIS_URL` is set (e.g., `redis://localhost:6379/0`).

**Required Environment Variables:**
- `FLASK_ENV`
- `FLASK_SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL` (Required in production)
- `CORS_ORIGINS`

### Background Cleanup Scheduler
Temporary uploads and forensic artifacts are continuously cleared to prevent disk exhaustion. The cleanup daemon is executed automatically in `backend/app.py` via a background thread (`run_cleanup`), removing files older than `CLEANUP_MAX_AGE_HOURS` (default: 24h). Active analyses are unaffected since they process well within this window.

### Continuous Security Tooling Recommendations
It is highly recommended to integrate the following static analysis tools into your CI/CD pipeline:
- **TruffleHog / git-secrets / GitHub Secret Scanning**: Automatically detect leaked secrets in commits.
- **Bandit**: Scan Python code for common security vulnerabilities.
- **pip-audit**: Ensure backend dependencies are free of known CVEs.
- **npm audit**: Keep frontend dependencies secure.

## Configuration

All configurable parameters are in [`backend/config.py`](backend/config.py):

- **Module weights** — adjust relative importance of each forensic signal
- **Tier thresholds** — customize classification boundaries
- **Max file size** — default 100 MB
- **ELA quality** — recompression quality level (default 95)
- **Allowed extensions** — supported file types by media category

---

## Tech Stack

- **Frontend:** React 18, Vanilla CSS (glassmorphism dark theme)
- **Backend:** Flask, Flask-CORS
- **Image Processing:** OpenCV, Pillow, NumPy
- **Face Landmarking:** MediaPipe Face Mesh
- **Audio Analysis:** Librosa
- **Video Processing:** FFmpeg (subprocess)
- **Report Generation:** ReportLab
- **HTTP Client:** Axios
