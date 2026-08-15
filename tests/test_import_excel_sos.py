"""Tests for the SOS Excel import (upsert keyed by N° Gestión)."""

from __future__ import annotations

import re
import zipfile
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from src.application.import_excel_sos import (
    SosExcelRow,
    importar_excel_sos,
    parse_excel_sos,
)
from src.domain.domain_enums import TipoReclamoEnum
from src.domain.models.entities import Reclamo, ReclamoSos
from tests.fakes.unit_of_work import FakeUnitOfWork

HEADERS = [
    'N° Gestión',
    'Fecha',
    'Cliente',
    'Dominio',
    'Póliza',
    'Motivo',
    'Usuario Carga',
    'Usuario Respuesta',
    'Estado',
    'ITR',
]


def _xlsx(rows: list[tuple], headers: list[str] | None = None) -> bytes:
    wb = Workbook()
    hoja = wb.active
    assert hoja is not None
    hoja.append(headers or HEADERS)
    for fila in rows:
        hoja.append(fila)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _sembrar_sos(
    uow: FakeUnitOfWork,
    nro_gestion: int,
    *,
    cliente: str = 'Cliente Viejo',
    dominio: str = 'AB200CD',
    poliza: str = 'P-200',
    status: str = 'Abierto',
    itr: int | None = 5,
    importe: float = 1234.5,
) -> None:
    reclamo = uow.reclamos.save(
        Reclamo(
            tipo_reclamo=TipoReclamoEnum.SOS,
            cliente=cliente,
            dominio=dominio,
            poliza=poliza,
            importe_reclamado=importe,
            active=True,
        )
    )
    assert reclamo.id is not None
    uow.reclamos_sos.save(
        ReclamoSos(
            reclamo_id=reclamo.id,
            reclamo=reclamo,
            nro_gestion=nro_gestion,
            status=status,
            itr=itr,
        )
    )


def _reclamo_de(uow: FakeUnitOfWork, nro_gestion: int) -> tuple[ReclamoSos, Reclamo]:
    sos = uow.reclamos_sos.get_by_nro_gestion(nro_gestion)
    assert sos is not None
    reclamo = sos.reclamo
    if reclamo is None:
        assert sos.reclamo_id is not None
        reclamo = uow.reclamos.get(sos.reclamo_id)
    return sos, reclamo


def test_parse_devuelve_filas_validas_y_errores() -> None:
    contenido = _xlsx(
        [
            (
                135151,
                datetime(2026, 2, 5),
                'Cliente Uno',
                'AB123CD',
                'P-1',
                'Robo',
                'carga',
                'resp',
                'En Curso',
                7,
            ),
            (None, None, None, None, None, None, None, None, None, None),
            ('abc', '9/2/2026', None, None, None, None, None, None, None, None),
        ]
    )
    filas, errores = parse_excel_sos(contenido)
    assert len(filas) == 1
    assert len(errores) == 1
    assert errores[0] == 'Fila 4: N° Gestión inválido'
    fila = filas[0]
    assert fila.nro_gestion == 135151
    assert fila.fecha == date(2026, 2, 5)
    assert fila.cliente == 'Cliente Uno'
    assert fila.dominio == 'AB123CD'
    assert fila.poliza == 'P-1'
    assert fila.motivo == 'Robo'
    assert fila.usuario_carga == 'carga'
    assert fila.usuario_respuesta == 'resp'
    assert fila.status == 'En Curso'
    assert fila.itr == 7


def test_parse_fecha_como_texto_y_nro_como_float() -> None:
    contenido = _xlsx(
        [(135151.0, '9/2/2026', 'Cliente', 'AB123CD', 'P-1', None, None, None, None, 0)]
    )
    filas, errores = parse_excel_sos(contenido)
    assert errores == []
    assert len(filas) == 1
    assert filas[0].nro_gestion == 135151
    assert filas[0].fecha == date(2026, 2, 9)
    assert filas[0].poliza == 'P-1'
    assert filas[0].status is None


def test_parse_falta_columna_nro_gestion_levanta_value_error() -> None:
    headers_sin_nro = [h for h in HEADERS if h != 'N° Gestión']
    contenido = _xlsx([(datetime(2026, 2, 5), 'Cliente', 'AB123CD')], headers_sin_nro)
    with pytest.raises(ValueError, match='N° Gestión'):
        parse_excel_sos(contenido)


def test_importar_crea_sos_cada_detalle_y_fecha_sembrada() -> None:
    contenido = _xlsx(
        [
            (
                135100,
                datetime(2026, 2, 5),
                'Cliente Nuevo',
                'AB123CD',
                'P-100',
                'Robo',
                'carga1',
                'resp1',
                'En Curso',
                7,
            ),
            (
                135101,
                '9/2/2026',
                'Cliente Texto',
                'CD456EF',
                'P-101',
                None,
                None,
                None,
                'RECHAZADO',
                '0',
            ),
        ]
    )
    uow = FakeUnitOfWork()
    report = importar_excel_sos(contenido=contenido, uow=uow)
    assert report.creados == 2
    assert report.actualizados == 0
    assert report.errores == []

    sos, reclamo = _reclamo_de(uow, 135100)
    assert sos.nro_gestion == 135100
    assert sos.motivo == 'ROBO'
    assert sos.usuario_carga == 'CARGA1'
    assert sos.usuario_respuesta == 'RESP1'
    assert sos.status == 'EN CURSO'
    assert sos.itr == 7
    assert reclamo.tipo_reclamo is TipoReclamoEnum.SOS
    assert reclamo.cliente == 'CLIENTE NUEVO'
    assert reclamo.dominio == 'AB123CD'
    assert reclamo.poliza == 'P-100'
    assert reclamo.importe_reclamado == 0.0
    assert reclamo.active is True
    assert reclamo.created_at == datetime(2026, 2, 5, 0, 0)

    sos2, reclamo2 = _reclamo_de(uow, 135101)
    assert sos2.status == 'RECHAZADO'
    assert sos2.itr is None
    assert sos2.usuario_carga is None
    assert reclamo2.created_at == datetime(2026, 2, 9, 0, 0)
    assert uow.committed is True


def test_importar_actualiza_solo_campos_no_vacios() -> None:
    uow = FakeUnitOfWork()
    _sembrar_sos(uow, 135200)
    contenido = _xlsx(
        [(135200, '1/3/2026', '', 'ZZ999ZZ', '', None, None, None, 'RECHAZADO', 4)]
    )
    report = importar_excel_sos(contenido=contenido, uow=uow)
    assert report.creados == 0
    assert report.actualizados == 1
    assert report.errores == []

    sos, reclamo = _reclamo_de(uow, 135200)
    assert sos.status == 'RECHAZADO'
    assert sos.itr == 4
    assert reclamo.cliente == 'CLIENTE VIEJO'
    assert reclamo.dominio == 'ZZ999ZZ'
    assert reclamo.poliza == ''
    assert reclamo.importe_reclamado == 1234.5
    assert reclamo.active is True


def test_importar_dry_run_no_escribe_ni_commitea() -> None:
    uow = FakeUnitOfWork()
    _sembrar_sos(uow, 135200)
    reclamos_antes = len(uow.reclamos.list(active_only=False))
    sos_antes = len(
        [s for s in uow.reclamos_sos._store.values() if s.nro_gestion is not None]
    )
    contenido = _xlsx(
        [
            (
                135300,
                datetime(2026, 2, 5),
                'Nuevo',
                'AB123CD',
                'P-1',
                None,
                None,
                None,
                None,
                1,
            ),
            (135200, '1/3/2026', 'Viejo', None, None, None, None, None, None, None),
        ]
    )
    report = importar_excel_sos(contenido=contenido, uow=uow, dry_run=True)
    assert report.creados == 1
    assert report.actualizados == 1
    assert report.errores == []
    assert len(uow.reclamos.list(active_only=False)) == reclamos_antes
    sos_ahora = len(
        [s for s in uow.reclamos_sos._store.values() if s.nro_gestion is not None]
    )
    assert sos_ahora == sos_antes
    assert uow.committed is False


def test_errores_de_filas_no_impiden_importar_validas() -> None:
    contenido = _xlsx(
        [
            (
                135300,
                datetime(2026, 2, 5),
                'Cliente',
                'AB123CD',
                'P-1',
                None,
                None,
                None,
                None,
                None,
            ),
            (0, None, None, None, None, None, None, None, None, None),
        ]
    )
    uow = FakeUnitOfWork()
    report = importar_excel_sos(contenido=contenido, uow=uow)
    assert report.creados == 1
    assert report.actualizados == 0
    assert report.errores == ['Fila 3: N° Gestión inválido']
    sos, reclamo = _reclamo_de(uow, 135300)
    assert sos.nro_gestion == 135300
    assert reclamo.cliente == 'CLIENTE'


def test_importar_valida_nro_gestion_cero_y_vacio() -> None:
    contenido = _xlsx(
        [
            (0, None, None, None, None, None, None, None, None, None),
            (None, None, None, None, None, None, None, None, None, None),
            (
                135400,
                '5/2/2026',
                'Cliente',
                None,
                None,
                None,
                None,
                None,
                'RECHAZADO',
                None,
            ),
        ]
    )
    uow = FakeUnitOfWork()
    report = importar_excel_sos(contenido=contenido, uow=uow)
    assert report.creados == 1
    assert report.actualizados == 0
    assert report.errores == ['Fila 2: N° Gestión inválido']
    sos, _ = _reclamo_de(uow, 135400)
    assert sos.status == 'RECHAZADO'


def _xlsx_con_dimension_rota(rows: list[tuple]) -> bytes:
    """Build an xlsx whose sheet declares ``<dimension ref="A1"/>`` (broken exporters)."""
    contenido = _xlsx(rows)
    origen = zipfile.ZipFile(BytesIO(contenido))
    destino = BytesIO()
    try:
        with zipfile.ZipFile(destino, 'w') as salida:
            for item in origen.infolist():
                data = origen.read(item.filename)
                if item.filename == 'xl/worksheets/sheet1.xml':
                    xml = data.decode('utf-8')
                    xml = re.sub(r'<dimension ref="[^"]*"', '<dimension ref="A1"', xml)
                    data = xml.encode('utf-8')
                salida.writestr(item, data)
    finally:
        origen.close()
    return destino.getvalue()


def test_parse_archivo_con_dimension_rota() -> None:
    contenido = _xlsx_con_dimension_rota(
        [
            (
                135151.0,
                '9/2/2026',
                'Cliente X',
                'AB123CD',
                'P-1',
                None,
                None,
                None,
                'RECHAZADO',
                '0',
            )
        ]
    )
    filas, errores = parse_excel_sos(contenido)
    assert errores == []
    assert len(filas) == 1
    assert filas[0].nro_gestion == 135151
    assert filas[0].status == 'RECHAZADO'
    assert filas[0].itr is None


def test_parse_archivo_real_del_repo() -> None:
    ruta = Path(__file__).resolve().parents[1] / 'Gestión Reclamos Y Reintegros.xlsx'
    if not ruta.exists():
        pytest.skip('archivo de muestra ausente')
    filas, errores = parse_excel_sos(ruta.read_bytes())
    assert errores == []
    assert filas
    assert filas[0].nro_gestion == 135151
    assert filas[0].fecha == date(2026, 2, 9)
    assert filas[0].status == 'RECHAZADO'
    assert filas[0].itr is None


def test_parse_acepta_variantes_de_encabezado() -> None:
    headers = [
        'Nº de GESTIÓN',
        'FECHA',
        'cliente',
        'dominio',
        'póliza',
        'Tipo',
        'Motivo',
        'N° Caso',
        'USUARIO CARGA',
        'USUARIO RESPUESTA',
        'estado',
        'itr',
    ]
    contenido = _xlsx(
        [
            (
                135600,
                '9/2/2026',
                'C1',
                'AB1',
                'P1',
                'X',
                'M',
                '99',
                'U1',
                'U2',
                'RECHAZADO',
                '4',
            )
        ],
        headers,
    )
    filas, errores = parse_excel_sos(contenido)
    assert errores == []
    assert len(filas) == 1
    assert filas[0].nro_gestion == 135600
    assert filas[0].status == 'RECHAZADO'
    assert filas[0].usuario_carga == 'U1'
    assert filas[0].usuario_respuesta == 'U2'
    assert filas[0].itr == 4


def test_parse_falta_columna_reporte_columnas_detectadas() -> None:
    contenido = _xlsx(
        [('Cliente', 'AB1', 'P1')],
        ['Cliente', 'Dominio', 'Póliza'],
    )
    with pytest.raises(
        ValueError, match='Columnas detectadas: Cliente, Dominio, Póliza'
    ):
        parse_excel_sos(contenido)


def test_parse_fila_estructura_tipada() -> None:
    contenido = _xlsx(
        [
            (
                135500,
                datetime(2026, 1, 15),
                'C',
                'AB1',
                '',
                None,
                'u',
                None,
                'Estado',
                '3',
            )
        ]
    )
    filas, errores = parse_excel_sos(contenido)
    assert errores == []
    assert len(filas) == 1
    fila: SosExcelRow = filas[0]
    assert fila.poliza == ''
    assert fila.fecha == date(2026, 1, 15)
    assert fila.usuario_carga == 'u'
    assert fila.usuario_respuesta is None
    assert fila.itr == 3
