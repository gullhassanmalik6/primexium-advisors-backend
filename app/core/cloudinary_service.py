from __future__ import annotations

from typing import BinaryIO

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status

from app.core.config import settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    if not (
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File upload is not configured. Set Cloudinary credentials on the server.",
        )
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    _configured = True


ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


def upload_document(
    file_obj: BinaryIO,
    *,
    filename: str,
    content_type: str | None,
    folder: str = "primexium/documents",
) -> str:
    _ensure_configured()

    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG, PNG, and WEBP files are allowed",
        )

    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be 8 MB or less",
        )

    resource_type = "image" if content_type and content_type.startswith("image/") else "raw"

    try:
        result = cloudinary.uploader.upload(
            file_obj,
            folder=folder,
            resource_type=resource_type,
            public_id=filename.rsplit(".", 1)[0] if filename else None,
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload failed: {exc}",
        ) from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upload succeeded but no file URL was returned",
        )
    return str(url)
