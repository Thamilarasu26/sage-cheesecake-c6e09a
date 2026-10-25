"""
CloudShare Configuration Module
Loads all settings from environment variables using python-dotenv.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class BaseConfig:
    """Base configuration shared across all environments."""

    # Flask core
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-me-in-production-please"
    DEBUG = False
    TESTING = False

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Session / Cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # File upload limits
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

    # Storage backend: "local" or "s3"
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")

    # Local storage path (outside web-accessible static folder, always absolute)
    _raw_upload_dir = os.environ.get("LOCAL_UPLOAD_DIR", "uploads")
    if os.path.isabs(_raw_upload_dir):
        LOCAL_UPLOAD_DIR = _raw_upload_dir
    else:
        LOCAL_UPLOAD_DIR = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), _raw_upload_dir)
        )

    # AWS S3
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    S3_PRESIGNED_URL_EXPIRY = int(os.environ.get("S3_PRESIGNED_URL_EXPIRY", 300))  # seconds

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        "txt", "pdf", "png", "jpg", "jpeg", "gif", "bmp", "svg",
        "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "csv", "json", "xml", "zip", "tar", "gz",
        "mp3", "mp4", "mov", "avi", "mkv",
        "py", "js", "html", "css", "java", "c", "cpp",
    }

    # Rate limiting (requests per minute per IP for sensitive routes)
    LOGIN_RATE_LIMIT = "10 per minute"
    SHARE_ACCESS_RATE_LIMIT = "20 per minute"
    RATELIMIT_STORAGE_URI = "memory://"

    # WTF / CSRF
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour


class DevelopmentConfig(BaseConfig):
    """Development-specific configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost/cloudshare_db",
    )
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    """Production-specific configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or ""
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"

    @classmethod
    def validate(cls):
        """Raise if required production variables are missing."""
        required = ["SECRET_KEY", "DATABASE_URL", "AWS_ACCESS_KEY_ID",
                    "AWS_SECRET_ACCESS_KEY", "S3_BUCKET_NAME"]
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            raise RuntimeError(f"Missing production env vars: {missing}")


class TestingConfig(BaseConfig):
    """Testing configuration using an in-memory SQLite database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    STORAGE_BACKEND = "local"
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


# Map environment names to config classes
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the active configuration class based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
