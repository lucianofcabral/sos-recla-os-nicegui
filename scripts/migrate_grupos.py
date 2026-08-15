"""Migrate the denormalized ``tres_arr.grupo`` strings into the ``grupos`` table.

For every distinct non-null ``tres_arr.grupo`` in the target database it
creates a ``grupos`` row (get-or-create, idempotent) and backfills the new
``tres_arr.grupo_id`` foreign key. With ``--apply`` it also creates the
``grupos`` table and the ``tres_arr.grupo_id`` column on demand, so it works
against databases created before this change.

Usage:
    uv run python scripts/migrate_grupos.py [--apply]

Target database comes from ``DATABASE_URL`` (Postgres) or the SQLite dev
``sqlite:///sos.db``.

Safeguards:
- Dry-run by default: read-only, only reports counts; ``--apply`` writes.
- Idempotent: existing ``grupos`` rows are reused and ``tres_arr`` rows already
  pointing at the right group are not re-linked.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text
from sqlmodel import Session, select

from src.adapters.sqlmodel import models  # noqa: F401  (registers tables)
from src.adapters.sqlmodel.models import TresArrRow
from src.application.import_gestiones import parse_fecha, resolver_grupo
from src.infrastructure.database import build_engine, create_schema
from src.infrastructure.unit_of_work import SqlModelUnitOfWork


def _table_exists(engine, table: str) -> bool:
    with engine.connect() as conn:
        return table in set(inspect(conn).get_table_names())


def _column_exists(engine, table: str, column: str) -> bool:
    with engine.connect() as conn:
        return column in {col['name'] for col in inspect(conn).get_columns(table)}


def _add_grupo_id_column(engine) -> bool:
    """Add ``tres_arr.grupo_id`` when missing; returns True when altered."""
    if _column_exists(engine, 'tres_arr', 'grupo_id'):
        return False
    with engine.begin() as conn:
        conn.execute(
            text(
                'ALTER TABLE tres_arr ADD COLUMN grupo_id INTEGER '
                'REFERENCES grupos (id)'
            )
        )
    return True


def _fecha_del_grupo(nombre: str) -> date | None:
    """Parse the ISO date embedded in a legacy group name when present."""
    return parse_fecha(nombre)


def _reportar_dry_run(engine) -> tuple[dict[str, int], bool]:
    """Count what a real run would do, without writing anything."""
    hay_columna = _column_exists(engine, 'tres_arr', 'grupo_id')
    columnas = 'id, grupo' + (', grupo_id' if hay_columna else '')
    with engine.connect() as conn:
        filas = (
            conn.execute(
                text(f'SELECT {columnas} FROM tres_arr WHERE grupo IS NOT NULL')
            )
            .mappings()
            .all()
        )
        if _table_exists(engine, 'grupos'):
            existentes = set(
                conn.execute(text('SELECT grupo FROM grupos')).scalars().all()
            )
            id_por_nombre = dict(
                conn.execute(text('SELECT grupo, id FROM grupos')).all()
            )
        else:
            existentes = set()
            id_por_nombre = {}

    creados = sorted({row['grupo'] for row in filas} - existentes)
    filas_actualizadas = 0
    filas_ya_ok = 0
    for row in filas:
        grupo = row['grupo']
        assert grupo is not None
        grupo_id = id_por_nombre.get(grupo)
        if grupo_id is None:
            filas_actualizadas += 1
        elif hay_columna and row.get('grupo_id') == grupo_id:
            filas_ya_ok += 1
        else:
            filas_actualizadas += 1
    report = {
        'grupos_existentes': len(existentes),
        'grupos_a_crear': len(creados),
        'filas_tres_arr': len(filas),
        'filas_a_actualizar': filas_actualizadas,
        'filas_ya_ok': filas_ya_ok,
    }
    return report, False


def _migrar(engine) -> tuple[dict[str, int], bool]:
    """Create missing groups and backfill ``tres_arr.grupo_id`` (idempotent)."""
    added_column = _add_grupo_id_column(engine)
    with Session(engine) as session, SqlModelUnitOfWork(session) as uow:
        rows = session.exec(
            select(TresArrRow).where(TresArrRow.grupo.is_not(None))
        ).all()
        por_nombre_id = {
            grupo.grupo: grupo.id for grupo in uow.grupos.list() if grupo.id is not None
        }
        creados = sorted(
            {row.grupo for row in rows if row.grupo is not None} - set(por_nombre_id)
        )
        for nombre in creados:
            grupo_id = resolver_grupo(uow, nombre, _fecha_del_grupo(nombre))
            assert grupo_id is not None
            por_nombre_id[nombre] = grupo_id
        filas_actualizadas = 0
        filas_ya_ok = 0
        for row in rows:
            assert row.grupo is not None
            grupo_id = por_nombre_id[row.grupo]
            if row.grupo_id == grupo_id:
                filas_ya_ok += 1
            else:
                row.grupo_id = grupo_id
                filas_actualizadas += 1
        uow.commit()
    report = {
        'grupos_existentes': len(por_nombre_id) - len(creados),
        'grupos_a_crear': len(creados),
        'filas_tres_arr': len(rows),
        'filas_a_actualizar': filas_actualizadas,
        'filas_ya_ok': filas_ya_ok,
    }
    return report, added_column


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Migrar tres_arr.grupo (string) a la tabla grupos + FK grupo_id.'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Escribir en la base de destino (sin esto solo reporta).',
    )
    args = parser.parse_args(argv)

    engine = build_engine()
    if args.apply:
        create_schema(engine)
        report, added_column = _migrar(engine)
    else:
        report, added_column = _reportar_dry_run(engine)

    modo = 'MIGRADO' if args.apply else 'PENDIENTE'
    print(f'--- {modo} grupos')
    for clave in ('grupos_existentes', 'grupos_a_crear', 'filas_tres_arr'):
        print(f'{clave}: {report[clave]}')
    print(f'filas_a_actualizar: {report["filas_a_actualizar"]}')
    print(f'filas_ya_ok: {report["filas_ya_ok"]}')
    if added_column:
        print('AVISO: se agregó la columna tres_arr.grupo_id (ALTER TABLE).')
    if not args.apply:
        print('DRY RUN — sin cambios; usá --apply para escribir.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
