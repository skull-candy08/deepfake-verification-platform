"""SQLAlchemy models for the Deepfake Verification Platform."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from extensions import db


class User(db.Model):
    """Registered user."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    uploads = db.relationship("Upload", backref="user", lazy=True)
    analyses = db.relationship("Analysis", backref="user", lazy=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Upload(db.Model):
    """A file uploaded by a user."""

    __tablename__ = "uploads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    original_filename = db.Column(db.String(256), nullable=False)
    saved_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(16), nullable=False)
    uploaded_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    analyses = db.relationship("Analysis", backref="upload", lazy=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_id": self.file_id,
            "original_filename": self.original_filename,
            "media_type": self.media_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class TokenBlocklist(db.Model):
    """Blocklist for revoked JWT tokens."""

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Analysis(db.Model):
    """An analysis run against an uploaded file."""

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey("uploads.id"), nullable=False)
    analysis_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    fused_score = db.Column(db.Float, nullable=True)
    tier_label = db.Column(db.String(64), nullable=True)
    verdict = db.Column(db.String(128), nullable=True)
    report_path = db.Column(db.String(512), nullable=True)
    error_message = db.Column(db.String(512), nullable=True)
    started_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at = db.Column(db.DateTime, nullable=True)
    result_json = db.Column(db.Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": self.id,
            "user_id": self.user_id,
            "upload_id": self.upload_id,
            "analysis_id": self.analysis_id,
            "status": self.status,
            "fused_score": self.fused_score,
            "tier_label": self.tier_label,
            "verdict": self.verdict,
            "report_id": self.analysis_id if self.report_path else None,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
        # Include parsed results if available
        if self.result_json:
            try:
                result["results"] = json.loads(self.result_json)
            except (json.JSONDecodeError, TypeError):
                result["results"] = None
        return result
