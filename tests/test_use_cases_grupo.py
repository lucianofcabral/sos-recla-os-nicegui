"""Tests for the grupo rename use case and the grupo detalle query."""

from datetime import datetime

import pytest

from src.application.use_cases.reclamo import ActualizarGrupo
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoReclamoEnum
from src.domain.exceptions import (
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from src.domain.models.entities import Grupo, Pago, Reclamo, TresArrReclamo
from tests.fakes.unit_of_work import FakeUnitOfWork


def _crear_grupo(uow: FakeUnitOfWork, nombre: str) -> Grupo:
    grupo = uow.grupos.save(Grupo(grupo=nombre, fecha_creacion=datetime.now()))
    assert grupo.id is not None
    for i, (dominio, con_pago) in enumerate(
        (('AA111', False), ('BB222', True)), start=1
    ):
        reclamo = uow.reclamos.save(
            Reclamo(
                tipo_reclamo=TipoReclamoEnum.TRESA,
                active=True,
                cliente=f'CLIENTE {i}',
                poliza=f'P-{i:03d}',
                dominio=dominio,
                importe_reclamado=1000.0 * i,
            )
        )
        assert reclamo.id is not None
        uow.tres_arr.save(
            TresArrReclamo(
                reclamo_id=reclamo.id,
                reclamo=reclamo,
                grupo=grupo.grupo,
                grupo_id=grupo.id,
            )
        )
        if con_pago:
            uow.pagos.save(
                Pago(
                    reclamo_id=reclamo.id,
                    forma_pago=FormaPagoEnum.TRANSFERENCIA,
                    pagador=AgenteEnum.SM,
                    destinatario=AgenteEnum.PRESTADOR,
                    monto=1000.0 * i,
                )
            )
    return grupo


def test_renombrar_grupo_actualiza_grupo_y_todos_sus_reclamos() -> None:
    uow = FakeUnitOfWork()
    grupo = _crear_grupo(uow, 'GRUPO A')
    assert grupo.id is not None
    with uow:
        updated = ActualizarGrupo(uow)(grupo.id, 'GRUPO B')

    assert updated.grupo == 'GRUPO B'
    assert updated.id == grupo.id
    assert uow.grupos.get(grupo.id).grupo == 'GRUPO B'
    tres_arrs = uow.tres_arr.list_by_grupo_id(grupo.id)
    assert len(tres_arrs) == 2
    assert all(t.grupo == 'GRUPO B' for t in tres_arrs)
    assert all(t.grupo_id == grupo.id for t in tres_arrs)
    pagos = uow.pagos.list()
    assert len(pagos) == 1
    assert pagos[0].monto == 2000.0
    assert pagos[0].reclamo_id in {t.reclamo_id for t in tres_arrs}
    assert uow.committed is True


def test_renombrar_mismo_nombre_no_commitea() -> None:
    uow = FakeUnitOfWork()
    grupo = _crear_grupo(uow, 'GRUPO A')
    assert grupo.id is not None
    with uow:
        result = ActualizarGrupo(uow)(grupo.id, 'GRUPO A')

    assert result.grupo == 'GRUPO A'
    assert result.id == grupo.id
    assert uow.committed is False
    assert len(uow.tres_arr.list_by_grupo_id(grupo.id)) == 2


def test_renombrar_nombre_vacio_levanta_error() -> None:
    uow = FakeUnitOfWork()
    grupo = _crear_grupo(uow, 'GRUPO A')
    assert grupo.id is not None
    with pytest.raises(DomainError, match='no puede estar vacío'):
        ActualizarGrupo(uow)(grupo.id, '   ')


def test_renombrar_a_nombre_existente_levanta_error() -> None:
    uow = FakeUnitOfWork()
    grupo_a = _crear_grupo(uow, 'GRUPO A')
    grupo_b = _crear_grupo(uow, 'GRUPO B')
    assert grupo_a.id is not None
    assert grupo_b.id is not None
    uow.commit()

    with pytest.raises(DuplicateEntityError, match='GRUPO B'):
        ActualizarGrupo(uow)(grupo_a.id, 'GRUPO B')

    assert uow.grupos.get(grupo_a.id).grupo == 'GRUPO A'
    assert uow.grupos.get(grupo_b.id).grupo == 'GRUPO B'
    assert uow.grupos.get_by_nombre('GRUPO A') is not None
    tres_a = uow.tres_arr.list_by_grupo_id(grupo_a.id)
    assert len(tres_a) == 2
    assert all(t.grupo == 'GRUPO A' for t in tres_a)


def test_renombrar_grupo_inexistente_levanta_error() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(EntityNotFoundError):
        ActualizarGrupo(uow)(999, 'GRUPO X')


def test_list_grupo_detalle_devuelve_items_con_cant_pagos() -> None:
    uow = FakeUnitOfWork()
    grupo = _crear_grupo(uow, 'GRUPO A')
    assert grupo.id is not None

    items = uow.list_grupo_detalle(grupo.id)

    assert len(items) == 2
    by_dominio = {item.dominio: item for item in items}
    assert by_dominio['AA111'].cant_pagos == 0
    assert by_dominio['AA111'].pagos == []
    assert by_dominio['AA111'].cliente == 'CLIENTE 1'
    assert by_dominio['AA111'].importe_reclamado == 1000.0
    assert by_dominio['BB222'].cant_pagos == 1
    assert by_dominio['BB222'].pagos[0].monto == 2000.0
    assert by_dominio['BB222'].pagos[0].forma_pago == FormaPagoEnum.TRANSFERENCIA
    assert by_dominio['BB222'].pagos[0].nro_gestion is None
    ids_esperados = {t.reclamo_id for t in uow.tres_arr.list_by_grupo_id(grupo.id)}
    assert {item.reclamo_id for item in items} == ids_esperados
