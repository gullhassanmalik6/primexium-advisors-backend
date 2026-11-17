"""Phone number normalisation helpers for duplicate detection."""

from __future__ import annotations

import re


def normalize_phone(value: str | None) -> str | None:
    """Return digits-only E.164-ish form, or None if empty/invalid."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    # Keep leading + for international, then strip non-digits except leading +
    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7 or len(digits) > 15:
        return None
    return f"+{digits}" if has_plus or len(digits) > 10 else digits


def is_valid_phone(value: str | None, *, required: bool = False) -> bool:
    if value is None or not str(value).strip():
        return not required
    return normalize_phone(value) is not None


def sanitize_text(value: str | None, *, max_length: int = 255) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        return None
    return cleaned[:max_length]
