"""Historical import from the legacy SQLite database.

This module holds the pure mapping helpers and the idempotent ``import_gestiones``
pipeline used by ``scripts/import_old_db.py``. It reads the legacy database
(``gestiones/pagos/notas/facturas/agentes/formaspago``) and writes domain entities
through a ``UnitOfWorkPort``. Idempotency bookkeeping lives in an ``import_ledger``
table on the destination database (infra machinery, not the legacy ``aux_*``
tables, which belong to an older migration and are ignored).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Protocol

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)
from src.domain.models.entities import (
    CreditNote,
    Documento,
    EntidadDocumento,
    Factura,
    Grupo,
    Pago,
    Periodo,
    Reclamo,
    ReclamoSos,
    TresArrReclamo,
    normalizar_texto,
)
from src.domain.ports.unit_of_work import UnitOfWorkPort

AGENTE_POR_NOMBRE: dict[str, AgenteEnum] = {
    'asegurado': AgenteEnum.ASEGURADO,
    'prestador': AgenteEnum.PRESTADOR,
    'sm': AgenteEnum.SM,
    'sos': AgenteEnum.SOS,
    'productor': AgenteEnum.PRODUCTOR,
}

FORMA_PAGO_POR_NOMBRE_VIEJO: dict[str, FormaPagoEnum] = {
    'transferencia': FormaPagoEnum.TRANSFERENCIA,
    'nota de credito': FormaPagoEnum.NOTA_DE_CREDITO,
    'nc polizas': FormaPagoEnum.NC_POLIZA,
    'efectivo': FormaPagoEnum.EFECTIVO,
    'cheque': FormaPagoEnum.CHEQUE,
    'cuenta corriente': FormaPagoEnum.CUENTA_CORRIENTE,
}

FECHA_FORMATOS: tuple[str, ...] = ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y')

TIPO_REPORT_KEY: dict[TipoReclamoEnum, str] = {
    TipoReclamoEnum.SOS: 'sos',
    TipoReclamoEnum.TRESA: 'tres_arr',
    TipoReclamoEnum.OTROS: 'otros',
}

BATCH_SIZE = 100

LedgerRow = tuple[str, int, str, int]


class ImportLedgerPort(Protocol):
    """Old->new id bookkeeping stored on the destination DB.

    Each imported legacy row is recorded as ``(old_table, old_id) -> new_id``
    so re-runs skip already-migrated rows and resolve old->new links within
    the same run. Dry runs never call ``write``.
    """

    def read(self) -> dict[tuple[str, int], int]:
        """Return ``{(old_table, old_id): new_id}`` for every entry."""
        ...

    def write(self, rows: Sequence[LedgerRow]) -> None:
        """Record ``(old_table, old_id, new_table, new_id)`` rows."""
        ...


@dataclass(frozen=True)
class GestionVieja:
    """Normalized legacy ``gestiones`` row (old Spanish column names)."""

    id: int
    ngestion: int
    fecha: date | None
    cliente: str | None
    dominio: str | None
    poliza: str
    motivo: str | None
    usuariocarga: str | None
    usuariorespuesta: str | None
    estado: str | None
    itr: int
    totalfactura: float
    obs: str | None
    activa: int


@dataclass(frozen=True)
class PagoVieja:
    """Normalized legacy ``pagos`` row with resolved names (old columns)."""

    id: int
    gestion_id: int
    fecha_pago: date | None
    pagador: str | None
    destinatario: str | None
    formapago: str | None
    importe: float


def _normalizar(nombre: str | None) -> str:
    """Normalize a legacy name: lowercase, collapse and strip whitespace."""
    if not nombre:
        return ''
    return ' '.join(nombre.strip().lower().split())


def agente_por_nombre(nombre: str | None) -> AgenteEnum | None:
    """Map a legacy agent name ('Asegurado', 'SM', ...) to AgenteEnum."""
    return AGENTE_POR_NOMBRE.get(_normalizar(nombre))


def forma_pago_por_nombre(nombre: str | None) -> FormaPagoEnum | None:
    """Map a legacy payment form name to FormaPagoEnum."""
    return FORMA_PAGO_POR_NOMBRE_VIEJO.get(_normalizar(nombre))


def parse_fecha(value: object) -> date | None:
    """Parse a legacy date ('YYYY-MM-DD' and friends); None when blank/invalid."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {'none', 'null'}:
        return None
    for fmt in FECHA_FORMATOS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def clasificar_gestion(ngestion: int, misma_fecha_otras: bool) -> TipoReclamoEnum:
    """Classify a legacy gestion by nro de gestión and same-date group membership."""
    if ngestion and ngestion > 0:
        return TipoReclamoEnum.SOS
    if misma_fecha_otras:
        return TipoReclamoEnum.TRESA
    return TipoReclamoEnum.OTROS


def _comentario(obs: str | None) -> str | None:
    if not obs or obs.strip().lower() in {'', 'none'}:
        return None
    return obs


def _created_at(fecha: date | None) -> datetime:
    if fecha is not None:
        return datetime.combine(fecha, time.min)
    return datetime.now()


def build_reclamo(gestion: GestionVieja, tipo: TipoReclamoEnum) -> Reclamo:
    """Build the base Reclamo entity from a legacy gestion row."""
    created = _created_at(gestion.fecha)
    return Reclamo(
        tipo_reclamo=tipo,
        cliente=gestion.cliente,
        poliza=gestion.poliza,
        dominio=gestion.dominio,
        importe_reclamado=gestion.totalfactura,
        comentario=_comentario(gestion.obs),
        active=bool(gestion.activa),
        created_at=created,
        updated_at=created,
    )


def build_sos(gestion: GestionVieja) -> ReclamoSos:
    """Build a ReclamoSos from a legacy gestion row (nro_gestion = ngestion)."""
    return ReclamoSos(
        nro_gestion=gestion.ngestion,
        motivo=gestion.motivo,
        usuario_carga=gestion.usuariocarga,
        usuario_respuesta=gestion.usuariorespuesta,
        status=gestion.estado,
        itr=gestion.itr or None,
    )


def build_tres_arr(fecha: date | None) -> TresArrReclamo:
    """Build a TresArrReclamo with the legacy date as its group key."""
    return TresArrReclamo(grupo=fecha.isoformat() if fecha is not None else None)


def resolver_grupo(
    uow: UnitOfWorkPort, nombre: str | None, fecha: date | None = None
) -> int | None:
    """Resolve a group by name, creating it when missing; returns its id.

    ``fecha`` seeds ``fecha_creacion`` (e.g. the legacy group date) when the
    group has to be created.
    """
    if not nombre:
        return None
    nombre = normalizar_texto(nombre)
    assert nombre is not None
    grupo = uow.grupos.get_by_nombre(nombre)
    if grupo is None:
        grupo = uow.grupos.save(
            Grupo(
                grupo=nombre,
                fecha_creacion=(
                    datetime.combine(fecha, time.min) if fecha is not None else None
                ),
            )
        )
    assert grupo.id is not None
    return grupo.id


def build_pago(
    pago: PagoVieja,
    pagador: AgenteEnum | None,
    destinatario: AgenteEnum | None,
    forma: FormaPagoEnum | None,
) -> Pago:
    """Build a Pago from a legacy pago row with resolved enum actors/form."""
    return Pago(
        fecha_pago=pago.fecha_pago,
        forma_pago=forma,
        pagador=pagador,
        destinatario=destinatario,
        monto=pago.importe,
    )


def build_periodo(anio_mes: int) -> Periodo:
    """Build a Periodo from an ``anio_mes`` value like 202304."""
    anio, mes = divmod(anio_mes, 100)
    return Periodo(
        anio=anio,
        mes=mes,
        anio_mes=anio_mes,
        nombre_corto=f'{mes:02d}/{anio}',
    )


def build_factura(
    periodo_id: int,
    fechaemitida: object,
    importe: float,
    anio_mes: int,
) -> Factura:
    """Build a Factura from a legacy ``facturas`` row (fabricated nro)."""
    return Factura(
        periodo_id=periodo_id,
        nro_factura=f'FIC-{anio_mes}',
        importe=importe,
        fecha_emision=parse_fecha(fechaemitida),
    )


def build_documento(fila: Mapping[str, Any], contenido: bytes) -> Documento:
    """Build a Documento from a legacy ``documentos`` row and its file bytes.

    The legacy ``descripcion`` becomes the document ``tipo`` (fallback
    ``'Documento'``), ``nombre_archivo`` becomes ``nombre`` (fallback
    ``titulo``) and the legacy ``creado_en`` timestamp becomes ``creado``.
    """
    descripcion = str(fila['descripcion'] or '').strip()
    nombre = str(fila['nombre_archivo'] or '').strip()
    if not nombre:
        nombre = str(fila['titulo'] or '').strip()
    return Documento(
        document_hash=str(fila['hash']).strip().lower(),
        tipo=descripcion[:100] or 'Documento',
        nombre=nombre[:255],
        contenido=contenido,
        tamanio=int(fila['tamano'] or 0),
        mime=str(fila['mime_type'] or ''),
        descripcion='',
        creado=_creado_en(fila['creado_en']),
    )


def ruta_documento(ruta: str, old_path: str | Path) -> Path:
    """Resolve a legacy document ``ruta`` (Windows backslashes) to a Path.

    The legacy DB stores Windows-style paths like ``files\\docs\\<hash>.ext``
    relative to the folder that holds the legacy database file; the physical
    files live next to it, so they are resolved against ``old_path``'s folder.
    """
    base = Path(old_path)
    return (base.parent / ruta.replace('\\', '/')).resolve()


def _creado_en(value: object) -> datetime:
    """Parse a legacy ``creado_en`` timestamp; fall back to now when blank."""
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.now()


def _leer_archivo(path: Path) -> bytes | None:
    """Read the physical file for a legacy document; None when missing."""
    try:
        return path.read_bytes()
    except OSError:
        return None


def parse_gestion(row: Mapping[str, Any]) -> GestionVieja:
    """Convert a legacy gestiones row (sqlite Row or dict) to GestionVieja."""
    return GestionVieja(
        id=int(row['id']),
        ngestion=int(row['ngestion'] or 0),
        fecha=parse_fecha(row['fecha']),
        cliente=_optional_str(row['cliente']),
        dominio=_optional_str(row['dominio']),
        poliza=str(row['poliza'] or ''),
        motivo=_optional_str(row['motivo']),
        usuariocarga=_optional_str(row['usuariocarga']),
        usuariorespuesta=_optional_str(row['usuariorespuesta']),
        estado=_optional_str(row['estado']),
        itr=int(row['itr'] or 0),
        totalfactura=float(row['totalfactura'] or 0.0),
        obs=_optional_str(row['obs']),
        activa=int(row['activa'] or 0),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


Report = dict[str, Any]


def import_gestiones(
    *,
    old_path: str,
    uow: UnitOfWorkPort,
    ledger: ImportLedgerPort | None = None,
    dry_run: bool = True,
    limit: int | None = None,
) -> Report:
    """Import legacy gestiones/pagos/notas/facturas into the destination UoW.

    Returns a report dict with counts per type and a list of errors.
    ``dry_run=True`` only counts; nothing is written to the destination nor to
    the import ledger. When ``ledger`` is provided, already-migrated rows are
    skipped and newly imported rows are recorded on it.
    """
    report = {
        'sos': 0,
        'tres_arr': 0,
        'otros': 0,
        'pagos': 0,
        'notas_credito': 0,
        'facturas': 0,
        'periodos': 0,
        'documentos': 0,
        'entidad_documentos': 0,
        'errores': [],
    }
    conn = sqlite3.connect(old_path)
    conn.row_factory = sqlite3.Row
    try:
        _run_import(
            conn,
            uow,
            report,
            ledger=ledger,
            dry_run=dry_run,
            limit=limit,
            old_path=old_path,
        )
    finally:
        conn.close()
    return report


def _run_import(
    conn: sqlite3.Connection,
    uow: UnitOfWorkPort,
    report: Report,
    *,
    ledger: ImportLedgerPort | None,
    dry_run: bool,
    limit: int | None,
    old_path: str,
) -> None:
    movidos = ledger.read() if ledger is not None else {}

    def _por_tabla(tabla: str) -> dict[int, int]:
        return {
            old_id: new_id
            for (old_tabla, old_id), new_id in movidos.items()
            if old_tabla == tabla
        }

    moved_gestiones = _por_tabla('gestiones')
    moved_pagos = _por_tabla('pagos')
    moved_facturas = _por_tabla('facturas')
    moved_documentos = _por_tabla('documentos')

    fechas_grupo = _fechas_grupo(conn)
    pagos_con_nota = _pagos_con_nota(conn)

    filas = conn.execute('SELECT * FROM gestiones ORDER BY id').fetchall()
    pendientes = [row for row in filas if int(row['id']) not in moved_gestiones]
    if limit is not None:
        pendientes = pendientes[:limit]

    reclamo_por_gestion = dict(moved_gestiones)
    pago_por_antiguo = dict(moved_pagos)
    pagos_a_migrar: set[int] = set()
    pagos_migrados_hoy: set[int] = set()

    _import_gestiones(
        uow,
        report,
        pendientes,
        fechas_grupo,
        reclamo_por_gestion,
        ledger,
        dry_run,
    )
    _import_pagos(
        conn,
        uow,
        report,
        pagos_con_nota,
        reclamo_por_gestion,
        pago_por_antiguo,
        pagos_a_migrar,
        pagos_migrados_hoy,
        ledger,
        dry_run,
    )
    periodo_por_anio_mes = _import_facturas(
        conn, uow, report, moved_facturas, ledger, dry_run
    )
    _import_notas(
        conn,
        uow,
        report,
        pagos_a_migrar,
        pagos_migrados_hoy,
        pago_por_antiguo,
        periodo_por_anio_mes,
        dry_run,
    )
    _import_documentos(
        conn,
        uow,
        report,
        reclamo_por_gestion,
        moved_documentos,
        ledger,
        dry_run,
        old_path,
    )


def _fechas_grupo(conn: sqlite3.Connection) -> set[date]:
    """Dates grouping 2+ ngestion=0 gestiones (whole legacy universe)."""
    filas = conn.execute(
        'SELECT fecha, COUNT(*) as c FROM gestiones '
        'WHERE ngestion = 0 GROUP BY fecha HAVING c > 1'
    )
    return {fecha for row in filas if (fecha := parse_fecha(row['fecha']))}


def _pagos_con_nota(conn: sqlite3.Connection) -> set[int]:
    filas = conn.execute('SELECT pago_id FROM notas')
    return {int(row['pago_id']) for row in filas if row['pago_id'] is not None}


def _import_gestiones(
    uow: UnitOfWorkPort,
    report: Report,
    pendientes: list,
    fechas_grupo: set[date],
    reclamo_por_gestion: dict[int, int],
    ledger: ImportLedgerPort | None,
    dry_run: bool,
) -> None:
    errores = report['errores']
    assert isinstance(errores, list)
    ledger_rows: list[LedgerRow] = []
    for fila in pendientes:
        gestion = parse_gestion(fila)
        tipo = clasificar_gestion(gestion.ngestion, gestion.fecha in fechas_grupo)
        report[TIPO_REPORT_KEY[tipo]] = int(report[TIPO_REPORT_KEY[tipo]]) + 1
        if dry_run:
            reclamo_por_gestion[gestion.id] = gestion.id
            continue
        reclamo = uow.reclamos.save(build_reclamo(gestion, tipo))
        assert reclamo.id is not None
        _save_hijo(uow, tipo, gestion, reclamo.id)
        reclamo_por_gestion[gestion.id] = reclamo.id
        ledger_rows.append(('gestiones', gestion.id, 'reclamos', reclamo.id))
        if len(ledger_rows) >= BATCH_SIZE:
            _guardar_lote(uow, ledger, ledger_rows)
            ledger_rows = []
    if ledger_rows:
        _guardar_lote(uow, ledger, ledger_rows)


def _save_hijo(
    uow: UnitOfWorkPort,
    tipo: TipoReclamoEnum,
    gestion: GestionVieja,
    reclamo_id: int,
) -> None:
    if tipo == TipoReclamoEnum.SOS:
        uow.reclamos_sos.save(
            build_sos(gestion).model_copy(update={'reclamo_id': reclamo_id})
        )
    elif tipo == TipoReclamoEnum.TRESA:
        tres = build_tres_arr(gestion.fecha)
        uow.tres_arr.save(
            tres.model_copy(
                update={
                    'reclamo_id': reclamo_id,
                    'grupo_id': resolver_grupo(uow, tres.grupo, gestion.fecha),
                }
            )
        )


def _import_pagos(
    conn: sqlite3.Connection,
    uow: UnitOfWorkPort,
    report: Report,
    pagos_con_nota: set[int],
    reclamo_por_gestion: dict[int, int],
    pago_por_antiguo: dict[int, int],
    pagos_a_migrar: set[int],
    pagos_migrados_hoy: set[int],
    ledger: ImportLedgerPort | None,
    dry_run: bool,
) -> None:
    errores = report['errores']
    assert isinstance(errores, list)
    ledger_rows: list[LedgerRow] = []
    filas = conn.execute(
        'SELECT p.id, p.gestion_id, p.fecha, p.importe, '
        'pag.agente AS pagador, dest.agente AS destinatario, '
        'fp.formapago AS formapago '
        'FROM pagos p '
        'JOIN agentes pag ON pag.id = p.pagador_id '
        'JOIN agentes dest ON dest.id = p.destinatario_id '
        'JOIN formaspago fp ON fp.id = p.formapago_id '
        'ORDER BY p.id'
    ).fetchall()
    for fila in filas:
        pago_id = int(fila['id'])
        gestion_id = int(fila['gestion_id'])
        if pago_id in pago_por_antiguo:
            continue
        if gestion_id not in reclamo_por_gestion:
            errores.append(f'pago {pago_id}: gestion {gestion_id} no migrada')
            continue
        forma = forma_pago_por_nombre(fila['formapago'])
        if pago_id in pagos_con_nota:
            forma = FormaPagoEnum.NOTA_DE_CREDITO
        if forma is None:
            errores.append(f'pago {pago_id}: forma de pago desconocida')
            continue
        pagos_a_migrar.add(pago_id)
        report['pagos'] = int(report['pagos']) + 1
        if dry_run:
            continue
        pago_vieja = PagoVieja(
            id=pago_id,
            gestion_id=gestion_id,
            fecha_pago=parse_fecha(fila['fecha']),
            pagador=fila['pagador'],
            destinatario=fila['destinatario'],
            formapago=fila['formapago'],
            importe=float(fila['importe']),
        )
        pago = build_pago(
            pago_vieja,
            agente_por_nombre(fila['pagador']),
            agente_por_nombre(fila['destinatario']),
            forma,
        ).model_copy(update={'reclamo_id': reclamo_por_gestion[gestion_id]})
        guardado = uow.pagos.save(pago)
        assert guardado.id is not None
        pago_por_antiguo[pago_id] = guardado.id
        pagos_migrados_hoy.add(pago_id)
        ledger_rows.append(('pagos', pago_id, 'pagos', guardado.id))
        if len(ledger_rows) >= BATCH_SIZE:
            _guardar_lote(uow, ledger, ledger_rows)
            ledger_rows = []
    if ledger_rows:
        _guardar_lote(uow, ledger, ledger_rows)


def _import_facturas(
    conn: sqlite3.Connection,
    uow: UnitOfWorkPort,
    report: Report,
    moved_facturas: dict[int, int],
    ledger: ImportLedgerPort | None,
    dry_run: bool,
) -> dict[int, int]:
    periodo_por_anio_mes = {
        int(p.anio_mes): int(p.id)
        for p in uow.periodos.list()
        if p.anio_mes is not None and p.id is not None
    }
    ledger_rows: list[LedgerRow] = []
    contados: set[int] = set()
    filas = conn.execute('SELECT * FROM facturas ORDER BY id').fetchall()
    for fila in filas:
        factura_id = int(fila['id'])
        anio_mes = int(fila['periodo'])
        if factura_id in moved_facturas:
            continue
        report['facturas'] = int(report['facturas']) + 1
        if anio_mes not in periodo_por_anio_mes and anio_mes not in contados:
            contados.add(anio_mes)
            report['periodos'] = int(report['periodos']) + 1
        if dry_run:
            continue
        if anio_mes not in periodo_por_anio_mes:
            periodo = uow.periodos.save(build_periodo(anio_mes))
            assert periodo.id is not None
            periodo_por_anio_mes[anio_mes] = periodo.id
        factura = build_factura(
            periodo_por_anio_mes[anio_mes],
            fila['fechaemitida'],
            float(fila['importe'] or 0.0),
            anio_mes,
        )
        guardada = uow.facturas.save(factura)
        assert guardada.id is not None
        ledger_rows.append(('facturas', factura_id, 'facturas', guardada.id))
        if len(ledger_rows) >= BATCH_SIZE:
            _guardar_lote(uow, ledger, ledger_rows)
            ledger_rows = []
    if ledger_rows:
        _guardar_lote(uow, ledger, ledger_rows)
    return periodo_por_anio_mes


def _import_notas(
    conn: sqlite3.Connection,
    uow: UnitOfWorkPort,
    report: Report,
    pagos_a_migrar: set[int],
    pagos_migrados_hoy: set[int],
    pago_por_antiguo: dict[int, int],
    periodo_por_anio_mes: dict[int, int],
    dry_run: bool,
) -> None:
    errores = report['errores']
    assert isinstance(errores, list)
    filas = conn.execute(
        'SELECT n.pago_id, n.factura_id FROM notas n ORDER BY n.pago_id'
    ).fetchall()
    notas: list[CreditNote] = []
    for fila in filas:
        pago_id = int(fila['pago_id'])
        if pago_id in pagos_a_migrar:
            report['notas_credito'] = int(report['notas_credito']) + 1
        elif pago_id in pago_por_antiguo:
            continue
        else:
            errores.append(f'nota de crédito: pago {pago_id} no migrado')
            continue
        if dry_run:
            continue
        if pago_id not in pagos_migrados_hoy:
            errores.append(f'nota de crédito: pago {pago_id} no migrado hoy')
            continue
        periodo_id = _periodo_de_factura(conn, fila['factura_id'], periodo_por_anio_mes)
        notas.append(
            CreditNote(pago_id=pago_por_antiguo[pago_id], periodo_id=periodo_id)
        )
    if not dry_run and notas:
        for nota in notas:
            uow.credit_notes.save(nota)
        uow.commit()


def _periodo_de_factura(
    conn: sqlite3.Connection,
    factura_id: Any,
    periodo_por_anio_mes: dict[int, int],
) -> int | None:
    if factura_id is None:
        return None
    fila = conn.execute(
        'SELECT periodo FROM facturas WHERE id = ?', (int(factura_id),)
    ).fetchone()
    if fila is None or fila['periodo'] is None:
        return None
    return periodo_por_anio_mes.get(int(fila['periodo']))


def _import_documentos(
    conn: sqlite3.Connection,
    uow: UnitOfWorkPort,
    report: Report,
    reclamo_por_gestion: dict[int, int],
    moved_documentos: dict[int, int],
    ledger: ImportLedgerPort | None,
    dry_run: bool,
    old_path: str,
) -> None:
    """Import legacy ``documentos`` and their ``gestion_documento`` links.

    File bytes come from the legacy DB folder (``files/docs``). Links are
    created only for documents saved in this run (mirroring ``_import_notas``);
    documents already in the ledger had their links created on a previous run,
    so re-runs are no-ops for both. The ledger's ``new_id`` for a document is
    the legacy id: ``Documento`` is hash-keyed without an integer id, and
    ``('documentos', ...)`` entries are never read back.
    """
    errores = report['errores']
    assert isinstance(errores, list)
    ledger_rows: list[LedgerRow] = []
    filas = conn.execute('SELECT * FROM documentos ORDER BY id').fetchall()
    documentos_migrados_hoy: set[int] = set()
    hash_por_documento: dict[int, str] = {}
    for fila in filas:
        documento_id = int(fila['id'])
        if documento_id in moved_documentos:
            continue
        contenido = _leer_archivo(ruta_documento(fila['ruta'], old_path))
        if contenido is None:
            errores.append(f'documento {documento_id}: archivo no encontrado')
            continue
        report['documentos'] = int(report['documentos']) + 1
        documentos_migrados_hoy.add(documento_id)
        if dry_run:
            continue
        guardado = uow.documentos.save(build_documento(fila, contenido))
        hash_por_documento[documento_id] = guardado.document_hash
        ledger_rows.append(('documentos', documento_id, 'documentos', documento_id))
        if len(ledger_rows) >= BATCH_SIZE:
            _guardar_lote(uow, ledger, ledger_rows)
            ledger_rows = []
    if ledger_rows:
        _guardar_lote(uow, ledger, ledger_rows)

    vinculos: list[EntidadDocumento] = []
    vinculos_rows = conn.execute(
        'SELECT gestion_id, documento_id FROM gestion_documento '
        'ORDER BY documento_id, gestion_id'
    ).fetchall()
    for fila_v in vinculos_rows:
        documento_id = int(fila_v['documento_id'])
        if documento_id not in documentos_migrados_hoy:
            continue
        gestion_id = int(fila_v['gestion_id'])
        if gestion_id not in reclamo_por_gestion:
            errores.append(f'documento {documento_id}: gestion {gestion_id} no migrada')
            continue
        report['entidad_documentos'] = int(report['entidad_documentos']) + 1
        if dry_run:
            continue
        vinculos.append(
            EntidadDocumento(
                document_hash=hash_por_documento[documento_id],
                tipo_entidad=TipoEntidadEnum.RECLAMO,
                entidad_id=reclamo_por_gestion[gestion_id],
            )
        )
    if not dry_run and vinculos:
        for vinculo in vinculos:
            uow.entidad_documentos.save(vinculo)
        uow.commit()


def _guardar_lote(
    uow: UnitOfWorkPort,
    ledger: ImportLedgerPort | None,
    ledger_rows: list[LedgerRow],
) -> None:
    if ledger is not None:
        ledger.write(ledger_rows)
    uow.commit()
