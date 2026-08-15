"""CLI to import the legacy database into the system.

Reads the legacy SQLite database (gestiones/pagos/notas/facturas/diccionarios)
selected with ``OLD_DB_PATH``, maps it into the destination domain entities and
writes them through ``SqlModelUnitOfWork``. Migration bookkeeping lives in the
``import_ledger`` table of the destination database (created on every run);
re-running the import is a no-op for already-migrated rows. The legacy
``aux_*`` tables are garbage from an older migration and are ignored.

By default the run is a dry run; set ``IMPORT_APPLY=1`` (or pass ``--apply``)
to actually write.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from src.application.import_gestiones import import_gestiones
from src.infrastructure.database import build_engine, create_schema, load_env
from src.infrastructure.import_ledger import (
    SqlModelImportLedger,
    create_import_ledger,
)
from src.infrastructure.unit_of_work import SqlModelUnitOfWork

DEFAULT_OLD_DB = '/home/fexa/sos-viejo/reclamos/gestiones.db'


def main(argv: Sequence[str] | None = None) -> int:
    load_env()  # import reads OLD_DB_PATH / IMPORT_APPLY from the project .env
    old_db = os.getenv('OLD_DB_PATH', DEFAULT_OLD_DB)
    apply_default = os.getenv('IMPORT_APPLY', '').strip().lower() in {
        '1',
        'true',
        'yes',
    }

    parser = argparse.ArgumentParser(
        description='Importar la base legada (Excel/MySQL antigua) al sistema.'
    )
    parser.add_argument(
        '--old-db',
        default=old_db,
        help=f'Ruta a la base SQLite legada (o variable OLD_DB_PATH, por defecto '
        f'{DEFAULT_OLD_DB}).',
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        default=apply_default,
        help='Escribir en la base de destino (o aplicar con IMPORT_APPLY=1). '
        'Sin esto es solo un dry run.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=os.getenv('IMPORT_LIMIT', None),
        help='Limitar la cantidad de gestiones a importar (útil para pruebas).',
    )
    args = parser.parse_args(argv)

    engine = build_engine()
    create_schema(engine)
    with Session(engine) as session:
        create_import_ledger(session)
        report = import_gestiones(
            old_path=args.old_db,
            uow=SqlModelUnitOfWork(session),
            ledger=SqlModelImportLedger(session),
            dry_run=not args.apply,
            limit=args.limit,
        )

    modo = 'ESCRITURA' if args.apply else 'DRY RUN'
    print(f'--- {modo} (old-db: {args.old_db!r})')
    for clave in (
        'sos',
        'tres_arr',
        'otros',
        'pagos',
        'notas_credito',
        'facturas',
        'periodos',
        'documentos',
        'entidad_documentos',
    ):
        print(f'{clave}: {report[clave]}')
    errores = report['errores']
    assert isinstance(errores, list)
    if errores:
        print(f'errores: {len(errores)}')
        for error in errores[:10]:
            print(f'  - {error}')
    if not args.apply:
        print('DRY RUN — sin cambios; usá --apply para escribir.')
    else:
        print('Importación finalizada.')

    if errores:
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
