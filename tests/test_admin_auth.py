import os
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "admin-auth-tests-only-secret")

from Backend.app import create_app
from database import db


class AdminAuthFlowTests(unittest.TestCase):
    def make_app(self, production=False):
        env = {
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD_HASH": generate_password_hash("admin123"),
            "SECRET_KEY": "admin-auth-tests-only-secret",
            "FLASK_ENV": "testing",
            "DATABASE_URL": "sqlite://",
        }
        with patch.dict(os.environ, env):
            app = create_app("testing")
        app.config["TESTING"] = True
        # Exercise Vercel's secure-cookie behavior without connecting to Supabase.
        app.config["SESSION_COOKIE_SECURE"] = production
        with app.app_context():
            db.create_all()
        return app

    def post_with_csrf(self, client, path, payload=None):
        token = client.get("/api/csrf", base_url="https://localhost").get_json()["csrf_token"]
        return client.post(path, json=payload, headers={"X-CSRF-Token": token}, base_url="https://localhost")

    def assert_complete_admin_flow(self, production=False):
        client = self.make_app(production).test_client()

        self.assertEqual(client.get("/admin", base_url="https://localhost").status_code, 302)
        login = self.post_with_csrf(client, "/api/auth/admin-login", {
            "username": "admin", "password": "admin123",
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.get_json()["user"]["role"], "admin")
        self.assertTrue(client.get("/api/auth/session", base_url="https://localhost").get_json()["success"])
        self.assertEqual(client.get("/admin", base_url="https://localhost").status_code, 200)
        self.assertEqual(client.get("/admin", base_url="https://localhost").status_code, 200)

        logout = self.post_with_csrf(client, "/api/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(client.get("/api/auth/session", base_url="https://localhost").status_code, 401)
        self.assertEqual(client.get("/admin", base_url="https://localhost").status_code, 302)

        relogin = self.post_with_csrf(client, "/api/auth/admin-login", {
            "username": "admin", "password": "admin123",
        })
        self.assertEqual(relogin.status_code, 200)
        self.assertEqual(client.get("/admin", base_url="https://localhost").status_code, 200)

    def test_complete_local_admin_flow(self):
        self.assert_complete_admin_flow()

    def test_complete_production_like_admin_flow(self):
        self.assert_complete_admin_flow(production=True)

    def test_wrong_credentials_do_not_create_an_admin_session(self):
        client = self.make_app().test_client()
        response = self.post_with_csrf(client, "/api/auth/admin-login", {
            "username": "admin", "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(client.get("/api/auth/session", base_url="https://localhost").status_code, 401)

    def test_admin_pages_hide_recovery_while_citizen_recovery_remains(self):
        client = self.make_app().test_client()
        home = client.get("/").get_data(as_text=True)
        admin_form = home.split('<form id="adminLoginForm"', 1)[1].split("</form>", 1)[0]
        citizen_form = home.split('<form id="citizenLoginForm"', 1)[1].split("</form>", 1)[0]
        self.assertNotIn("Forgot password?", admin_form)
        self.assertNotIn("forgotPasswordToggle", admin_form)
        self.assertIn("Forgot password?", citizen_form)
        self.assertIn("citizenForgotPasswordToggle", citizen_form)

        self.assertEqual(self.post_with_csrf(client, "/api/auth/admin-login", {
            "username": "admin", "password": "admin123",
        }).status_code, 200)
        dashboard = client.get("/admin").get_data(as_text=True)
        admin_dashboard_form = dashboard.split('<form id="adminLoginForm"', 1)[1].split("</form>", 1)[0]
        self.assertNotIn("Forgot password?", admin_dashboard_form)
        self.assertNotIn("forgotPasswordToggle", admin_dashboard_form)

    def test_missing_hash_fails_closed_with_safe_service_error(self):
        client = self.make_app().test_client()
        with patch.dict(os.environ, {"ADMIN_PASSWORD_HASH": ""}):
            response = self.post_with_csrf(client, "/api/auth/admin-login", {
                "username": "admin", "password": "admin123",
            })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(client.get("/api/auth/session", base_url="https://localhost").status_code, 401)


if __name__ == "__main__":
    unittest.main()
