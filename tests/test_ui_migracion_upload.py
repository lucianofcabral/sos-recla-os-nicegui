"""Tests for the migration page ZIP/DB upload helper (`_prepare_upload`)."""

from __future__ import annotations

import io
import shutil
import sqlite3
import zipfile
from pathlib import Path

from src.ui.pages.migracion import _prepare_upload


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE gestiones (id INTEGER PRIMARY KEY, ngestion INTEGER)')
    conn.commit()
    conn.close()


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_prepare_upload_accepts_plain_db(tmp_path: Path) -> None:
    db_file = tmp_path / 'gestiones.db'
    _make_db(db_file)
    db_path, workspace = _prepare_upload('gestiones.db', db_file.read_bytes())
    try:
        assert Path(db_path).name == 'gestiones.db'
        assert sqlite3.connect(db_path).execute('SELECT 1').fetchone() == (1,)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_prepare_upload_zip_with_db_attachments_in_files_docs(
    tmp_path: Path,
) -> None:
    """Los adjuntos dentro de files/docs pueden tener extensión .db; no deben
    confundirse con la base legada (que vive en la raíz del ZIP)."""
    db_file = tmp_path / 'gestiones.db'
    _make_db(db_file)
    zip_bytes = _make_zip(
        {
            'gestiones.db': db_file.read_bytes(),
            'files/docs/adjunto1.db': b'contenido adjunto',
            'files/docs/adjunto2.pdf': b'%PDF-1.4',
        }
    )
    db_path, workspace = _prepare_upload('migracion.zip', zip_bytes)
    try:
        assert Path(db_path).name == 'gestiones.db'
        assert Path(workspace, 'files/docs/adjunto1.db').exists()
        assert Path(workspace, 'files/docs/adjunto2.pdf').exists()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_prepare_upload_zip_without_db_rejected(tmp_path: Path) -> None:
    zip_bytes = _make_zip({'files/docs/x.pdf': b'%PDF'})
    try:
        _prepare_upload('migracion.zip', zip_bytes)
    except ValueError as exc:
        assert 'exactamente una base .db' in str(exc)
    else:
        raise AssertionError('Se esperaba ValueError')


def test_prepare_upload_zip_with_two_roots_rejected(tmp_path: Path) -> None:
    db_file = tmp_path / 'gestiones.db'
    _make_db(db_file)
    zip_bytes = _make_zip(
        {
            'gestiones.db': db_file.read_bytes(),
            'otra.db': db_file.read_bytes(),
        }
    )
    try:
        _prepare_upload('migracion.zip', zip_bytes)
    except ValueError as exc:
        assert 'exactamente una base .db' in str(exc)
    else:
        raise AssertionError('Se esperaba ValueError')
