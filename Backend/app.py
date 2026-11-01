import os
import sys
import hmac
import secrets
from flask import Flask, render_template, jsonify, redirect, session, request, make_response, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import config_by_name
from database import db
from routes.reports import reports_bp
from routes.auth import auth_bp

def create_app(config_name=None):
    """Application Factory Pattern."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development").lower()

    FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Frontend"))
    PUBLIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "public"))

    # Templates are bundled with the function. Static assets are published from
    # public/static by Vercel while retaining Flask's /static URL convention.
    template_folder = os.path.join(FRONTEND_DIR, "templates") if os.path.exists(os.path.join(FRONTEND_DIR, "templates")) else FRONTEND_DIR
    public_static = os.path.abspath(os.path.join(BASE_DIR, "..", "public", "static"))

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=public_static,
        static_url_path="/static",
        instance_path=os.path.join(BASE_DIR, "instance")
    )

    # Apply configuration
    app_config = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(app_config)
    from config import get_database_url
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url(production=config_name == "production")
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is missing. Set it in the project root .env file.")
    if config_name == "production" and not os.environ.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set in the production environment.")
    if config_name == "production" and (not os.environ.get("ADMIN_USERNAME") or not os.environ.get("ADMIN_PASSWORD_HASH")):
        raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD_HASH must be set in the production environment.")
    if config_name == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    # Enable CORS for frontend API calls
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}}, supports_credentials=True)

    @app.before_request
    def enforce_csrf_for_api_writes():
        if request.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if session.get("role") not in {"citizen", "admin"} and request.path in {
                "/api/register", "/api/login", "/api/auth/admin-login", "/api/auth/login", "/api/logout", "/api/auth/logout"
            }:
                return None
            expected = session.get("csrf_token", "")
            supplied = request.headers.get("X-CSRF-Token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                return jsonify({"success": False, "error": "CSRF validation failed. Refresh and try again."}), 400

    @app.get("/api/csrf")
    def csrf_token():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return jsonify({"csrf_token": token})

    def serve_public_icon(filename):
        return send_from_directory(PUBLIC_DIR, filename, max_age=86400)

    for icon_name in ("favicon.ico", "favicon.svg", "favicon-32x32.png", "apple-touch-icon.png"):
        app.add_url_rule(
            f"/{icon_name}",
            endpoint=f"serve_{icon_name.replace('-', '_').replace('.', '_')}",
            view_func=lambda asset=icon_name: serve_public_icon(asset),
        )

    # Initialize the extension without opening a connection during module import.
    # Serverless cold starts should not fail until a request actually needs DB access.
    db.init_app(app)

    # Register blueprints under /api prefix
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")

    @app.get("/api/health/database")
    def database_health():
        from sqlalchemy import text
        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()
            return jsonify({"success": True, "database": "connected"}), 200
        except Exception:
            app.logger.exception("Supabase PostgreSQL connectivity check failed")
            return jsonify({"success": False, "database": "unavailable"}), 503

    # ==========================================
    # Integrated HTML Page Routes
    # ==========================================
    @app.route("/", methods=["GET"])
    @app.route("/index.html", methods=["GET"])
    def serve_index():
        return render_template("index.html")

    @app.route("/dashboard", methods=["GET"])
    @app.route("/dashboard.html", methods=["GET"])
    def serve_dashboard():
        return render_template("dashboard.html")

    @app.route("/citizen", methods=["GET"])
    @app.route("/citizen/dashboard", methods=["GET"])
    def serve_citizen_dashboard():
        if session.get("role") != "citizen":
            return redirect("/?citizen_login=1")
        return render_template("citizen.html")

    @app.get("/reset-password")
    def serve_reset_password():
        response = make_response(render_template("index.html", reset_mode=True))
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.route("/admin", methods=["GET"])
    @app.route("/admin.html", methods=["GET"])
    def serve_admin():
        if session.get("role") != "admin":
            return redirect("/?admin_login=1")
        return render_template("admin.html")

    # ==========================================
    # Global Error Handlers
    # ==========================================
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Requested resource was not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"success": False, "error": "HTTP method not allowed for this route."}), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"success": False, "error": "Internal server error."}), 500

    return app

app = create_app()

if __name__ == "__main__":
    from utils.request_logging import RedactingWSGIRequestHandler

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("==================================================")
    print(f" CivicLens Server live at: http://{host}:{port}")
    print(" Admin login: use the configured CivicLens admin credentials.")
    print("==================================================")
    app.run(
        host=host,
        port=port,
        debug=os.environ.get("FLASK_ENV", "development").lower() != "production",
        request_handler=RedactingWSGIRequestHandler,
    )
