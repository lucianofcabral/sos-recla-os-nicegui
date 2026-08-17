"""NiceGUI application entrypoint (run with `uv run python -m src.ui.main`)."""

from __future__ import annotations

import os

from nicegui import ui

from src.infrastructure.database import build_engine, create_schema

UI_HOST = os.getenv('UI_HOST', '127.0.0.1')
UI_PORT = int(os.getenv('UI_PORT', '8081'))
STORAGE_SECRET = os.getenv('STORAGE_SECRET', 'sos-reclamos-dev-secret')


def start() -> None:
    """Create the schema if needed and start the NiceGUI server."""
    create_schema(build_engine())
    ui.run(
        host=UI_HOST,
        port=UI_PORT,
        title='SOS Reclamos',
        language='es',
        dark=True,
        storage_secret=STORAGE_SECRET,
        reload=False,
    )


if __name__ == '__main__':
    start()
