import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Environment variables win; load the root .env before the legacy backend file.
load_dotenv(os.path.join(PROJECT_DIR, ".env"), override=False)
if os.environ.get("FLASK_ENV", "development").lower() != "production":
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)


def get_database_url(production=False):
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url and not any(value in url for value in ("YOUR_DB_PASSWORD", "YOUR_PROJECT_REF", "[YOUR-PASSWORD]", "[PROJECT-REF]")):
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        if production and not url.startswith("postgresql+psycopg://"):
            raise RuntimeError("DATABASE_URL must use Supabase PostgreSQL with the psycopg driver in production.")
        return url

    if production or os.environ.get("FLASK_ENV", "development").lower() == "production":
        raise RuntimeError("DATABASE_URL must be set to the Supabase PostgreSQL connection string in production.")

    # Fallback to local SQLite instance storage
    instance_dir = os.path.join(BASE_DIR, "instance")
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, "civiclens.db").replace("\\", "/")
    return f"sqlite:///{db_path}"


_db_url = get_database_url()

class Config:
    """Flask settings supporting Supabase PostgreSQL and local-development SQLite."""
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    if _db_url.startswith("sqlite:"):
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_size": 1,
            "max_overflow": 0,
            "pool_recycle": 300,
            "connect_args": {"sslmode": "require", "prepare_threshold": None},
        }

    CORS_ORIGINS = [
        origin.strip() for origin in os.environ.get(
            "CORS_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5500,http://localhost:5500"
        ).split(",") if origin.strip()
    ]


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = "production"
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
