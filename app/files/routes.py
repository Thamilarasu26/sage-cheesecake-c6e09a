"""
File management routes: upload, list, download, rename, delete.
"""

import os
import mimetypes
from pathlib import Path
from flask import (
    render_template, redirect, url_for, flash,
    request, send_file, abort, jsonify, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.models import File, DownloadLog, SharedLink
from app.files import files_bp
from app.storage.backend import upload_file, delete_file, get_download_response


# Allowed extensions set – checked server-side
ALLOWED_EXTENSIONS = None  # populated from config in each request


def _allowed(filename: str) -> bool:
    exts = current_app.config.get("ALLOWED_EXTENSIONS", set())
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in exts


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@files_bp.route("/dashboard")
@login_required
def dashboard():
    user_files = File.query.filter_by(owner_id=current_user.id).all()
    total_files = len(user_files)
    total_size = sum(f.file_size or 0 for f in user_files)

    # shared links created by the user
    shared_count = SharedLink.query.filter_by(
        created_by=current_user.id, is_revoked=False
    ).count()

    recent = (
        File.query.filter_by(owner_id=current_user.id)
        .order_by(File.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "files/dashboard.html",
        total_files=total_files,
        total_size=total_size,
        shared_count=shared_count,
        recent_files=recent,
    )


# ---------------------------------------------------------------------------
# File Manager (list / search)
# ---------------------------------------------------------------------------
@files_bp.route("/manager")
@login_required
def manager():
    q = request.args.get("q", "").strip()
    folder = request.args.get("folder", "/")

    query = File.query.filter_by(owner_id=current_user.id)

    if q:
        query = query.filter(
            or_(
                File.original_filename.ilike(f"%{q}%"),
                File.mime_type.ilike(f"%{q}%"),
            )
        )

    files = query.order_by(File.created_at.desc()).all()

    # Collect folder list
    folders = (
        db.session.query(File.folder)
        .filter_by(owner_id=current_user.id)
        .distinct()
        .all()
    )
    folder_list = sorted({f[0] for f in folders if f[0]})

    return render_template(
        "files/manager.html",
        files=files,
        search_query=q,
        folders=folder_list,
        current_folder=folder,
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
@files_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        uploaded = request.files.getlist("files")
        folder = request.form.get("folder", "/").strip() or "/"

        if not uploaded or all(f.filename == "" for f in uploaded):
            flash("Please select at least one file.", "warning")
            return redirect(url_for("files.upload"))

        success_count = 0
        for f in uploaded:
            if not f.filename:
                continue

            if not _allowed(f.filename):
                flash(
                    f"'{f.filename}' has a disallowed file type.",
                    "danger",
                )
                continue

            # Sanitise original filename (no path components)
            safe_name = Path(f.filename).name

            # Upload to backend
            result = upload_file(f.stream, safe_name)

            file_record = File(
                owner_id=current_user.id,
                original_filename=safe_name,
                storage_key=result["storage_key"],
                mime_type=result["mime_type"],
                file_size=result["file_size"],
                folder=folder,
            )
            db.session.add(file_record)
            success_count += 1

        if success_count:
            db.session.commit()
            flash(f"{success_count} file(s) uploaded successfully.", "success")
        return redirect(url_for("files.manager"))

    return render_template("files/upload.html")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
@files_bp.route("/download/<int:file_id>")
@login_required
def download(file_id):
    f = db.get_or_404(File, file_id)

    # Ownership check
    if f.owner_id != current_user.id:
        abort(403)

    _log_download(f.id, None, "success")

    kind, value = get_download_response(f)
    if kind == "s3_redirect":
        return redirect(value)
    else:
        if not os.path.exists(value):
            flash(f"File '{f.original_filename}' could not be found on server storage.", "warning")
            return redirect(url_for("files.manager"))
        return send_file(
            value,
            as_attachment=True,
            download_name=f.original_filename,
            mimetype=f.mime_type or "application/octet-stream",
        )


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------
@files_bp.route("/rename/<int:file_id>", methods=["POST"])
@login_required
def rename(file_id):
    f = db.get_or_404(File, file_id)
    if f.owner_id != current_user.id:
        abort(403)

    new_name = request.form.get("new_name", "").strip()
    if not new_name:
        flash("File name cannot be empty.", "danger")
    elif not _allowed(new_name):
        flash("That file extension is not allowed.", "danger")
    else:
        f.original_filename = Path(new_name).name
        db.session.commit()
        flash("File renamed successfully.", "success")

    return redirect(url_for("files.manager"))


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@files_bp.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete(file_id):
    f = db.get_or_404(File, file_id)
    if f.owner_id != current_user.id:
        abort(403)

    key = f.storage_key
    db.session.delete(f)
    db.session.commit()

    try:
        delete_file(key)
    except Exception as e:
        current_app.logger.error("Storage delete failed: %s", e)

    flash("File deleted.", "success")
    return redirect(url_for("files.manager"))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _log_download(file_id, shared_link_id, outcome):
    log = DownloadLog(
        file_id=file_id,
        shared_link_id=shared_link_id,
        ip_address=request.remote_addr,
        outcome=outcome,
    )
    db.session.add(log)
    db.session.commit()
