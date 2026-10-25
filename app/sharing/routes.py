"""
Sharing routes: create link, revoke link, access shared file.
"""

import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from flask import (
    render_template, redirect, url_for, flash,
    request, abort, send_file, current_app
)
from flask_login import login_required, current_user

from app import db, limiter
from app.models import File, SharedLink, DownloadLog
from app.sharing import sharing_bp
from app.storage.backend import get_download_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _log(file_id, sl_id, outcome):
    log = DownloadLog(
        file_id=file_id,
        shared_link_id=sl_id,
        ip_address=request.remote_addr,
        outcome=outcome,
    )
    db.session.add(log)
    db.session.commit()


# ---------------------------------------------------------------------------
# Manage links (authenticated owner)
# ---------------------------------------------------------------------------

@sharing_bp.route("/manage")
@login_required
def manage():
    links = (
        SharedLink.query
        .join(File)
        .filter(File.owner_id == current_user.id)
        .order_by(SharedLink.created_at.desc())
        .all()
    )
    files = File.query.filter_by(owner_id=current_user.id).order_by(File.original_filename).all()
    return render_template("sharing/manage.html", links=links, files=files)


# ---------------------------------------------------------------------------
# Create sharing link
# ---------------------------------------------------------------------------

@sharing_bp.route("/create", methods=["POST"])
@login_required
def create_link():
    file_id = request.form.get("file_id", type=int)
    if not file_id:
        flash("Please select a file.", "warning")
        return redirect(url_for("sharing.manage"))

    f = db.get_or_404(File, file_id)
    if f.owner_id != current_user.id:
        abort(403)

    # Parse expiry
    expires_str = request.form.get("expires_at", "").strip()
    expires_at = None
    if expires_str:
        try:
            expires_at = datetime.strptime(expires_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Invalid expiration date format.", "danger")
            return redirect(url_for("sharing.manage"))

    # Generate cryptographically strong token
    token = secrets.token_urlsafe(32)
    th = _token_hash(token)

    # Parse options
    allow_download = bool(request.form.get("allow_download"))
    share_password = request.form.get("share_password", "").strip()

    link = SharedLink(
        file_id=file_id,
        created_by=current_user.id,
        token=token,
        token_hash=th,
        expires_at=expires_at,
        allow_download=allow_download,
    )
    if share_password:
        link.set_password(share_password)

    db.session.add(link)
    db.session.commit()
    flash("Sharing link created!", "success")
    return redirect(url_for("sharing.manage"))


# ---------------------------------------------------------------------------
# Revoke sharing link
# ---------------------------------------------------------------------------

@sharing_bp.route("/revoke/<int:link_id>", methods=["POST"])
@login_required
def revoke_link(link_id):
    link = db.get_or_404(SharedLink, link_id)
    if link.created_by != current_user.id:
        abort(403)
    link.is_revoked = True
    db.session.commit()
    flash("Sharing link revoked.", "info")
    return redirect(url_for("sharing.manage"))


# ---------------------------------------------------------------------------
# Public: access shared file
# ---------------------------------------------------------------------------

@sharing_bp.route("/<token>", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def access_shared(token):
    th = _token_hash(token)
    link = SharedLink.query.filter_by(token_hash=th).first()

    if not link:
        abort(404)

    if link.is_revoked:
        _log(link.file_id, link.id, "revoked")
        return render_template("sharing/invalid.html",
                               reason="This sharing link has been revoked.")

    if link.is_expired:
        _log(link.file_id, link.id, "expired")
        return render_template("sharing/invalid.html",
                               reason="This sharing link has expired.")

    # Password check
    needs_password = bool(link.password_hash)
    password_error = None

    if needs_password and request.method == "POST":
        pw = request.form.get("password", "")
        if not link.check_password(pw):
            password_error = "Incorrect password. Please try again."
            _log(link.file_id, link.id, "denied")
        else:
            needs_password = False   # authenticated for this request

    if needs_password and request.method == "GET":
        return render_template("sharing/password.html", token=token, error=None)

    if password_error:
        return render_template("sharing/password.html",
                               token=token, error=password_error)

    # Serve the file info / download
    f = link.file
    if request.args.get("download") and link.allow_download:
        kind, value = get_download_response(f)
        if kind == "s3_redirect":
            _log(f.id, link.id, "success")
            from flask import redirect as _redirect
            return _redirect(value)
        if not os.path.exists(value):
            flash(f"File '{f.original_filename}' is currently not available on server storage.", "warning")
            return redirect(url_for("sharing.access_link", token=token))
        _log(f.id, link.id, "success")
        return send_file(
            value,
            as_attachment=True,
            download_name=f.original_filename,
            mimetype=f.mime_type or "application/octet-stream",
        )

    _log(f.id, link.id, "view")
    return render_template("sharing/view.html", file=f, link=link, token=token)
