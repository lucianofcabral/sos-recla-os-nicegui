"""Domain invariant: reclamo text is UPPERCASE, identifiers have no spaces.

``Reclamo``/``ReclamoSos``/``TresArrReclamo``/``Grupo`` normalize free text on
construction (uppercase + collapsed whitespace) and identifiers (poliza/dominio)
get all internal spaces removed. This holds on create AND on every update path
(validated merge, since ``model_copy`` does not run validators).
"""

from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import Workbook

from src.application.import_excel_sos import importar_excel_sos
from src.application.use_cases.lote import LoteTresArrNuevo
from src.application.use_cases.reclamo import SosReclamoActualizar, SosReclamoNuevo
from src.domain.domain_enums import TipoReclamoEnum
from src.domain.dto.create import (
    GestionLoteItem,
    LoteTresArrCreate,
    ReclamoCreate,
    ReclamoSosCreate,
)
from src.domain.dto.edit import ReclamoSosEdit
from src.domain.exceptions import DomainError
from src.domain.models.entities import (
    Grupo,
    Reclamo,
    ReclamoSos,
    TresArrReclamo,
)
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


def _xlsx(rows: list[tuple]) -> bytes:
    wb = Workbook()
    hoja = wb.active
    assert hoja is not None
    hoja.append(HEADERS)
    for fila in rows:
        hoja.append(fila)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# --- 1. entity validators ---------------------------------------------------


def test_reclamo_normaliza_texto_e_identificadores() -> None:
    reclamo = Reclamo(
        cliente='  juan   perez ',
        poliza='5247 614',
        dominio='mtb 828',
        comentario=' robo  parcial ',
    )
    assert reclamo.cliente == 'JUAN PEREZ'
    assert reclamo.poliza == '5247614'
    assert reclamo.dominio == 'MTB828'
    assert reclamo.comentario == 'ROBO PARCIAL'


def test_reclamo_normalizacion_respeta_none() -> None:
    reclamo = Reclamo()
    assert reclamo.cliente is None
    assert reclamo.poliza is None
    assert reclamo.dominio is None
    assert reclamo.comentario is None


def test_reclamo_sos_normaliza_campos_texto() -> None:
    sos = ReclamoSos(
        status='rechazado',
        categoria=' colision ',
        motivo='choque  posterior',
        usuario_carga='  juan   perez ',
        usuario_respuesta='autor',
        itr=7,
    )
    assert sos.status == 'RECHAZADO'
    assert sos.categoria == 'COLISION'
    assert sos.motivo == 'CHOQUE POSTERIOR'
    assert sos.usuario_carga == 'JUAN PEREZ'
    assert sos.usuario_respuesta == 'AUTOR'
    assert sos.itr == 7


def test_tres_arr_y_grupo_normalizan_grupo() -> None:
    assert TresArrReclamo(grupo='lote 1').grupo == 'LOTE 1'
    assert Grupo(grupo=' lote 1 ').grupo == 'LOTE 1'


# --- 2. update path via use case ---------------------------------------------


def _reclamo_data(**overrides: object) -> ReclamoCreate:
    values: dict[str, object] = {
        'tipo_reclamo': TipoReclamoEnum.SOS,
        'cliente': 'ACME',
        'poliza': 'P-001',
        'dominio': 'ab 123 cd',
        'importe_reclamado': 15000.0,
        'comentario': 'sin novedades',
    }
    values.update(overrides)
    return ReclamoCreate(**values)


def test_sos_actualizar_persiste_valores_normalizados() -> None:
    with FakeUnitOfWork() as uow:
        creado = SosReclamoNuevo(uow)(
            ReclamoSosCreate(reclamo=_reclamo_data(), nro_gestion=1001)
        )
        assert creado.id is not None
        actualizado = SosReclamoActualizar(uow)(
            ReclamoSosEdit(
                id=creado.id,
                cliente='  nueva   agencia ',
                dominio='oq n 536',
                poliza='abc 123',
                status='pendiente',
                categoria='hurto  total ',
                motivo=' robo   parcial ',
            )
        )
        assert actualizado.reclamo is not None
        assert actualizado.reclamo.cliente == 'NUEVA AGENCIA'
        assert actualizado.reclamo.dominio == 'OQN536'
        assert actualizado.reclamo.poliza == 'ABC123'
        assert actualizado.status == 'PENDIENTE'
        assert actualizado.categoria == 'HURTO TOTAL'
        assert actualizado.motivo == 'ROBO PARCIAL'
        guardado = uow.reclamos_sos.get_by_reclamo_id(creado.id)
        assert guardado is not None
        assert guardado.reclamo is not None
        assert guardado.reclamo.dominio == 'OQN536'


# --- 3./5. Excel import: create and update persist normalized ----------------


def test_import_excel_crea_seeds_normalizado() -> None:
    contenido = _xlsx(
        [
            (
                135100,
                '9/2/2026',
                '  cliente   nuevo ',
                'OQN 536',
                'abc 123',
                ' robo  parcial ',
                ' usuario   carga ',
                'prestador',
                'en  curso',
                7,
            )
        ]
    )
    uow = FakeUnitOfWork()
    report = importar_excel_sos(contenido=contenido, uow=uow)
    assert report.creados == 1
    assert report.actualizados == 0
    sos = uow.reclamos_sos.get_by_nro_gestion(135100)
    assert sos is not None
    assert sos.reclamo is not None
    assert sos.reclamo.cliente == 'CLIENTE NUEVO'
    assert sos.reclamo.dominio == 'OQN536'
    assert sos.reclamo.poliza == 'ABC123'
    assert sos.motivo == 'ROBO PARCIAL'
    assert sos.usuario_carga == 'USUARIO CARGA'
    assert sos.usuario_respuesta == 'PRESTADOR'
    assert sos.status == 'EN CURSO'


def test_import_excel_actualiza_persiste_normalizado() -> None:
    uow = FakeUnitOfWork()
    with uow:
        creado = SosReclamoNuevo(uow)(
            ReclamoSosCreate(
                reclamo=ReclamoCreate(
                    tipo_reclamo=TipoReclamoEnum.SOS,
                    cliente='Viejo',
                    poliza='P-200',
                    dominio='AB200CD',
                ),
                nro_gestion=135200,
                status='Abierto',
            )
        )
        assert creado.reclamo_id is not None
        uow.commit()
    contenido = _xlsx(
        [
            (
                135200,
                '1/3/2026',
                '  cliente   actualizado ',
                'OQN 536',
                'mtb 828',
                '  robo   parcial ',
                'operador uno',
                None,
                'rechazado',
                4,
            )
        ]
    )
    report = importar_excel_sos(contenido=contenido, uow=uow)
    assert report.creados == 0
    assert report.actualizados == 1
    sos = uow.reclamos_sos.get_by_nro_gestion(135200)
    assert sos is not None
    assert sos.reclamo is not None
    assert sos.reclamo.cliente == 'CLIENTE ACTUALIZADO'
    assert sos.reclamo.dominio == 'OQN536'
    assert sos.reclamo.poliza == 'MTB828'
    assert sos.motivo == 'ROBO PARCIAL'
    assert sos.usuario_carga == 'OPERADOR UNO'
    assert sos.status == 'RECHAZADO'


# --- 4. grupo duplicate check uses the normalized name -----------------------


def test_lote_grupo_duplicado_con_casing_distinto() -> None:
    with FakeUnitOfWork() as uow:
        primero = LoteTresArrNuevo(uow)(
            LoteTresArrCreate(
                grupo='LOTE 1',
                gestiones=[GestionLoteItem(reclamo=_reclamo_data())],
            )
        )
        assert primero.grupo == 'LOTE 1'
        with pytest.raises(DomainError, match="el grupo 'LOTE 1' ya existe"):
            LoteTresArrNuevo(uow)(
                LoteTresArrCreate(
                    grupo='lote 1',
                    gestiones=[GestionLoteItem(reclamo=_reclamo_data())],
                )
            )
        assert len(uow.grupos.list()) == 1
