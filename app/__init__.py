"""
CloudShare Application Factory
Initialises Flask extensions and registers all blueprints.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Extension singletons (initialised without app in create_app)
# ---------------------------------------------------------------------------
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_object=None):
    """Application factory."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ------------------------------------------------------------------
    # Load configuration
    # ------------------------------------------------------------------
    if config_object is None:
        from config import get_config
        config_object = get_config()

    app.config.from_object(config_object)

    # ------------------------------------------------------------------
    # Ensure local upload directory exists
    # ------------------------------------------------------------------
    upload_dir = app.config.get("LOCAL_UPLOAD_DIR", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Check Database Connection (graceful MySQL fallback to SQLite)
    # ------------------------------------------------------------------
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("mysql"):
        try:
            from sqlalchemy import create_engine
            eng = create_engine(db_uri, connect_args={"connect_timeout": 2})
            with eng.connect():
                pass
        except Exception:
            fallback_db = "sqlite:///cloudshare.db"
            print(f"[CloudShare] Notice: MySQL server not reachable. Falling back to local SQLite ({fallback_db}) for seamless local development.")
            app.config["SQLALCHEMY_DATABASE_URI"] = fallback_db

    # ------------------------------------------------------------------
    # Initialise extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # ------------------------------------------------------------------
    # User loader for Flask-Login
    # ------------------------------------------------------------------
    from app.models import User  # noqa: E402

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------
    # Register Blueprints
    # ------------------------------------------------------------------
    from app.auth.routes import auth_bp
    from app.files.routes import files_bp
    from app.sharing.routes import sharing_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(files_bp, url_prefix="/files")
    app.register_blueprint(sharing_bp, url_prefix="/share")

    # ------------------------------------------------------------------
    # Custom Jinja2 filters and globals
    # ------------------------------------------------------------------
    _file_icon_map = {
        "pdf": "bi-file-earmark-pdf", "doc": "bi-file-earmark-word",
        "docx": "bi-file-earmark-word", "xls": "bi-file-earmark-excel",
        "xlsx": "bi-file-earmark-excel", "ppt": "bi-file-earmark-ppt",
        "pptx": "bi-file-earmark-ppt", "png": "bi-file-earmark-image",
        "jpg": "bi-file-earmark-image", "jpeg": "bi-file-earmark-image",
        "gif": "bi-file-earmark-image", "bmp": "bi-file-earmark-image",
        "svg": "bi-file-earmark-image", "zip": "bi-file-earmark-zip",
        "tar": "bi-file-earmark-zip", "gz": "bi-file-earmark-zip",
        "mp3": "bi-file-earmark-music", "mp4": "bi-file-earmark-play",
        "mov": "bi-file-earmark-play", "avi": "bi-file-earmark-play",
        "mkv": "bi-file-earmark-play", "txt": "bi-file-earmark-text",
        "csv": "bi-file-earmark-spreadsheet", "json": "bi-file-earmark-code",
        "xml": "bi-file-earmark-code", "html": "bi-file-earmark-code",
        "css": "bi-file-earmark-code", "js": "bi-file-earmark-code",
        "py": "bi-file-earmark-code", "java": "bi-file-earmark-code",
        "c": "bi-file-earmark-code", "cpp": "bi-file-earmark-code",
    }

    @app.template_global()
    def file_icon(ext: str) -> str:
        return _file_icon_map.get(ext.lower(), "bi-file-earmark")

    # ------------------------------------------------------------------
    # Create DB tables (development convenience)
    # ------------------------------------------------------------------
    with app.app_context():
        db.create_all()

    return app
