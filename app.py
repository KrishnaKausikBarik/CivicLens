"""Vercel and local WSGI entry point for CivicLens."""
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_DIR / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from Backend.app import app, create_app  # noqa: E402
from utils.request_logging import RedactingWSGIRequestHandler  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"CivicLens server listening at http://{host}:{port}")
    app.run(
        host=host,
        port=port,
        debug=os.environ.get("FLASK_ENV", "development").lower() != "production",
        request_handler=RedactingWSGIRequestHandler,
    )
