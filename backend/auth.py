from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from extensions import db, bcrypt
from models import User
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    username = data.get("username").strip()
    password = data.get("password").strip()

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    new_user = User(username=username, password_hash=password_hash)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"New user registered: {username}")
        
        # Optionally auto-login after register
        access_token = create_access_token(identity=new_user.id)
        return jsonify({
            "message": "User registered successfully",
            "user": new_user.to_dict(),
            "token": access_token
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during registration: {e}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=data.get("username").strip()).first()
    
    if not user or not bcrypt.check_password_hash(user.password_hash, data.get("password").strip()):
        return jsonify({"error": "Invalid username or password"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        "token": access_token
    }), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"user": user.to_dict()}), 200
