"""Centralized Flask extension instances (avoids circular imports)."""
import os
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

# Use Redis for rate limiting if available, otherwise fallback to memory
redis_url = os.environ.get("REDIS_URL")
storage_uri = redis_url if redis_url else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri=storage_uri,
)
