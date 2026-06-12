"""
Centralized configuration for the Deepfake Verification Platform.

Defines module weights, tier thresholds, file handling parameters,
and forensic analysis settings used across the entire application.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# ---------------------------------------------------------------------------
# Base directories – resolved relative to *this* file so they work regardless
# of where the application is launched from.
# ---------------------------------------------------------------------------
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR: str = os.path.join(BASE_DIR, "outputs")

# ---------------------------------------------------------------------------
# Application secrets & JWT
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", "")
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("CRITICAL: FLASK_SECRET_KEY environment variable is missing or too weak. It must be at least 32 characters.")

if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("CRITICAL: JWT_SECRET_KEY environment variable is missing or too weak. It must be at least 32 characters.")

# Enable JWT cookies for enhanced security
JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"  # True in production
JWT_COOKIE_CSRF_PROTECT = True

JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=30)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///deepfake.db")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
CLEANUP_MAX_AGE_HOURS: int = int(os.environ.get("CLEANUP_MAX_AGE_HOURS", "24"))

# ---------------------------------------------------------------------------
# File upload constraints
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "image": {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp", "gif"},
    "video": {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"},
    "audio": {"wav", "mp3", "flac", "aac", "ogg", "m4a"},
}

# Flat set for quick membership checks during upload validation.
ALL_ALLOWED_EXTENSIONS: set[str] = set()
for _exts in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(_exts)

# ---------------------------------------------------------------------------
# Forensic module weights (must sum to 1.0 when all modules participate)
# Note: These weights are automatically normalized at runtime based on which
# modules actually execute for a given media type. For example, if an audio
# file only triggers the 'audio' module, its weight becomes 1.0 (100%).
# ---------------------------------------------------------------------------
MODULE_WEIGHTS: dict[str, float] = {
    "metadata":    0.20,
    "compression": 0.25,
    "ela":         0.25,
    "frame":       0.15,
    "audio":       0.15,
}

# ---------------------------------------------------------------------------
# Tier classification thresholds
#   Tier 1 – Likely Authentic   : score < 0.4
#   Tier 2 – Suspicious         : 0.4 <= score < 0.7
#   Tier 3 – Likely Manipulated : score >= 0.7
# ---------------------------------------------------------------------------
TIER_THRESHOLDS: list[dict] = [
    {
        "tier": 1,
        "max_score": 0.4,
        "label": "Likely Authentic",
        "description": (
            "The media shows minimal signs of manipulation. "
            "No significant anomalies were detected across the analysed modules."
        ),
    },
    {
        "tier": 2,
        "max_score": 0.7,
        "label": "Suspicious",
        "description": (
            "Some indicators of potential manipulation were found. "
            "Manual review is recommended to confirm authenticity."
        ),
    },
    {
        "tier": 3,
        "max_score": 1.0,  # inclusive upper bound
        "label": "Likely Manipulated",
        "description": (
            "Strong evidence of manipulation detected. "
            "Multiple forensic modules flagged anomalies consistent with forgery."
        ),
    },
]

# ---------------------------------------------------------------------------
# ELA (Error Level Analysis) parameters
# ---------------------------------------------------------------------------
ELA_RECOMPRESSION_QUALITY: int = 95

# ---------------------------------------------------------------------------
# Frame extraction defaults
# ---------------------------------------------------------------------------
DEFAULT_FRAME_EXTRACTION_FPS: int = 1

# ---------------------------------------------------------------------------
# Image normalisation
# ---------------------------------------------------------------------------
IMAGE_MAX_DIMENSION: int = 1920

# ---------------------------------------------------------------------------
# Production Configuration Validation
# ---------------------------------------------------------------------------
def validate_production_config():
    """Fail application startup if required production secrets or infrastructure settings are missing."""
    if os.environ.get("FLASK_ENV") == "production":
        # Check SQLite
        if DATABASE_URL.startswith("sqlite://"):
            raise RuntimeError("CRITICAL: SQLite cannot be used in production. Please configure a production DATABASE_URL (e.g., PostgreSQL).")
        
        # Check Weak Secrets
        weak_secrets = ["12345678901234567890123456789012", "abcdefghijklmnopqrstuvwxyz123456"]
        if SECRET_KEY in weak_secrets or JWT_SECRET_KEY in weak_secrets:
            raise RuntimeError("CRITICAL: Production secrets cannot be default placeholder values.")
        
        # Redis is checked in extensions.py, so it's handled there.

validate_production_config()
