"""
Storage abstraction layer.
Supports two backends: "local" (filesystem) and "s3" (AWS S3).
Select via STORAGE_BACKEND env variable.
"""

import os
import uuid
import hashlib
import mimetypes
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)


def _get_backend() -> str:
    return current_app.config.get("STORAGE_BACKEND", "local").lower()


# ---------------------------------------------------------------------------
# Internal filename helpers
# ---------------------------------------------------------------------------

def generate_storage_key(original_filename: str) -> str:
    """Generate a unique, filesystem-safe storage key."""
    ext = Path(original_filename).suffix.lower()
    unique = uuid.uuid4().hex
    return f"{unique}{ext}"


def guess_mime_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


# ---------------------------------------------------------------------------
# Local filesystem backend
# ---------------------------------------------------------------------------

def _local_upload_dir() -> str:
    d = current_app.config["LOCAL_UPLOAD_DIR"]
    if not os.path.isabs(d):
        d = os.path.abspath(os.path.join(os.path.dirname(current_app.root_path), d))
    os.makedirs(d, exist_ok=True)
    return d


def local_save(file_stream, storage_key: str) -> int:
    """Save a file stream to local storage. Returns bytes written."""
    dest = os.path.join(_local_upload_dir(), storage_key)
    total = 0
    with open(dest, "wb") as f:
        for chunk in iter(lambda: file_stream.read(65536), b""):
            f.write(chunk)
            total += len(chunk)
    return total


def local_delete(storage_key: str):
    path = os.path.join(_local_upload_dir(), storage_key)
    try:
        os.remove(path)
    except FileNotFoundError:
        logger.warning("local_delete: file not found: %s", path)


def local_get_path(storage_key: str) -> str:
    return os.path.abspath(os.path.join(_local_upload_dir(), storage_key))


# ---------------------------------------------------------------------------
# AWS S3 backend
# ---------------------------------------------------------------------------

def _s3_client():
    import boto3  # imported lazily so local-only installs don't need boto3
    return boto3.client(
        "s3",
        aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
        region_name=current_app.config["AWS_REGION"],
    )


def s3_upload(file_stream, storage_key: str, mime_type: str) -> int:
    """Upload to S3. Returns the number of bytes uploaded."""
    data = file_stream.read()
    client = _s3_client()
    client.put_object(
        Bucket=current_app.config["S3_BUCKET_NAME"],
        Key=storage_key,
        Body=data,
        ContentType=mime_type,
        ServerSideEncryption="AES256",
    )
    return len(data)


def s3_delete(storage_key: str):
    client = _s3_client()
    client.delete_object(
        Bucket=current_app.config["S3_BUCKET_NAME"],
        Key=storage_key,
    )


def s3_presigned_url(storage_key: str) -> str:
    client = _s3_client()
    expiry = current_app.config.get("S3_PRESIGNED_URL_EXPIRY", 300)
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": current_app.config["S3_BUCKET_NAME"],
            "Key": storage_key,
        },
        ExpiresIn=expiry,
    )
    return url


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_file(file_stream, original_filename: str) -> dict:
    """
    Upload a file using the configured backend.

    Returns a dict:
      - storage_key (str)
      - mime_type   (str)
      - file_size   (int, bytes)
    """
    storage_key = generate_storage_key(original_filename)
    mime_type = guess_mime_type(original_filename)
    backend = _get_backend()

    if backend == "s3":
        size = s3_upload(file_stream, storage_key, mime_type)
    else:
        size = local_save(file_stream, storage_key)

    return {"storage_key": storage_key, "mime_type": mime_type, "file_size": size}


def delete_file(storage_key: str):
    """Delete a file from the configured backend."""
    if _get_backend() == "s3":
        s3_delete(storage_key)
    else:
        local_delete(storage_key)


def get_download_response(file_obj):
    """
    For S3: return a presigned redirect URL string.
    For local: return the absolute filesystem path string.
    The caller (route) decides how to serve it.
    """
    if _get_backend() == "s3":
        return ("s3_redirect", s3_presigned_url(file_obj.storage_key))
    else:
        return ("local_path", local_get_path(file_obj.storage_key))
