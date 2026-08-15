"""Tests for the historical import from the legacy SQLite database."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from src.application.import_gestiones import (
    GestionVieja,
    PagoVieja,
    agente_por_nombre,
    build_documento,
    build_factura,
    build_pago,
    build_periodo,
    build_reclamo,
    build_sos,
    build_tres_arr,
    clasificar_gestion,
    forma_pago_por_nombre,
    import_gestiones,
    parse_fecha,
    ruta_documento,
)
from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)
from src.domain.models.entities import ReclamoSos
from src.infrastructure.database import create_schema
from src.infrastructure.import_ledger import (
    SqlModelImportLedger,
    create_import_ledger,
)
from src.infrastructure.unit_of_work import SqlModelUnitOfWork
from tests.fakes.unit_of_work import FakeUnitOfWork

SCHEMAS: dict[str, str] = {
    'agentes': (
        'CREATE TABLE agentes ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'agente TEXT NOT NULL, UNIQUE (agente))'
    ),
    'formaspago': (
        'CREATE TABLE formaspago ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'formapago TEXT NOT NULL, UNIQUE (formapago))'
    ),
    'gestiones': (
        'CREATE TABLE gestiones ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'ngestion INTEGER DEFAULT(0) NOT NULL, '
        'fecha DATE, cliente TEXT, dominio TEXT, poliza TEXT NOT NULL, '
        'tipo TEXT NOT NULL, motivo TEXT, ncaso INTEGER DEFAULT(0) NOT NULL, '
        'usuariocarga TEXT, usuariorespuesta TEXT, estado TEXT, '
        'itr INTEGER DEFAULT(0) NOT NULL, '
        'totalfactura REAL DEFAULT(0.0) NOT NULL, '
        'terminado INTEGER DEFAULT(0) NOT NULL, obs TEXT, '
        'cod_productor INT NULL, nom_productor TEXT NULL, '
        'cod_organizador INT NULL, nom_organizador TEXT NULL, '
        'activa INTEGER DEFAULT(0) NOT NULL)'
    ),
    'pagos': (
        'CREATE TABLE pagos ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'gestion_id INTEGER NOT NULL, '
        'fecha DATE NOT NULL, '
        'pagador_id INTEGER NOT NULL, '
        'destinatario_id INTEGER NOT NULL, '
        'formapago_id INTEGER NOT NULL, '
        'importe REAL NOT NULL CHECK (importe > 0), '
        'FOREIGN KEY (gestion_id) REFERENCES gestiones (id), '
        'FOREIGN KEY (pagador_id) REFERENCES agentes (id), '
        'FOREIGN KEY (destinatario_id) REFERENCES agentes (id), '
        'FOREIGN KEY (formapago_id) REFERENCES formaspago (id))'
    ),
    'notas': (
        'CREATE TABLE notas ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'pago_id INTEGER NOT NULL, factura_id INTEGER NULL, '
        'UNIQUE (pago_id), '
        'FOREIGN KEY (pago_id) REFERENCES pagos (id), '
        'FOREIGN KEY (factura_id) REFERENCES facturas (id))'
    ),
    'facturas': (
        'CREATE TABLE facturas ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'fechaemitida DATE, periodo INTEGER NOT NULL, '
        'importe REAL DEFAULT(0.0), UNIQUE (periodo))'
    ),
    'aux_gestiones': (
        'CREATE TABLE aux_gestiones ('
        'ngestion integer, id_viejo integer, id_nuevo integer)'
    ),
    'aux_pagos': 'CREATE TABLE aux_pagos (id_viejo integer, id_nuevo integer)',
    'aux_facturas': 'CREATE TABLE aux_facturas (id_viejo integer, id_nuevo integer)',
    'documentos': (
        'CREATE TABLE documentos ('
        'id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
        'titulo TEXT NOT NULL, descripcion TEXT, nombre_archivo TEXT NOT NULL, '
        'mime_type TEXT, tamano INTEGER NOT NULL, hash TEXT NOT NULL, '
        'ruta TEXT NOT NULL, creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '
        'creado_por TEXT, UNIQUE (hash))'
    ),
    'gestion_documento': (
        'CREATE TABLE gestion_documento ('
        'gestion_id INTEGER NOT NULL, documento_id INTEGER NOT NULL, '
        'PRIMARY KEY (gestion_id, documento_id), '
        'FOREIGN KEY (gestion_id) REFERENCES gestiones (id) ON DELETE CASCADE, '
        'FOREIGN KEY (documento_id) REFERENCES documentos (id) ON DELETE CASCADE)'
    ),
}


def _crear_db_vieja(path: Path) -> None:
    """Build a small legacy DB mirroring the sos-viejo schema."""
    conn = sqlite3.connect(path)
    for tabla in SCHEMAS.values():
        conn.execute(tabla)
    conn.executemany(
        'INSERT INTO agentes (id, agente) VALUES (?, ?)',
        [
            (1, 'Asegurado'),
            (2, 'Prestador'),
            (3, 'SM'),
            (4, 'SOS'),
            (5, 'Productor'),
        ],
    )
    conn.executemany(
        'INSERT INTO formaspago (id, formapago) VALUES (?, ?)',
        [
            (1, 'Transferencia'),
            (2, 'Efectivo'),
            (3, 'Cheque'),
            (4, 'Nota De Credito'),
            (5, 'Nc Polizas'),
            (6, 'Cuenta Corriente'),
        ],
    )
    conn.executemany(
        'INSERT INTO gestiones '
        '(id, ngestion, fecha, cliente, dominio, poliza, tipo, motivo, '
        'usuariocarga, usuariorespuesta, estado, itr, totalfactura, obs, '
        'activa) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            (
                1,
                39982,
                '2023-01-24',
                'Cliente Uno',
                'AB123CD',
                'P-1',
                'VEHICULAR',
                'Motivo SOS',
                'juan',
                'maria',
                'en curso',
                0,
                150.5,
                None,
                1,
            ),
            (
                2,
                0,
                '2023-03-15',
                'Cliente Dos',
                'CD456EF',
                'P-2',
                'TREM',
                None,
                'pedro',
                None,
                None,
                0,
                0.0,
                'obs otras',
                1,
            ),
            (
                3,
                0,
                '2023-03-15',
                'Cliente Tres',
                'EF789GH',
                'P-3',
                'GEST',
                None,
                None,
                None,
                None,
                0,
                0.0,
                None,
                1,
            ),
            (
                4,
                0,
                '2023-04-02',
                'Cliente Cuatro',
                None,
                'P-4',
                'GEST',
                None,
                None,
                None,
                None,
                0,
                0.0,
                None,
                1,
            ),
        ],
    )
    conn.executemany(
        'INSERT INTO pagos '
        '(id, gestion_id, fecha, pagador_id, destinatario_id, formapago_id, '
        'importe) VALUES (?, ?, ?, ?, ?, ?, ?)',
        [
            (1, 1, '2023-01-25', 4, 3, 1, 1000.0),
            (2, 4, '2023-04-05', 3, 2, 2, 500.0),
            (3, 4, '2023-04-06', 4, 3, 6, 250.0),
        ],
    )
    conn.executemany(
        'INSERT INTO facturas (id, fechaemitida, periodo, importe) VALUES (?, ?, ?, ?)',
        [(1, '2023-04-30', 202304, 1234.0), (2, '2023-05-31', 202305, 0.0)],
    )
    conn.executemany(
        'INSERT INTO notas (id, pago_id, factura_id) VALUES (?, ?, ?)',
        [(1, 1, 1), (2, 2, None)],
    )
    hash_pdf = 'a' * 64
    hash_jpeg = 'b' * 64
    hash_faltante = 'c' * 64
    conn.executemany(
        'INSERT INTO documentos (id, titulo, descripcion, nombre_archivo, '
        'mime_type, tamano, hash, ruta, creado_en) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            (
                1,
                'Factura pdf',
                'Factura',
                'factura.pdf',
                'application/pdf',
                1024,
                hash_pdf,
                f'files\\docs\\{hash_pdf}.pdf',
                '2023-01-25 10:00:00',
            ),
            (
                2,
                'Captura llamadas',
                '',
                'captura.jpeg',
                'image/jpeg',
                512,
                hash_jpeg,
                f'files\\docs\\{hash_jpeg}.jpeg',
                '2023-04-06 11:00:00',
            ),
            (
                3,
                'Documento sin archivo',
                'Otro',
                'faltante.pdf',
                'application/pdf',
                0,
                hash_faltante,
                f'files\\docs\\{hash_faltante}.pdf',
                '2023-04-07 12:00:00',
            ),
        ],
    )
    conn.executemany(
        'INSERT INTO gestion_documento (gestion_id, documento_id) VALUES (?, ?)',
        [
            (1, 1),
            (1, 2),
            (4, 2),
        ],
    )
    files_dir = path.parent / 'files' / 'docs'
    files_dir.mkdir(parents=True, exist_ok=True)
    (files_dir / f'{hash_pdf}.pdf').write_bytes(b'%PDF-1.4\nfake pdf content')
    (files_dir / f'{hash_jpeg}.jpeg').write_bytes(b'\xff\xd8\xff\xe0 fake jpeg')
    # Garbage legacy aux_* bookkeeping: claims every row is already migrated.
    # The import must IGNORE these tables and still bring all rows.
    conn.executemany(
        'INSERT INTO aux_gestiones (ngestion, id_viejo, id_nuevo) VALUES (?, ?, ?)',
        [(0, 1, 900), (0, 2, 901), (0, 3, 902), (0, 4, 903)],
    )
    conn.executemany(
        'INSERT INTO aux_pagos (id_viejo, id_nuevo) VALUES (?, ?)',
        [(1, 910), (2, 911), (3, 912)],
    )
    conn.executemany(
        'INSERT INTO aux_facturas (id_viejo, id_nuevo) VALUES (?, ?)',
        [(1, 920), (2, 921)],
    )
    conn.commit()
    conn.close()


def _contar(path: Path, tabla: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]
    finally:
        conn.close()


def _destino() -> tuple[object, Session]:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    create_schema(engine)
    session = Session(engine)
    create_import_ledger(session)
    return engine, session


# --- unit: mapping helpers ---------------------------------------------------


def test_agente_por_nombre_ignora_mayusculas_y_espacios() -> None:
    assert agente_por_nombre('  SOS ') is AgenteEnum.SOS
    assert agente_por_nombre('sm') is AgenteEnum.SM
    assert agente_por_nombre('Productor') is AgenteEnum.PRODUCTOR
    assert agente_por_nombre('Desconocido') is None


def test_forma_pago_por_nombre_con_acentos_y_cuenta_corriente() -> None:
    assert forma_pago_por_nombre('Nota De Credito') is FormaPagoEnum.NOTA_DE_CREDITO
    assert forma_pago_por_nombre('Nc Polizas') is FormaPagoEnum.NC_POLIZA
    assert forma_pago_por_nombre('Cuenta Corriente') is FormaPagoEnum.CUENTA_CORRIENTE
    assert forma_pago_por_nombre('Transferencia') is FormaPagoEnum.TRANSFERENCIA
    assert forma_pago_por_nombre('Rara') is None


def test_parse_fecha_varios_formatos() -> None:
    assert parse_fecha('2023-01-24') == date(2023, 1, 24)
    assert parse_fecha('24/01/2023') == date(2023, 1, 24)
    assert parse_fecha('2023/01/24') == date(2023, 1, 24)
    assert parse_fecha('24-01-2023') == date(2023, 1, 24)
    assert parse_fecha(None) is None
    assert parse_fecha('') is None
    assert parse_fecha('garbage') is None


def test_clasificar_gestion_tres_casos() -> None:
    assert clasificar_gestion(39982, True) is TipoReclamoEnum.SOS
    assert clasificar_gestion(0, True) is TipoReclamoEnum.TRESA
    assert clasificar_gestion(0, False) is TipoReclamoEnum.OTROS


def test_build_reclamo_y_build_sos() -> None:
    gestion = GestionVieja(
        id=1,
        ngestion=39982,
        fecha=date(2023, 1, 24),
        cliente='Cliente',
        dominio='AB123CD',
        poliza='P-1',
        motivo='Motivo',
        usuariocarga='juan',
        usuariorespuesta='maria',
        estado='en curso',
        itr=7,
        totalfactura=150.5,
        obs='mitad doble',
        activa=1,
    )
    reclamo = build_reclamo(gestion, TipoReclamoEnum.SOS)
    assert reclamo.tipo_reclamo is TipoReclamoEnum.SOS
    assert reclamo.cliente == 'CLIENTE'
    assert reclamo.dominio == 'AB123CD'
    assert reclamo.poliza == 'P-1'
    assert reclamo.importe_reclamado == 150.5
    assert reclamo.comentario == 'MITAD DOBLE'
    assert reclamo.active is True
    assert reclamo.created_at is not None

    sos: ReclamoSos = build_sos(gestion)
    assert sos.nro_gestion == 39982
    assert sos.motivo == 'MOTIVO'
    assert sos.usuario_carga == 'JUAN'
    assert sos.status == 'EN CURSO'
    assert sos.itr == 7


def test_build_reclamo_obs_vacia_se_descarta() -> None:
    gestion = GestionVieja(
        id=2,
        ngestion=0,
        fecha=date(2023, 3, 15),
        cliente=None,
        dominio=None,
        poliza='P-2',
        motivo=None,
        usuariocarga=None,
        usuariorespuesta=None,
        estado=None,
        itr=0,
        totalfactura=0.0,
        obs=None,
        activa=1,
    )
    assert build_reclamo(gestion, TipoReclamoEnum.TRESA).comentario is None


def test_build_tres_arr_grupo_con_fecha() -> None:
    tres = build_tres_arr(date(2023, 3, 15))
    assert tres.grupo == '2023-03-15'
    assert build_tres_arr(None).grupo is None


def test_build_reclamo_otros_es_reclamo_base() -> None:
    gestion = GestionVieja(
        id=4,
        ngestion=0,
        fecha=date(2023, 4, 2),
        cliente='Cliente Cuatro',
        dominio=None,
        poliza='P-4',
        motivo=None,
        usuariocarga=None,
        usuariorespuesta=None,
        estado=None,
        itr=0,
        totalfactura=0.0,
        obs=None,
        activa=1,
    )
    reclamo = build_reclamo(gestion, TipoReclamoEnum.OTROS)
    assert reclamo.tipo_reclamo is TipoReclamoEnum.OTROS
    assert reclamo.cliente == 'CLIENTE CUATRO'
    assert reclamo.id is None


def test_build_pago_y_build_periodo() -> None:
    pago = build_pago(
        PagoVieja(
            id=1,
            gestion_id=1,
            fecha_pago=date(2023, 1, 25),
            pagador='SOS',
            destinatario='SM',
            formapago='Transferencia',
            importe=1000.0,
        ),
        AgenteEnum.SOS,
        AgenteEnum.SM,
        FormaPagoEnum.TRANSFERENCIA,
    )
    assert pago.pagador is AgenteEnum.SOS
    assert pago.destinatario is AgenteEnum.SM
    assert pago.monto == 1000.0
    assert pago.fecha_pago == date(2023, 1, 25)

    periodo = build_periodo(202304)
    assert periodo.anio == 2023
    assert periodo.mes == 4
    assert periodo.anio_mes == 202304
    assert periodo.nombre_corto == '04/2023'
    assert periodo.nombre_largo is None


def test_build_factura_nro_fabricado() -> None:
    factura = build_factura(
        periodo_id=1, fechaemitida='2023-04-30', importe=1234.0, anio_mes=202304
    )
    assert factura.nro_factura == 'FIC-202304'
    assert factura.periodo_id == 1
    assert factura.importe == 1234.0
    assert factura.fecha_emision == date(2023, 4, 30)


def test_build_documento_mapea_campos() -> None:
    doc = build_documento(
        {
            'hash': 'a' * 64,
            'descripcion': 'Factura',
            'nombre_archivo': 'factura.pdf',
            'titulo': 'ignorado',
            'tamano': 1024,
            'mime_type': 'application/pdf',
            'creado_en': '2023-01-25 10:00:00',
        },
        b'pdf-bytes',
    )
    assert doc.document_hash == 'a' * 64
    assert doc.tipo == 'Factura'
    assert doc.nombre == 'factura.pdf'
    assert doc.contenido == b'pdf-bytes'
    assert doc.tamanio == 1024
    assert doc.mime == 'application/pdf'
    assert doc.descripcion == ''
    assert doc.creado == datetime(2023, 1, 25, 10, 0, 0)


def test_build_documento_tipo_fallback_y_nombre_titulo() -> None:
    doc = build_documento(
        {
            'hash': 'b' * 64,
            'descripcion': '   ',
            'nombre_archivo': '',
            'titulo': 'Titulo X',
            'tamano': 0,
            'mime_type': None,
            'creado_en': None,
        },
        b'',
    )
    assert doc.document_hash == 'b' * 64
    assert doc.tipo == 'Documento'
    assert doc.nombre == 'Titulo X'
    assert doc.tamanio == 0
    assert doc.mime == ''
    assert doc.creado is not None


def test_ruta_documento_convierte_backslashes(tmp_path: Path) -> None:
    old_path = tmp_path / 'gestiones.db'
    ruta = ruta_documento('files\\docs\\abcd.pdf', old_path)
    assert ruta == (tmp_path / 'files/docs/abcd.pdf').resolve()


# --- pipeline: E2E against a tmp legacy DB + fakes ---------------------------


def test_import_dry_run_no_escribe_nada(tmp_path: Path) -> None:
    db = tmp_path / 'gestiones.db'
    _crear_db_vieja(db)
    uow = FakeUnitOfWork()
    report = import_gestiones(old_path=str(db), uow=uow)
    assert report['sos'] == 1
    assert report['tres_arr'] == 2
    assert report['otros'] == 1
    assert report['pagos'] == 3
    assert report['notas_credito'] == 2
    assert report['facturas'] == 2
    assert report['periodos'] == 2
    assert report['documentos'] == 2
    assert report['entidad_documentos'] == 3
    assert report['errores'] == ['documento 3: archivo no encontrado']
    assert len(uow.reclamos.list(active_only=False)) == 0
    assert uow.documentos.list() == []
    assert uow.entidad_documentos.list() == []
    assert uow.committed is False
    # Legacy aux_* garbage is ignored and never touched by the import.
    assert _contar(db, 'aux_gestiones') == 4
    assert _contar(db, 'aux_pagos') == 3
    assert _contar(db, 'aux_facturas') == 2


def test_import_real_via_ledger_escribe_y_es_idempotente(tmp_path: Path) -> None:
    db = tmp_path / 'gestiones.db'
    _crear_db_vieja(db)
    engine, session = _destino()
    uow = SqlModelUnitOfWork(session)
    ledger = SqlModelImportLedger(session)
    report = import_gestiones(
        old_path=str(db),
        uow=uow,
        ledger=ledger,
        dry_run=False,
    )
    assert report['sos'] == 1
    assert report['tres_arr'] == 2
    assert report['otros'] == 1
    assert report['pagos'] == 3
    assert report['notas_credito'] == 2
    assert report['facturas'] == 2
    assert report['periodos'] == 2
    assert report['documentos'] == 2
    assert report['entidad_documentos'] == 3
    assert report['errores'] == ['documento 3: archivo no encontrado']

    reclamos = uow.reclamos.list(active_only=False)
    assert len(reclamos) == 4
    assert {r.tipo_reclamo for r in reclamos} == {
        TipoReclamoEnum.OTROS,
        TipoReclamoEnum.SOS,
        TipoReclamoEnum.TRESA,
    }
    assert len(uow.pagos.list()) == 3
    # nota 1 apunta a factura 1 (periodo 202304 -> id 1); nota 2 sin factura.
    assert len(uow.credit_notes.list_by_periodo(1)) == 1
    assert len(uow.periodos.list()) == 2
    assert len(uow.facturas.list_by_periodo(1)) == 1

    sos = uow.reclamos_sos.get_by_reclamo_id(1)
    assert sos is not None
    assert sos.nro_gestion == 39982
    tres = uow.tres_arr.get_by_reclamo_id(3)
    assert tres is not None
    assert tres.grupo == '2023-03-15'
    # Both TRESA gestiones share the same date -> one grupo row, linked by FK.
    assert [g.grupo for g in uow.grupos.list()] == ['2023-03-15']
    grupo = uow.grupos.get_by_nombre('2023-03-15')
    assert grupo is not None
    assert grupo.id is not None
    assert tres.grupo_id == grupo.id
    tres_hermano = uow.tres_arr.get_by_reclamo_id(2)
    assert tres_hermano is not None
    assert tres_hermano.grupo_id == grupo.id
    otros = uow.reclamos.get(4)
    assert otros.tipo_reclamo == TipoReclamoEnum.OTROS

    hash_pdf = 'a' * 64
    hash_jpeg = 'b' * 64
    doc_pdf = uow.documentos.get_by_hash(hash_pdf)
    assert doc_pdf is not None
    assert doc_pdf.tipo == 'Factura'
    assert doc_pdf.nombre == 'factura.pdf'
    assert doc_pdf.tamanio == 1024
    assert doc_pdf.mime == 'application/pdf'
    assert doc_pdf.contenido == b'%PDF-1.4\nfake pdf content'
    doc_jpeg = uow.documentos.get_by_hash(hash_jpeg)
    assert doc_jpeg is not None
    assert doc_jpeg.tipo == 'Documento'
    assert doc_jpeg.mime == 'image/jpeg'
    assert uow.documentos.get_by_hash('c' * 64) is None

    vinculos = uow.entidad_documentos.list()
    assert len(vinculos) == 3
    por_documento: dict[str, list[int]] = {}
    for vinculo in vinculos:
        assert vinculo.tipo_entidad is TipoEntidadEnum.RECLAMO
        assert vinculo.entidad_id is not None
        por_documento.setdefault(vinculo.document_hash, []).append(vinculo.entidad_id)
    assert sorted(por_documento[hash_pdf]) == [1]
    assert sorted(por_documento[hash_jpeg]) == [1, 4]

    # Idempotency bookkeeping lives in the destination DB ledger: 4 gestiones,
    # 3 pagos, 2 facturas and 2 documentos as (old_table, old_id) -> new_id.
    movidos = ledger.read()
    assert len(movidos) == 11
    assert movidos[('gestiones', 1)] == 1
    assert ('pagos', 1) in movidos
    assert ('facturas', 1) in movidos
    assert ('documentos', 1) in movidos
    assert ('documentos', 2) in movidos

    # Second run against the same destination: everything already in the ledger.
    session2 = Session(engine)
    uow2 = SqlModelUnitOfWork(session2)
    ledger2 = SqlModelImportLedger(session2)
    report2 = import_gestiones(
        old_path=str(db),
        uow=uow2,
        ledger=ledger2,
        dry_run=False,
    )
    assert report2['sos'] == 0
    assert report2['tres_arr'] == 0
    assert report2['otros'] == 0
    assert report2['pagos'] == 0
    assert report2['notas_credito'] == 0
    assert report2['facturas'] == 0
    assert report2['periodos'] == 0
    assert report2['documentos'] == 0
    assert report2['entidad_documentos'] == 0
    assert report2['errores'] == ['documento 3: archivo no encontrado']
    assert len(uow2.reclamos.list(active_only=False)) == 4
    assert len(uow2.documentos.list()) == 2
    assert len(uow2.entidad_documentos.list()) == 3
    session.close()
    session2.close()


def test_import_limit_trunca_gestiones(tmp_path: Path) -> None:
    db = tmp_path / 'gestiones.db'
    _crear_db_vieja(db)
    uow = FakeUnitOfWork()
    report = import_gestiones(old_path=str(db), uow=uow, limit=1)
    assert report['sos'] == 1
    assert report['tres_arr'] == 0
    assert report['otros'] == 0
    assert report['pagos'] == 1
    assert report['notas_credito'] == 1
    assert report['facturas'] == 2
    assert report['periodos'] == 2
    assert report['documentos'] == 2
    assert report['entidad_documentos'] == 2
    assert report['errores'] == [
        'pago 2: gestion 4 no migrada',
        'pago 3: gestion 4 no migrada',
        'nota de crédito: pago 2 no migrado',
        'documento 3: archivo no encontrado',
        'documento 2: gestion 4 no migrada',
    ]
