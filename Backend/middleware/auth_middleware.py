from functools import wraps
from flask import jsonify, session
from models.user import User


def citizen_session_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "citizen" or not session.get("user_id"):
            return jsonify({"success": False, "error": "Citizen login required."}), 401
        user = User.query.get(session["user_id"])
        if not user:
            session.clear()
            return jsonify({"success": False, "error": "Citizen account not found."}), 401
        return f(user, *args, **kwargs)
    return decorated


def admin_session_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"success": False, "error": "Administrator login required."}), 401
        return f(*args, **kwargs)
    return decorated
