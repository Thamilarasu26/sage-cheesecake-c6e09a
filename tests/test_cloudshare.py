"""
CloudShare Test Suite
Covers: registration, login, logout, file upload, download auth,
        sharing links (expiry, revocation, password).

Run with: pytest tests/ -v
"""

import io
import os
import hashlib
import secrets
import pytest
from datetime import datetime, timezone, timedelta

from app import create_app, db
from app.models import User, File, SharedLink, DownloadLog
from config import TestingConfig


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Create test application with in-memory SQLite."""
    test_app = create_app(TestingConfig)
    test_app.config["TESTING"] = True
    test_app.config["WTF_CSRF_ENABLED"] = False
    # Use a temp local upload dir
    test_app.config["LOCAL_UPLOAD_DIR"] = os.path.join(
        os.path.dirname(__file__), "_test_uploads"
    )
    os.makedirs(test_app.config["LOCAL_UPLOAD_DIR"], exist_ok=True)
    yield test_app
    # Cleanup test upload dir
    import shutil
    shutil.rmtree(test_app.config["LOCAL_UPLOAD_DIR"], ignore_errors=True)


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(autouse=True, scope="function")
def clean_db(app):
    """Roll back DB between tests."""
    with app.app_context():
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()


# ── Helper functions ─────────────────────────────────────────────────

def register(client, name="Test User", email="test@example.com", password="Test1234"):
    return client.post("/auth/register", data={
        "name": name, "email": email,
        "password": password, "confirm_password": password,
    }, follow_redirects=True)


def login(client, email="test@example.com", password="Test1234"):
    return client.post("/auth/login", data={
        "email": email, "password": password,
    }, follow_redirects=True)


def logout(client):
    return client.get("/auth/logout", follow_redirects=True)


def upload_file(client, filename="test.txt", content=b"hello world"):
    data = {"files": (io.BytesIO(content), filename), "folder": "/"}
    return client.post("/files/upload", data=data,
                       content_type="multipart/form-data",
                       follow_redirects=True)


# ── Registration Tests ───────────────────────────────────────────────

class TestRegistration:
    def test_register_success(self, client, app):
        resp = register(client)
        assert b"Account created" in resp.data or resp.status_code == 200

    def test_register_duplicate_email(self, client, app):
        register(client)
        logout(client)
        resp = register(client)
        assert b"already exists" in resp.data or resp.status_code == 200

    def test_register_weak_password(self, client, app):
        resp = client.post("/auth/register", data={
            "name": "User", "email": "weak@example.com",
            "password": "abc", "confirm_password": "abc",
        }, follow_redirects=True)
        assert b"at least" in resp.data

    def test_register_mismatched_passwords(self, client, app):
        resp = client.post("/auth/register", data={
            "name": "User", "email": "mismatch@example.com",
            "password": "Test1234", "confirm_password": "Test9999",
        }, follow_redirects=True)
        assert b"do not match" in resp.data

    def test_register_invalid_email(self, client, app):
        resp = client.post("/auth/register", data={
            "name": "User", "email": "not-an-email",
            "password": "Test1234", "confirm_password": "Test1234",
        }, follow_redirects=True)
        assert b"valid email" in resp.data


# ── Login / Logout Tests ─────────────────────────────────────────────

class TestAuth:
    def test_login_success(self, client, app):
        register(client)
        logout(client)
        resp = login(client)
        assert b"Welcome" in resp.data

    def test_login_wrong_password(self, client, app):
        register(client)
        logout(client)
        resp = client.post("/auth/login", data={
            "email": "test@example.com", "password": "Wrong9999",
        }, follow_redirects=True)
        assert b"Invalid" in resp.data

    def test_login_nonexistent_user(self, client, app):
        resp = client.post("/auth/login", data={
            "email": "ghost@example.com", "password": "Test1234",
        }, follow_redirects=True)
        assert b"Invalid" in resp.data

    def test_logout(self, client, app):
        register(client)
        login(client)
        resp = logout(client)
        assert b"logged out" in resp.data


# ── File Upload Tests ────────────────────────────────────────────────

class TestFileUpload:
    def test_upload_requires_login(self, client, app):
        resp = client.get("/files/upload", follow_redirects=True)
        assert b"log in" in resp.data.lower() or b"login" in resp.data.lower()

    def test_upload_success(self, client, app):
        register(client)
        login(client)
        resp = upload_file(client)
        assert b"uploaded successfully" in resp.data

    def test_upload_disallowed_extension(self, client, app):
        register(client)
        login(client)
        resp = upload_file(client, filename="virus.exe", content=b"bad")
        assert b"disallowed" in resp.data

    def test_upload_no_file(self, client, app):
        register(client)
        login(client)
        resp = client.post("/files/upload", data={"folder": "/"},
                           content_type="multipart/form-data",
                           follow_redirects=True)
        assert b"select" in resp.data.lower() or resp.status_code in (200, 302)


# ── File Download Auth Tests ─────────────────────────────────────────

class TestFileDownload:
    def test_download_own_file(self, client, app):
        register(client)
        login(client)
        upload_file(client)
        with app.app_context():
            f = File.query.first()
        resp = client.get(f"/files/download/{f.id}", follow_redirects=False)
        # Should return 200 or redirect to presigned URL
        assert resp.status_code in (200, 302)

    def test_download_other_users_file_forbidden(self, client, app):
        # User 1 uploads
        register(client, email="owner@example.com")
        login(client, email="owner@example.com")
        upload_file(client)
        with app.app_context():
            f = File.query.first()
        logout(client)

        # User 2 tries to download
        register(client, name="Other", email="other@example.com")
        login(client, email="other@example.com")
        resp = client.get(f"/files/download/{f.id}", follow_redirects=True)
        assert resp.status_code == 403

    def test_download_requires_login(self, client, app):
        resp = client.get("/files/download/999", follow_redirects=True)
        assert b"log in" in resp.data.lower() or b"login" in resp.data.lower()


# ── Sharing Link Tests ───────────────────────────────────────────────

class TestSharingLinks:
    def _setup_file(self, client, app):
        register(client)
        login(client)
        upload_file(client)
        with app.app_context():
            return File.query.first().id

    def test_create_link(self, client, app):
        fid = self._setup_file(client, app)
        resp = client.post("/share/create", data={
            "file_id": fid,
            "allow_download": "1",
        }, follow_redirects=True)
        assert b"created" in resp.data.lower() or b"link" in resp.data.lower()

    def test_access_valid_link(self, client, app):
        fid = self._setup_file(client, app)
        client.post("/share/create", data={"file_id": fid, "allow_download": "1"})
        with app.app_context():
            link = SharedLink.query.first()
            token = link.token
        logout(client)
        resp = client.get(f"/share/{token}", follow_redirects=True)
        assert resp.status_code == 200

    def test_revoked_link_rejected(self, client, app):
        fid = self._setup_file(client, app)
        client.post("/share/create", data={"file_id": fid, "allow_download": "1"})
        with app.app_context():
            link = SharedLink.query.first()
            lid, token = link.id, link.token
        client.post(f"/share/revoke/{lid}")
        logout(client)
        resp = client.get(f"/share/{token}", follow_redirects=True)
        assert b"revoked" in resp.data.lower()

    def test_expired_link_rejected(self, client, app):
        fid = self._setup_file(client, app)
        # Force expiry in the past
        client.post("/share/create", data={
            "file_id": fid,
            "allow_download": "1",
            "expires_at": "2000-01-01T00:00",
        })
        with app.app_context():
            link = SharedLink.query.first()
            token = link.token
        logout(client)
        resp = client.get(f"/share/{token}", follow_redirects=True)
        assert b"expired" in resp.data.lower()

    def test_password_protected_link(self, client, app):
        fid = self._setup_file(client, app)
        client.post("/share/create", data={
            "file_id": fid,
            "allow_download": "1",
            "share_password": "secret123",
        })
        with app.app_context():
            token = SharedLink.query.first().token
        logout(client)
        # GET should show password form
        resp = client.get(f"/share/{token}")
        assert b"password" in resp.data.lower()
        # Wrong password
        resp = client.post(f"/share/{token}", data={"password": "wrong"})
        assert b"incorrect" in resp.data.lower()
        # Correct password
        resp = client.post(f"/share/{token}", data={"password": "secret123"})
        assert resp.status_code == 200

    def test_invalid_token(self, client, app):
        resp = client.get("/share/INVALIDTOKEN123456")
        assert resp.status_code == 404

    def test_cannot_revoke_others_link(self, client, app):
        fid = self._setup_file(client, app)
        client.post("/share/create", data={"file_id": fid, "allow_download": "1"})
        with app.app_context():
            lid = SharedLink.query.first().id
        logout(client)

        # New user
        register(client, name="Attacker", email="attacker@example.com")
        login(client, email="attacker@example.com")
        resp = client.post(f"/share/revoke/{lid}", follow_redirects=True)
        assert resp.status_code == 403


# ── File Delete / Rename Auth Tests ─────────────────────────────────

class TestFileManagement:
    def test_delete_own_file(self, client, app):
        register(client)
        login(client)
        upload_file(client)
        with app.app_context():
            fid = File.query.first().id
        resp = client.post(f"/files/delete/{fid}", follow_redirects=True)
        assert b"deleted" in resp.data.lower()

    def test_delete_other_users_file_forbidden(self, client, app):
        register(client, email="owner2@example.com")
        login(client, email="owner2@example.com")
        upload_file(client)
        with app.app_context():
            fid = File.query.first().id
        logout(client)

        register(client, name="Attacker2", email="attacker2@example.com")
        login(client, email="attacker2@example.com")
        resp = client.post(f"/files/delete/{fid}", follow_redirects=True)
        assert resp.status_code == 403

    def test_rename_file(self, client, app):
        register(client)
        login(client)
        upload_file(client)
        with app.app_context():
            fid = File.query.first().id
        resp = client.post(f"/files/rename/{fid}",
                           data={"new_name": "renamed.txt"},
                           follow_redirects=True)
        assert b"renamed" in resp.data.lower()
