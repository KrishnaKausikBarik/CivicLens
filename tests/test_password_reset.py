import hashlib
import os
import struct
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from werkzeug.security import generate_password_hash

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "password-reset-tests-only-secret"
os.environ["FRONTEND_URL"] = "http://127.0.0.1:5000"
os.environ["ADMIN_USERNAME"] = "admin@example.test"

from Backend.app import create_app
from database import db
from models.password_reset import PasswordResetRateLimit, PasswordResetToken
from models.user import User
from utils.password_reset import send_password_reset_email
from utils.request_logging import redact_reset_token_path
from config import get_database_url


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(full_name="Test Citizen", email="citizen@example.test")
            user.set_password("old-password-123")
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def post_json(self, path, payload, include_csrf=True):
        headers = {"Content-Type": "application/json"}
        if include_csrf:
            token = self.client.get("/api/csrf").get_json()["csrf_token"]
            headers["X-CSRF-Token"] = token
        return self.client.post(path, json=payload, headers=headers)

    def issue_reset(self, email="citizen@example.test"):
        captured = {}

        def capture(user, token):
            captured["token"] = token
            captured["email"] = user.email

        with patch("routes.auth.send_password_reset_email", side_effect=capture):
            response = self.post_json("/api/auth/forgot-password", {"email": email})
        self.assertEqual(response.status_code, 200)
        return captured.get("token")

    def test_forgot_password_sends_for_existing_and_is_generic_for_unknown_email(self):
        with patch("routes.auth.send_password_reset_email") as send_email:
            known = self.post_json("/api/auth/forgot-password", {"email": "citizen@example.test"})
            unknown = self.post_json("/api/auth/forgot-password", {"email": "nobody@example.test"})
        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.get_json(), unknown.get_json())
        self.assertIn("If an account exists", known.get_json()["message"])
        send_email.assert_called_once()

    def test_successful_email_delivery_uses_configured_frontend_url(self):
        os.environ.update({
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "sender@example.test",
            "SMTP_PASSWORD": "test-app-password",
            "SMTP_SENDER_EMAIL": "sender@example.test",
            "SMTP_SENDER_NAME": "CivicLens",
        })
        with self.app.app_context():
            user = User.query.filter_by(email="citizen@example.test").one()
            with patch("utils.password_reset.smtplib.SMTP") as smtp_class:
                send_password_reset_email(user, "test-reset-token")
            smtp_class.assert_called_once_with("smtp.example.test", 587, timeout=10)
            smtp_class.return_value.__enter__.return_value.starttls.assert_called_once()
            message = smtp_class.return_value.__enter__.return_value.send_message.call_args.args[0]
            self.assertEqual(message["Subject"], "Reset Your CivicLens Password")
            html = message.get_body(preferencelist=("html",)).get_content()
            self.assertIn("href='http://127.0.0.1:5000/reset-password#token=test-reset-token'", html)
            self.assertIn("background-color:#065f46", html)
            self.assertIn("Reset your password", html)
            self.assertIn("Hello Test Citizen", html)
            self.assertIn("15 minutes", html)

    def test_production_reset_email_uses_configured_vercel_url(self):
        with self.app.app_context(), patch.dict(os.environ, {
            "FRONTEND_URL": "https://civiclens-lake.vercel.app",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "sender@example.test",
            "SMTP_PASSWORD": "test-app-password",
            "SMTP_SENDER_EMAIL": "sender@example.test",
            "SMTP_SENDER_NAME": "CivicLens",
        }), patch("utils.password_reset.smtplib.SMTP") as smtp_class:
            user = User.query.filter_by(email="citizen@example.test").one()
            send_password_reset_email(user, "production-test-token")

        message = smtp_class.return_value.__enter__.return_value.send_message.call_args.args[0]
        html = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn("href='https://civiclens-lake.vercel.app/reset-password#token=production-test-token'", html)
        self.assertNotIn("127.0.0.1", html)

    def test_valid_reset_updates_password_and_token_cannot_be_reused(self):
        token = self.issue_reset()
        self.assertTrue(token)
        with self.app.app_context():
            reset = PasswordResetToken.query.one()
            self.assertEqual(reset.token_hash, hashlib.sha256(token.encode()).hexdigest())
            self.assertNotEqual(reset.token_hash, token)
        self.assertEqual(self.post_json("/api/auth/validate-reset-token", {"token": token}).status_code, 200)
        payload = {"token": token, "password": "new-password-456", "confirm_password": "new-password-456"}
        reset = self.post_json("/api/auth/reset-password", payload)
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(self.post_json("/api/auth/reset-password", payload).status_code, 400)
        self.assertEqual(self.post_json("/api/login", {"email": "citizen@example.test", "password": "new-password-456"}).status_code, 200)
        self.assertEqual(self.post_json("/api/login", {"email": "citizen@example.test", "password": "old-password-123"}).status_code, 401)

    def test_password_change_invalidates_existing_citizen_sessions(self):
        old_session = self.app.test_client()
        csrf = old_session.get("/api/csrf").get_json()["csrf_token"]
        logged_in = old_session.post("/api/login", json={
            "email": "citizen@example.test", "password": "old-password-123"
        }, headers={"X-CSRF-Token": csrf})
        self.assertEqual(logged_in.status_code, 200)
        token = self.issue_reset()
        reset = self.post_json("/api/auth/reset-password", {
            "token": token, "password": "new-password-456", "confirm_password": "new-password-456"
        })
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(old_session.get("/api/reports").status_code, 401)

    def test_expired_invalid_and_reused_tokens_are_rejected(self):
        expired = "expired-test-token"
        with self.app.app_context():
            user = User.query.filter_by(email="citizen@example.test").one()
            db.session.add(PasswordResetToken(
                user_id=user.id,
                token_hash=hashlib.sha256(expired.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            ))
            db.session.commit()
        self.assertEqual(self.post_json("/api/auth/validate-reset-token", {"token": "not-a-token"}).status_code, 400)
        self.assertEqual(self.post_json("/api/auth/validate-reset-token", {"token": expired}).status_code, 400)
        response = self.post_json("/api/auth/reset-password", {
            "token": expired, "password": "new-password-456", "confirm_password": "new-password-456"
        })
        self.assertEqual(response.status_code, 400)

    def test_password_mismatch_and_validation(self):
        token = self.issue_reset()
        mismatch = self.post_json("/api/auth/reset-password", {
            "token": token, "password": "new-password-456", "confirm_password": "different-password"
        })
        short = self.post_json("/api/auth/reset-password", {
            "token": token, "password": "short", "confirm_password": "short"
        })
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(short.status_code, 400)

    def test_reset_rate_limit_and_admin_account_restriction(self):
        with patch("routes.auth.send_password_reset_email") as send_email:
            responses = [self.post_json("/api/auth/forgot-password", {"email": "citizen@example.test"}) for _ in range(6)]
            admin = self.post_json("/api/auth/forgot-password", {"email": "admin@example.test"})
        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertEqual(responses[0].get_json(), responses[-1].get_json())
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(send_email.call_count, 5)
        with self.app.app_context():
            self.assertEqual(PasswordResetToken.query.count(), 5)

    def test_forgot_and_reset_endpoints_require_csrf(self):
        forgot = self.post_json("/api/auth/forgot-password", {"email": "citizen@example.test"}, include_csrf=False)
        reset = self.post_json("/api/auth/reset-password", {
            "token": "token", "password": "new-password-456", "confirm_password": "new-password-456"
        }, include_csrf=False)
        self.assertEqual(forgot.status_code, 400)
        self.assertEqual(reset.status_code, 400)

    def test_reset_page_is_not_cached_and_uses_no_referrer(self):
        response = self.client.get("/reset-password")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertIn(b"resetPasswordForm", response.data)
        self.assertIn(b"Create New Password", response.data)
        self.assertIn(b'class="navbar"', response.data)
        self.assertIn(b"Show password", response.data)
        self.assertIn(b"Return to login", response.data)
        self.assertIn(b'name="viewport"', response.data)

    def test_reset_frontend_reads_fragment_cleans_history_and_posts_token(self):
        script = (Path(__file__).resolve().parents[1] / "Frontend" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn("new URLSearchParams(resetUrl.hash.slice(1)).get('token')", script)
        self.assertIn("window.history.replaceState(null, '', '/reset-password')", script)
        self.assertIn("body: JSON.stringify({ token: resetToken })", script)
        self.assertIn("window.location.assign('/?citizen_login=1')", script)

    def test_local_access_log_redacts_reset_token(self):
        path = "/reset-password?token=secret-token&source=email"
        redacted = redact_reset_token_path(path)
        self.assertNotIn("secret-token", redacted)
        self.assertIn("token=%5BREDACTED%5D", redacted)
        self.assertIn("source=email", redacted)

    def test_production_app_initializes_with_null_pool_and_ssl(self):
        production_url = (
            "postgresql+psycopg://postgres.test-project:unused@"
            "aws-0-test-region.pooler.supabase.com:5432/postgres?sslmode=require"
        )
        with patch.dict(os.environ, {
            "DATABASE_URL": production_url,
            "SECRET_KEY": "production-startup-test-secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD_HASH": generate_password_hash("test-admin-password"),
        }):
            production_app = create_app("production")
            self.assertFalse(production_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"))
            self.assertTrue(production_app.config["SESSION_COOKIE_SECURE"])
            with production_app.app_context():
                self.assertEqual(type(db.engine.pool).__name__, "NullPool")
                self.assertEqual(db.engine.url.query.get("sslmode"), "require")
                db.engine.dispose()
            with production_app.test_client() as production_client:
                reset_page = production_client.get("/reset-password")
                self.assertEqual(reset_page.status_code, 200)
                self.assertIn(b"Create New Password", reset_page.data)
                self.assertIn(b"reset-page-main", reset_page.data)

    def test_production_rejects_direct_database_and_sqlite_urls(self):
        for url in (
            "postgresql+psycopg://postgres:unused@db.test.supabase.co:5432/postgres?sslmode=require",
            "sqlite:///local.db",
        ):
            with self.subTest(url=url), patch.dict(os.environ, {"DATABASE_URL": url}):
                with self.assertRaises(RuntimeError):
                    get_database_url(production=True)

    def test_citizen_registration_and_login(self):
        registered = self.post_json("/api/register", {
            "full_name": "New Citizen",
            "email": "new-citizen@example.test",
            "password": "new-citizen-password",
            "confirm_password": "new-citizen-password",
        })
        self.assertEqual(registered.status_code, 201)
        login = self.post_json("/api/login", {
            "email": "new-citizen@example.test",
            "password": "new-citizen-password",
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.get_json()["user"]["email"], "new-citizen@example.test")

    def test_admin_login_and_role_restrictions(self):
        admin_hash = generate_password_hash("test-admin-password")
        with patch("routes.auth._admin_username", return_value="admin@example.test"), \
             patch("routes.auth._admin_password_hash", return_value=admin_hash):
            login = self.post_json("/api/auth/admin-login", {
                "username": "admin@example.test", "password": "test-admin-password"
            })
            self.assertEqual(login.status_code, 200)
            self.assertEqual(self.client.get("/api/admin/reports").status_code, 200)
            self.assertEqual(self.client.get("/api/reports").status_code, 401)

        citizen = self.app.test_client()
        token = citizen.get("/api/csrf").get_json()["csrf_token"]
        citizen_login = citizen.post("/api/login", json={
            "email": "citizen@example.test", "password": "old-password-123"
        }, headers={"X-CSRF-Token": token})
        self.assertEqual(citizen_login.status_code, 200)
        self.assertEqual(citizen.get("/api/admin/reports").status_code, 401)

    def test_citizen_and_admin_login_rate_limits(self):
        citizen_responses = [self.post_json("/api/login", {
            "email": "citizen@example.test", "password": "wrong-password"
        }) for _ in range(10)]
        self.assertTrue(all(response.status_code == 401 for response in citizen_responses[:-1]))
        self.assertEqual(citizen_responses[-1].status_code, 429)
        self.assertEqual(self.post_json("/api/login", {
            "email": "citizen@example.test", "password": "old-password-123"
        }).status_code, 429)

        admin_hash = generate_password_hash("test-admin-password")
        with patch("routes.auth._admin_username", return_value="admin@example.test"), \
             patch("routes.auth._admin_password_hash", return_value=admin_hash):
            responses = [self.post_json("/api/auth/admin-login", {
                "username": "admin@example.test", "password": "wrong-password"
            }) for _ in range(5)]
        self.assertTrue(all(response.status_code == 401 for response in responses[:-1]))
        self.assertEqual(responses[-1].status_code, 429)

    def test_complaint_submission_and_admin_status_update(self):
        citizen = self.app.test_client()
        csrf = citizen.get("/api/csrf").get_json()["csrf_token"]
        login = citizen.post("/api/login", json={
            "email": "citizen@example.test", "password": "old-password-123"
        }, headers={"X-CSRF-Token": csrf})
        self.assertEqual(login.status_code, 200)
        complaint = citizen.post("/api/reports", json={
            "title": "Test pothole",
            "category": "Roads & Footpaths",
            "description": "A test complaint for production-readiness checks.",
            "latitude": 12.9716,
            "longitude": 77.5946,
        }, headers={"X-CSRF-Token": citizen.get("/api/csrf").get_json()["csrf_token"]})
        self.assertEqual(complaint.status_code, 201)
        report_id = complaint.get_json()["report"]["id"]
        my_complaints = citizen.get("/api/reports")
        self.assertEqual(my_complaints.status_code, 200)
        self.assertEqual([report["id"] for report in my_complaints.get_json()], [report_id])

        admin = self.app.test_client()
        admin_hash = generate_password_hash("test-admin-password")
        with patch("routes.auth._admin_username", return_value="admin@example.test"), \
             patch("routes.auth._admin_password_hash", return_value=admin_hash):
            admin_csrf = admin.get("/api/csrf").get_json()["csrf_token"]
            login = admin.post("/api/auth/admin-login", json={
                "username": "admin@example.test", "password": "test-admin-password"
            }, headers={"X-CSRF-Token": admin_csrf})
            self.assertEqual(login.status_code, 200)
            update = admin.put(f"/api/admin/reports/{report_id}/status", json={"status": "In Progress"},
                               headers={"X-CSRF-Token": admin.get("/api/csrf").get_json()["csrf_token"]})
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.get_json()["report"]["status"], "In Progress")

    def test_static_css_and_javascript_are_served(self):
        css = self.client.get("/static/css/style.css")
        javascript = self.client.get("/static/js/main.js")
        self.assertEqual(css.status_code, 200)
        self.assertEqual(javascript.status_code, 200)
        self.assertIn(b"--color-primary", css.data)
        self.assertIn(b"resetUrl.hash.slice(1)", javascript.data)
        css.close()
        javascript.close()

    def test_favicon_assets_are_served_and_referenced_by_every_page(self):
        public_dir = Path(__file__).resolve().parents[1] / "public"
        expected_sizes = {
            "favicon.ico": None,
            "favicon.svg": None,
            "favicon-32x32.png": (32, 32),
            "apple-touch-icon.png": (180, 180),
        }
        for name, size in expected_sizes.items():
            response = self.client.get(f"/{name}")
            self.assertEqual(response.status_code, 200, name)
            data = (public_dir / name).read_bytes()
            self.assertEqual(response.data, data, name)
            if name.endswith(".png"):
                self.assertEqual(struct.unpack(">II", data[16:24]), size)
            response.close()

        html_pages = list((public_dir.parent / "Frontend").rglob("*.html"))
        self.assertEqual(len(html_pages), 8)
        for page in html_pages:
            source = page.read_text(encoding="utf-8")
            for asset in expected_sizes:
                self.assertIn(f'href="/{asset}"', source, str(page))


if __name__ == "__main__":
    unittest.main()
