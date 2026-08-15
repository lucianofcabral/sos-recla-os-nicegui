"""Migrate an existing SQLite development database into PostgreSQL.

Copies every table defined by the current SQLModel metadata (plus the
``import_ledger`` infra table when present) from an SQLite source into the
PostgreSQL database configured in ``DATABASE_URL``. IDs are preserved so
foreign keys keep working, and PostgreSQL sequences are re-synced afterwards.

Usage:
    DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname" \\
        uv run python scripts/migrate_sqlite_to_postgres.py [--sqlite sqlite:///sos.db] [--apply]

Safeguards:
- Dry-run by default: only reports rows per table; ``--apply`` writes.
- Skips a destination table that already has rows (unless ``--force``).
- Copies only tables present in the current schema; legacy leftovers such as
  the old ``especiales`` table are ignored with a warning.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Boolean, Column, Engine, Table, inspect, text
from sqlmodel import Session, SQLModel

from src.adapters.sqlmodel import models  # noqa: F401  (registers tables)
from src.infrastructure.database import build_engine, create_schema

# Raw infra tables that live outside SQLModel.metadata (kept in sync manually).
EXTRA_TABLES: tuple[str, ...] = ('import_ledger',)

IMPORT_LEDGER_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS import_ledger (
    old_table TEXT NOT NULL,
    old_id INTEGER NOT NULL,
    new_table TEXT NOT NULL,
    new_id INTEGER NOT NULL,
    PRIMARY KEY (old_table, old_id)
)
"""


def _normalize(value: object, column: Column[object]) -> object:
    """Convert a value read from SQLite into a form PostgreSQL accepts."""
    if value is None:
        return None
    if isinstance(column.type, Boolean):
        # SQLite stores booleans as 0/1 ints; psycopg rejects ints for BOOLEAN.
        return bool(value)
    return value


def _copy_table(src: Session, dst: Session, table: Table) -> int:
    """Copy one SQLModel table from the SQLite source into PostgreSQL.

    Returns the number of rows inserted.
    """
    rows = src.exec(table.select()).mappings().all()
    if not rows:
        return 0
    insert = table.insert()
    for row in rows:
        values = {
            column.name: _normalize(row[column.name], column)
            for column in table.columns
        }
        dst.execute(insert, values)
    return len(rows)


def _copy_import_ledger(src: Session, dst: Session) -> int:
    """Copy the raw ``import_ledger`` table when it exists in the source."""
    rows = src.execute(
        text('SELECT old_table, old_id, new_table, new_id FROM import_ledger')
    ).all()
    if not rows:
        return 0
    dst.execute(text(IMPORT_LEDGER_CREATE_SQL))
    insert = text(
        'INSERT INTO import_ledger (old_table, old_id, new_table, new_id) '
        'VALUES (:old_table, :old_id, :new_table, :new_id)'
    )
    for old_table, old_id, new_table, new_id in rows:
        dst.execute(
            insert,
            {
                'old_table': str(old_table),
                'old_id': int(old_id),
                'new_table': str(new_table),
                'new_id': int(new_id),
            },
        )
    return len(rows)


def _reset_sequences(dst_engine: Engine, table_names: Sequence[str]) -> None:
    """Re-sync PostgreSQL identity sequences after explicit-ID inserts."""
    with dst_engine.connect() as conn:
        for name in table_names:
            max_id = conn.execute(
                text(f'SELECT COALESCE(MAX(id), 0) FROM {name}')
            ).scalar_one()
            if max_id > 0:
                conn.execute(
                    text(
                        'SELECT setval('
                        f"pg_get_serial_sequence('{name}', 'id'), "
                        ':max_id, true)'
                    ),
                    {'max_id': max_id},
                )
            else:
                conn.execute(
                    text(
                        'SELECT setval('
                        f"pg_get_serial_sequence('{name}', 'id'), "
                        '1, false)'
                    )
                )
        conn.commit()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Migrar una base SQLite de desarrollo a PostgreSQL.'
    )
    parser.add_argument(
        '--sqlite',
        default='sqlite:///sos.db',
        help='URL de la base SQLite de origen (default: sqlite:///sos.db).',
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Escribir en PostgreSQL (sin esto solo reporta).',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Vaciar tablas destino con datos antes de copiar (peligroso).',
    )
    args = parser.parse_args(argv)

    if not args.sqlite.startswith('sqlite'):
        parser.error('--sqlite debe ser una URL SQLite')

    src_engine = build_engine(args.sqlite)
    dst_engine = build_engine()

    tables = list(SQLModel.metadata.sorted_tables)  # topological (FK) order
    table_names = [t.name for t in tables]
    with src_engine.connect() as conn:
        src_tables = set(inspect(conn).get_table_names())

    with Session(src_engine) as src:
        if not args.apply:
            # Dry run: re-read counts without writing anything to PostgreSQL.
            totals: dict[str, int] = {}
            for t in tables:
                if t.name in src_tables:
                    totals[t.name] = src.execute(
                        text(f'SELECT COUNT(*) FROM {t.name}')
                    ).scalar_one()
                else:
                    totals[t.name] = 0
            if 'import_ledger' in src_tables:
                totals['import_ledger'] = src.execute(
                    text('SELECT COUNT(*) FROM import_ledger')
                ).scalar_one()
            else:
                totals['import_ledger'] = 0
            _print_report(totals, wrote=False)
            print('DRY RUN — sin cambios; usá --apply para escribir.')
            return 0

        with Session(dst_engine) as dst:
            create_schema(dst_engine)
            dst.execute(text(IMPORT_LEDGER_CREATE_SQL))

            copied: dict[str, int] = {}
            skipped: list[str] = []
            for t in tables:
                if t.name not in src_tables:
                    continue
                existing = dst.execute(
                    text(f'SELECT COUNT(*) FROM {t.name}')
                ).scalar_one()
                if existing:
                    if args.force:
                        dst.execute(text(f'DELETE FROM {t.name}'))
                        dst.commit()
                    else:
                        skipped.append(t.name)
                        continue
                copied[t.name] = _copy_table(src, dst, t)
                dst.commit()

            if 'import_ledger' in src_tables:
                existing_ledger = dst.execute(
                    text('SELECT COUNT(*) FROM import_ledger')
                ).scalar_one()
                if existing_ledger:
                    if args.force:
                        dst.execute(text('DELETE FROM import_ledger'))
                        dst.commit()
                    else:
                        skipped.append('import_ledger')
                if 'import_ledger' not in skipped:
                    copied['import_ledger'] = _copy_import_ledger(src, dst)
            dst.commit()

        _reset_sequences(dst_engine, table_names)

        report = {name: copied.get(name, 0) for name in list(copied) + skipped}
        _print_report(report, wrote=True)
        if skipped:
            print(
                'AVISO: tablas ya con datos u obsoletas (usá --force para vaciar): '
                + ', '.join(skipped)
            )
    return 0


def _print_report(report: dict[str, int], wrote: bool) -> None:
    modo = 'MIGRADO' if wrote else 'PENDIENTE'
    print(f'--- {modo} sqlite -> postgres')
    for name in sorted(report):
        print(f'{name}: {report[name]}')


if __name__ == '__main__':
    raise SystemExit(main())
