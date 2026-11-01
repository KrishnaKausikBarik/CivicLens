"""Root entrypoint proxy forwarding to Backend/app.py."""
import importlib.util
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "Backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

spec = importlib.util.spec_from_file_location("backend_app", os.path.join(BACKEND_DIR, "app.py"))
backend_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_app)

app = backend_app.app
create_app = backend_app.create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("==================================================")
    print(f" CivicLens Server live at: http://{host}:{port}")
    print(" Admin login: use the configured CivicLens admin credentials.")
    print("==================================================")
    app.run(host=host, port=port, debug=os.environ.get("FLASK_ENV", "development").lower() != "production")
