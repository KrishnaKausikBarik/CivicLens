from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import os
from database import db
from models.user import User
from middleware.auth_middleware import admin_session_required
from utils.validators import validate_email

auth_bp = Blueprint("auth_bp", __name__)


def _admin_username():
    return os.environ.get("ADMIN_USERNAME", "admin")


def _admin_password_hash():
    return os.environ.get("ADMIN_PASSWORD_HASH", "")


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@auth_bp.route("/register", methods=["POST"])
def register():
    data = _json_body()
    if data is None:
        return jsonify({"success": False, "error": "A valid JSON object is required."}), 400

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    if not isinstance(full_name, str) or not full_name.strip() or len(full_name.strip()) > 120:
        return jsonify({"success": False, "error": "Enter your full name (up to 120 characters)."}), 400
    if not validate_email(email) or len(email.strip()) > 254:
        return jsonify({"success": False, "error": "Enter a valid email address."}), 400
    if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
        return jsonify({"success": False, "error": "Password must be between 8 and 256 characters."}), 400
    if password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400

    normalized_email = email.strip().lower()
    try:
        if User.query.filter_by(email=normalized_email).first():
            return jsonify({"success": False, "error": "An account with this email already exists."}), 409

        user = User(full_name=full_name.strip(), email=normalized_email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "error": "An account with this email already exists."}), 409
    except SQLAlchemyError:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception("Citizen registration database operation failed")
        return jsonify({"success": False, "error": "Account could not be created."}), 500
    return jsonify({"success": True, "message": "Account created. You can now log in."}), 201


@auth_bp.route("/login", methods=["POST"])
def citizen_login():
    data = _json_body()
    if data is None:
        return jsonify({"success": False, "error": "A valid JSON object is required."}), 400
    email = data.get("email")
    password = data.get("password")
    if not validate_email(email) or not isinstance(password, str):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401
    session.clear()
    session["role"] = "citizen"
    session["user_id"] = user.id
    return jsonify({"success": True, "user": user.to_dict()}), 200


@auth_bp.route("/auth/admin-login", methods=["POST"])
@auth_bp.route("/auth/login", methods=["POST"])
def admin_login():
    data = _json_body()
    if data is None:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    admin_username = _admin_username()
    password_hash = _admin_password_hash()
    if not password_hash or username.strip() != admin_username or not check_password_hash(password_hash, password):
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    session.clear()
    session["role"] = "admin"
    return jsonify({"success": True, "user": {"username": admin_username, "role": "admin"}}), 200


@auth_bp.route("/me", methods=["GET"])
def current_user():
    if session.get("role") == "admin":
        return jsonify({"success": True, "user": {"username": _admin_username(), "role": "admin"}}), 200
    if session.get("role") == "citizen":
        user = User.query.get(session.get("user_id"))
        if user:
            return jsonify({"success": True, "user": {**user.to_dict(), "role": "citizen"}}), 200
    return jsonify({"success": False, "user": None}), 200


@auth_bp.route("/logout", methods=["POST"])
@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out."}), 200


@auth_bp.route("/auth/session", methods=["GET"])
@admin_session_required
def admin_session():
    return jsonify({"success": True, "user": {"username": _admin_username(), "role": "admin"}}), 200
