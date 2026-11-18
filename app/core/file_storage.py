"""Local file storage for Railway volumes (no third-party object storage)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, status

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _root() -> Path:
    root = Path(settings.upload_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _extension(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    if content_type and content_type in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[content_type]
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Only PDF, JPG, PNG, and WEBP files are allowed",
    )


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem.strip() or "file"
    cleaned = _SAFE_NAME.sub("_", stem).strip("._") or "file"
    return cleaned[:80]


def is_remote_url(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith("http://") or value.startswith("https://")


def save_upload(
    file_obj: BinaryIO,
    *,
    filename: str,
    content_type: str | None,
    folder: str = "uploads",
) -> str:
    """Save a file under UPLOAD_DIR and return a relative storage key."""
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG, PNG, and WEBP files are allowed",
        )

    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    if size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be 8 MB or less",
        )

    ext = _extension(filename, content_type)
    relative_folder = folder.strip("/").replace("\\", "/")
    stored_name = f"{uuid.uuid4().hex}_{_safe_stem(filename)}{ext}"
    relative_key = f"{relative_folder}/{stored_name}"

    destination = resolve_path(relative_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as out:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {exc}",
        ) from exc

    return relative_key


def resolve_path(storage_key: str) -> Path:
    if not storage_key or is_remote_url(storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    root = _root()
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path") from exc
    return candidate


def delete_upload(storage_key: str | None) -> None:
    if not storage_key or is_remote_url(storage_key):
        return
    path = resolve_path(storage_key)
    if path.is_file():
        path.unlink(missing_ok=True)


def content_type_for_key(storage_key: str) -> str:
    suffix = Path(storage_key).suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    return mapping.get(suffix, "application/octet-stream")


# Backwards-compatible name used by existing endpoints
def upload_document(
    file_obj: BinaryIO,
    *,
    filename: str,
    content_type: str | None,
    folder: str = "primexium/documents",
) -> str:
    return save_upload(
        file_obj,
        filename=filename,
        content_type=content_type,
        folder=folder,
    )
