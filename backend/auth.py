"""Authentication blueprint for the Deepfake Verification Platform."""
from __future__ import annotations

import logging
import re
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    get_jwt,
)

from extensions import bcrypt, db, limiter
from models import User, TokenBlocklist

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ── Validation helpers ──────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validate_registration(data: dict[str, Any]) -> str | None:
    """Return an error message if the registration payload is invalid."""
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 80:
        return "Username must be at most 80 characters."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        return "Username may only contain letters, digits, underscores, dots, or hyphens."
    if not email or not _EMAIL_RE.match(email):
        return "A valid email address is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


# ── Endpoints ───────────────────────────────────────────────────────────────


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5/hour")
def register():
    """Register a new user account.

    **Request** (JSON): ``{username, email, password}``
    **Response** (201): ``{user}`` (cookies set)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    error = _validate_registration(data)
    if error:
        return jsonify({"error": error}), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    password = data["password"]

    # Check for duplicates
    if db.session.query(User).filter_by(username=username).first():
        return jsonify({"error": "Username already taken."}), 409
    if db.session.query(User).filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    logger.info("New user registered: id=%s username=%s", user.id, username)
    response = jsonify({"user": user.to_dict()})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    """Authenticate a user and issue JWT cookies.

    **Request** (JSON): ``{email, password}``
    **Response** (200): ``{user}`` (cookies set)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = db.session.query(User).filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password."}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    logger.info("User logged in: id=%s", user.id)
    response = jsonify({"user": user.to_dict()})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    """Log out a user by revoking the token and unsetting cookies.

    **Response** (200): ``{msg}``
    """
    token = get_jwt()
    jti = token["jti"]
    ttype = token["type"]
    
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    
    response = jsonify({"msg": f"Successfully logged out ({ttype} token revoked)."})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Issue a new access token using a valid refresh cookie.

    **Response** (200): ``{}`` (new access cookie set)
    """
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    
    response = jsonify({"msg": "Token refreshed successfully."})
    set_access_cookies(response, access_token)
    return response, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the current authenticated user's profile.

    **Response** (200): ``{user: {...}}``
    """
    current_user_id = get_jwt_identity()
    user = db.session.get(User, int(current_user_id))
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict()}), 200
