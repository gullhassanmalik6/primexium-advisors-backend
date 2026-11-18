"""Compatibility shim — uploads now use Railway local disk storage."""

from app.core.file_storage import (  # noqa: F401
    ALLOWED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    upload_document,
)
