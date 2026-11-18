"""Unit tests for local Railway file storage helpers."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core import file_storage


def test_save_and_resolve_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(file_storage.settings, "upload_dir", str(tmp_path))
    key = file_storage.save_upload(
        BytesIO(b"%PDF-1.4 demo"),
        filename="rent-receipt.pdf",
        content_type="application/pdf",
        folder="finance/demo",
    )
    assert key.startswith("finance/demo/")
    assert key.endswith(".pdf")
    path = file_storage.resolve_path(key)
    assert path.is_file()
    assert path.read_bytes().startswith(b"%PDF")
    file_storage.delete_upload(key)
    assert not path.exists()


def test_rejects_bad_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(file_storage.settings, "upload_dir", str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        file_storage.save_upload(
            BytesIO(b"hello"),
            filename="notes.txt",
            content_type="text/plain",
            folder="finance/demo",
        )
    assert exc.value.status_code == 400
