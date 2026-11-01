import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.security import check_password_hash
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import os
from database import db
from models.user import User
from models.password_reset import PasswordResetRateLimit, PasswordResetToken
from middleware.auth_middleware import admin_session_required
from utils.validators import validate_email
from utils.password_reset import send_password_reset_email

auth_bp = Blueprint("auth_bp", __name__)
RESET_RESPONSE = "If an account exists with this email, you will receive a password reset link shortly."


def _utc_now():
    return datetime.now(timezone.utc)


def _as_utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _rate_limit_key(kind, value, scope="password-reset"):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, f"{scope}:{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _record_rate_limit_attempt(identifier_hash, now):
    table = PasswordResetRateLimit.__table__
    dialect = db.session.get_bind().dialect.name
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    expired_window = table.c.window_started_at <= now - timedelta(minutes=15)
    statement = insert(table).values(
        identifier_hash=identifier_hash,
        window_started_at=now,
        attempts=1,
    ).on_conflict_do_update(
        index_elements=[table.c.identifier_hash],
        set_={
            "window_started_at": case((expired_window, now), else_=table.c.window_started_at),
            "attempts": case((expired_window, 1), else_=table.c.attempts + 1),
        },
    )
    db.session.execute(statement)
    return db.session.execute(
        select(table.c.attempts).where(table.c.identifier_hash == identifier_hash)
    ).scalar_one()


def _cleanup_rate_limits(now):
    PasswordResetRateLimit.query.filter(
        PasswordResetRateLimit.window_started_at < now - timedelta(days=1)
    ).delete(synchronize_session=False)


def _login_attempt_keys(role, identity):
    ip_address = request.remote_addr or "unknown"
    return (
        _rate_limit_key("ip", ip_address, scope=f"{role}-login"),
        _rate_limit_key("identity", identity or "<invalid>", scope=f"{role}-login"),
    )


def _login_rate_limited(keys, identity_limit, ip_limit, now):
    rows = PasswordResetRateLimit.query.filter(
        PasswordResetRateLimit.identifier_hash.in_(keys)
    ).all()
    counts = {}
    for row in rows:
        if now - _as_utc(row.window_started_at) < timedelta(minutes=15):
            counts[row.identifier_hash] = row.attempts
    return counts.get(keys[0], 0) >= ip_limit or counts.get(keys[1], 0) >= identity_limit


def _record_login_failure(keys, identity_limit, ip_limit, now):
    ip_attempts = _record_rate_limit_attempt(keys[0], now)
    identity_attempts = _record_rate_limit_attempt(keys[1], now)
    db.session.commit()
    return ip_attempts >= ip_limit or identity_attempts >= identity_limit


def _clear_login_identity_counter(identity_key):
    PasswordResetRateLimit.query.filter_by(identifier_hash=identity_key).delete(synchronize_session=False)
    db.session.commit()


def _reset_token_is_valid(raw_token):
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    if not reset or reset.used_at is not None or _as_utc(reset.expires_at) <= _utc_now():
        return None
    return reset


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
    email = data.get("email") if data else None
    password = data.get("password") if data else None
    identity = email.strip().lower() if isinstance(email, str) else "<invalid>"
    keys = _login_attempt_keys("citizen", identity)
    now = _utc_now()
    _cleanup_rate_limits(now)
    if _login_rate_limited(keys, identity_limit=10, ip_limit=30, now=now):
        return jsonify({"success": False, "error": "Too many login attempts. Try again in 15 minutes."}), 429

    if not validate_email(email) or not isinstance(password, str):
        limited = _record_login_failure(keys, identity_limit=10, ip_limit=30, now=now)
        if limited:
            return jsonify({"success": False, "error": "Too many login attempts. Try again in 15 minutes."}), 429
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    user = User.query.filter_by(email=identity).first()
    if not user or not user.check_password(password):
        limited = _record_login_failure(keys, identity_limit=10, ip_limit=30, now=now)
        if limited:
            return jsonify({"success": False, "error": "Too many login attempts. Try again in 15 minutes."}), 429
        return jsonify({"success": False, "error": "Invalid email or password."}), 401
    _clear_login_identity_counter(keys[1])
    session.clear()
    session["role"] = "citizen"
    session["user_id"] = user.id
    session["password_version"] = user.password_version or 0
    return jsonify({"success": True, "user": user.to_dict()}), 200


@auth_bp.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = _json_body()
    email = data.get("email") if data else None
    if not validate_email(email) or len(email.strip()) > 254:
        return jsonify({"success": False, "error": "Enter a valid email address."}), 400

    normalized_email = email.strip().lower()
    now = _utc_now()
    try:
        _cleanup_rate_limits(now)
        PasswordResetToken.query.filter(
            PasswordResetToken.expires_at < now - timedelta(days=1)
        ).delete(synchronize_session=False)
        ip_address = request.remote_addr or "unknown"
        ip_attempts = _record_rate_limit_attempt(_rate_limit_key("ip", ip_address), now)
        email_attempts = _record_rate_limit_attempt(_rate_limit_key("email", normalized_email), now)
        db.session.commit()
        if ip_attempts > 30 or email_attempts > 5:
            return jsonify({"success": True, "message": RESET_RESPONSE}), 200

        admin_username = _admin_username().strip().lower()
        user = None if normalized_email == admin_username else User.query.filter_by(email=normalized_email).first()
        if user:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update(
                {PasswordResetToken.used_at: now}, synchronize_session=False
            )
            reset = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=now + timedelta(minutes=15),
            )
            db.session.add(reset)
            db.session.commit()
            try:
                send_password_reset_email(user, raw_token)
            except Exception:
                db.session.delete(reset)
                db.session.commit()
                current_app.logger.warning("Password reset email could not be delivered.")
        return jsonify({"success": True, "message": RESET_RESPONSE}), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Password reset request could not be processed.")
        return jsonify({"success": False, "error": "Password reset is temporarily unavailable."}), 503


@auth_bp.route("/auth/validate-reset-token", methods=["POST"])
def validate_reset_token():
    data = _json_body()
    raw_token = data.get("token") if data else None
    if not isinstance(raw_token, str) or not raw_token or len(raw_token) > 256:
        return jsonify({"success": False, "error": "This reset link is invalid or has expired."}), 400
    try:
        if not _reset_token_is_valid(raw_token):
            return jsonify({"success": False, "error": "This reset link is invalid or has expired."}), 400
        return jsonify({"success": True}), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Password reset token validation failed.")
        return jsonify({"success": False, "error": "Password reset is temporarily unavailable."}), 503


@auth_bp.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = _json_body()
    raw_token = data.get("token") if data else None
    password = data.get("password") if data else None
    confirmation = data.get("confirm_password") if data else None
    if not isinstance(raw_token, str) or not raw_token or len(raw_token) > 256:
        return jsonify({"success": False, "error": "This reset link is invalid or has expired."}), 400
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        return jsonify({"success": False, "error": "Password must be between 8 and 256 characters."}), 400
    if not isinstance(confirmation, str) or password != confirmation:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400

    try:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        reset = PasswordResetToken.query.filter_by(token_hash=token_hash).with_for_update().first()
        if not reset or reset.used_at is not None or _as_utc(reset.expires_at) <= _utc_now():
            return jsonify({"success": False, "error": "This reset link is invalid or has expired."}), 400
        user = db.session.get(User, reset.user_id)
        if not user:
            return jsonify({"success": False, "error": "This reset link is invalid or has expired."}), 400

        now = _utc_now()
        user.set_password(password)
        user.password_version = (user.password_version or 0) + 1
        PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update(
            {PasswordResetToken.used_at: now}, synchronize_session=False
        )
        db.session.commit()
        if session.get("role") == "citizen" and session.get("user_id") == user.id:
            session.clear()
        return jsonify({"success": True, "message": "Password reset successfully. Log in with your new password."}), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Password reset could not be completed.")
        return jsonify({"success": False, "error": "Password reset is temporarily unavailable."}), 503


@auth_bp.route("/auth/admin-login", methods=["POST"])
@auth_bp.route("/auth/login", methods=["POST"])
def admin_login():
    data = _json_body()
    username = data.get("username") if data else None
    password = data.get("password") if data else None
    identity = username.strip().lower() if isinstance(username, str) else "<invalid>"
    keys = _login_attempt_keys("admin", identity)
    now = _utc_now()
    _cleanup_rate_limits(now)
    if _login_rate_limited(keys, identity_limit=5, ip_limit=20, now=now):
        return jsonify({"success": False, "error": "Too many login attempts. Try again in 15 minutes."}), 429

    if not isinstance(username, str) or not isinstance(password, str):
        limited = _record_login_failure(keys, identity_limit=5, ip_limit=20, now=now)
        status = 429 if limited else 401
        message = "Too many login attempts. Try again in 15 minutes." if limited else "Invalid username or password"
        return jsonify({"success": False, "error": message}), status
    admin_username = _admin_username()
    password_hash = _admin_password_hash()
    if not password_hash or username.strip() != admin_username or not check_password_hash(password_hash, password):
        limited = _record_login_failure(keys, identity_limit=5, ip_limit=20, now=now)
        status = 429 if limited else 401
        message = "Too many login attempts. Try again in 15 minutes." if limited else "Invalid username or password"
        return jsonify({"success": False, "error": message}), status
    _clear_login_identity_counter(keys[1])
    session.clear()
    session["role"] = "admin"
    return jsonify({"success": True, "user": {"username": admin_username, "role": "admin"}}), 200


@auth_bp.route("/me", methods=["GET"])
def current_user():
    if session.get("role") == "admin":
        return jsonify({"success": True, "user": {"username": _admin_username(), "role": "admin"}}), 200
    if session.get("role") == "citizen":
        user = db.session.get(User, session.get("user_id"))
        if user and session.get("password_version", 0) == (user.password_version or 0):
            return jsonify({"success": True, "user": {**user.to_dict(), "role": "citizen"}}), 200
        session.clear()
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
