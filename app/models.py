"""
Database models for CloudShare.
Tables: User, File, SharedLink, DownloadLog
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def now_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc, nullable=False)

    # relationships
    files = db.relationship(
        "File", backref="owner", lazy="dynamic", cascade="all, delete-orphan"
    )
    shared_links = db.relationship(
        "SharedLink", backref="creator", lazy="dynamic", foreign_keys="SharedLink.created_by"
    )

    # ------------------------------------------------------------------
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------
class File(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(512), unique=True, nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.BigInteger, default=0)
    folder = db.Column(db.String(255), nullable=True, default="/")
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc, nullable=False)

    shared_links = db.relationship(
        "SharedLink", backref="file", lazy="dynamic", cascade="all, delete-orphan"
    )
    download_logs = db.relationship(
        "DownloadLog", backref="file", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def size_human(self):
        """Return a human-readable file size."""
        size = self.file_size or 0
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def extension(self):
        name = self.original_filename or ""
        return name.rsplit(".", 1)[-1].lower() if "." in name else ""

    def __repr__(self):
        return f"<File {self.original_filename}>"


# ---------------------------------------------------------------------------
# SharedLink
# ---------------------------------------------------------------------------
class SharedLink(db.Model):
    __tablename__ = "shared_links"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(
        db.Integer, db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # We store the random token in plaintext for URL construction,
    # but keep a SHA-256 hash for DB lookup to prevent timing attacks.
    token = db.Column(db.String(64), unique=True, nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    allow_download = db.Column(db.Boolean, default=True, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)

    download_logs = db.relationship(
        "DownloadLog", backref="shared_link", lazy="dynamic"
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return now_utc() > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def is_active(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def __repr__(self):
        return f"<SharedLink file_id={self.file_id}>"


# ---------------------------------------------------------------------------
# DownloadLog
# ---------------------------------------------------------------------------
class DownloadLog(db.Model):
    __tablename__ = "download_logs"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(
        db.Integer, db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shared_link_id = db.Column(
        db.Integer, db.ForeignKey("shared_links.id", ondelete="SET NULL"), nullable=True
    )
    ip_address = db.Column(db.String(45), nullable=True)
    accessed_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    outcome = db.Column(db.String(50), default="success")   # success / denied / expired

    def __repr__(self):
        return f"<DownloadLog file_id={self.file_id} outcome={self.outcome}>"
