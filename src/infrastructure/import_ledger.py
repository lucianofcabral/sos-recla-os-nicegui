"""Import ledger: idempotency bookkeeping for the historical import.

The ledger lives in the destination database (not in the legacy ``aux_*``
tables, which belong to an older migration of the legacy app). Each imported
legacy row is recorded as ``(old_table, old_id) -> (new_table, new_id)`` so
re-runs can skip what is already migrated and resolve old->new id links within
the same run.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlmodel import Session

CREATE_IMPORT_LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS import_ledger (
    old_table TEXT NOT NULL,
    old_id INTEGER NOT NULL,
    new_table TEXT NOT NULL,
    new_id INTEGER NOT NULL,
    PRIMARY KEY (old_table, old_id)
)
"""

LedgerRow = tuple[str, int, str, int]


def create_import_ledger(session: Session) -> None:
    """Create the import ledger table if missing (idempotent)."""
    session.execute(text(CREATE_IMPORT_LEDGER_SQL))
    session.commit()


class SqlModelImportLedger:
    """Ledger of old->new id mappings stored in the destination database."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def read(self) -> dict[tuple[str, int], int]:
        """Return ``{(old_table, old_id): new_id}`` for every ledge row."""
        rows = self._session.exec(
            text('SELECT old_table, old_id, new_id FROM import_ledger')
        ).all()
        result: dict[tuple[str, int], int] = {}
        for row in rows:
            result[(str(row[0]), int(row[1]))] = int(row[2])
        return result

    def write(self, rows: Sequence[LedgerRow]) -> None:
        """Insert ledger rows into the current session (not yet committed)."""
        if not rows:
            return
        insert = text(
            'INSERT INTO import_ledger (old_table, old_id, new_table, new_id) '
            'VALUES (:old_table, :old_id, :new_table, :new_id)'
        )
        for old_table, old_id, new_table, new_id in rows:
            params: dict[str, Any] = {
                'old_table': old_table,
                'old_id': old_id,
                'new_table': new_table,
                'new_id': new_id,
            }
            self._session.execute(insert, params)
