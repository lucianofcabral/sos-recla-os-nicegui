"""Tests for the closed-period feature: PeriodoCerrar/PeriodoReabrir and NC guards."""

from __future__ import annotations

import pytest

from src.application.use_cases.nota_credito import (
    AsignarNotaCreditoAPeriodo,
    AsignarNotasCreditoAPeriodo,
    DesasignarNotaCreditoAPeriodo,
    NotaCreditoBorrar,
)
from src.application.use_cases.pago import PagoActualizar, PagoNuevo
from src.application.use_cases.periodo import (
    PeriodoCerrar,
    PeriodoNuevo,
    PeriodoReabrir,
)
from src.application.use_cases.reclamo import SosReclamoNuevo
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum
from src.domain.dto.create import (
    PagoCreate,
    PeriodoCreate,
    ReclamoCreate,
    ReclamoSosCreate,
)
from src.domain.dto.edit import PagoEdit
from src.domain.exceptions import DomainError, EntityNotFoundError
from tests.fakes.unit_of_work import FakeUnitOfWork


def _crear_reclamo(uow: FakeUnitOfWork) -> int:
    reclamo = SosReclamoNuevo(uow)(
        ReclamoSosCreate(
            reclamo=ReclamoCreate(
                cliente='ACME',
                poliza='P-001',
                dominio='AB123CD',
                importe_reclamado=15000.0,
            ),
            nro_gestion=1001,
        )
    )
    assert reclamo.id is not None
    return reclamo.id


def _crear_nc_pago(uow: FakeUnitOfWork, reclamo_id: int) -> int:
    pago = PagoNuevo(uow)(
        PagoCreate(
            reclamo_id=reclamo_id,
            forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
            pagador=AgenteEnum.SOS,
            destinatario=AgenteEnum.SM,
            monto=1000.0,
        )
    )
    assert pago.id is not None
    return pago.id


def _crear_periodo(uow: FakeUnitOfWork, *, cerrado: bool = False) -> int:
    periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=1))
    assert periodo.id is not None
    if cerrado:
        PeriodoCerrar(uow)(periodo.id)
    return periodo.id


def test_periodo_cerrar_marca_cerrado_y_reabrir_lo_desmarca() -> None:
    with FakeUnitOfWork() as uow:
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=1))
        assert periodo.id is not None
        assert periodo.cerrado is False
        cerrado = PeriodoCerrar(uow)(periodo.id)
        assert cerrado.cerrado is True
        assert uow.periodos.get(periodo.id).cerrado is True
        reabierto = PeriodoReabrir(uow)(periodo.id)
        assert reabierto.cerrado is False
        assert uow.periodos.get(periodo.id).cerrado is False


def test_periodo_cerrar_periodo_inexistente_raises_entity_not_found() -> None:
    with FakeUnitOfWork() as uow, pytest.raises(EntityNotFoundError):
        PeriodoCerrar(uow)(999)


def test_nota_credito_borrar_de_periodo_cerrado_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        PeriodoCerrar(uow)(periodo_id)
        with pytest.raises(DomainError):
            NotaCreditoBorrar(uow)(nc.id)


def test_nota_credito_borrar_de_periodo_abierto_funciona() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        NotaCreditoBorrar(uow)(nc.id)
        with pytest.raises(EntityNotFoundError):
            uow.credit_notes.get(nc.id)
        with pytest.raises(EntityNotFoundError):
            uow.pagos.get(1)


def test_pago_actualizar_nc_de_periodo_cerrado_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        pago_id = _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        PeriodoCerrar(uow)(periodo_id)
        with pytest.raises(DomainError):
            PagoActualizar(uow)(PagoEdit(id=pago_id, monto=2500.0))


def test_pago_actualizar_nc_de_periodo_abierto_funciona() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        pago_id = _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        actualizado = PagoActualizar(uow)(PagoEdit(id=pago_id, monto=2500.0))
        assert actualizado.monto == 2500.0
        assert uow.pagos.get(pago_id).monto == 2500.0


def test_pago_actualizar_normal_no_se_bloquea_por_periodo_cerrado() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        pago = PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=reclamo_id,
                forma_pago=FormaPagoEnum.TRANSFERENCIA,
                pagador=AgenteEnum.ASEGURADO,
                destinatario=AgenteEnum.SM,
                monto=1000.0,
            )
        )
        assert pago.id is not None
        _crear_periodo(uow, cerrado=True)
        actualizado = PagoActualizar(uow)(PagoEdit(id=pago.id, monto=2500.0))
        assert actualizado.monto == 2500.0


def test_asignar_nc_a_periodo_cerrado_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow, cerrado=True)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        with pytest.raises(DomainError):
            AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)


def test_asignar_nc_a_periodo_abierto_funciona() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        asignada = AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        assert asignada.periodo_id == periodo_id
        assert uow.credit_notes.get(nc.id).periodo_id == periodo_id


def test_desasignar_nc_de_periodo_cerrado_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        PeriodoCerrar(uow)(periodo_id)
        with pytest.raises(DomainError):
            DesasignarNotaCreditoAPeriodo(uow)(nc.id)


def test_desasignar_nc_de_periodo_abierto_funciona() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        periodo_id = _crear_periodo(uow)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo_id)
        desasignada = DesasignarNotaCreditoAPeriodo(uow)(nc.id)
        assert desasignada.periodo_id is None
        assert uow.credit_notes.get(nc.id).periodo_id is None


def test_desasignar_nc_sin_periodo_funciona() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        _crear_nc_pago(uow, reclamo_id)
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        desasignada = DesasignarNotaCreditoAPeriodo(uow)(nc.id)
        assert desasignada.periodo_id is None


def test_asignar_varias_nc_a_periodo_abierto_funciona() -> None:
    with FakeUnitOfWork() as uow:
        r1 = _crear_reclamo(uow)
        _crear_nc_pago(uow, r1)
        r2 = _crear_reclamo(uow)
        _crear_nc_pago(uow, r2)
        periodo_id = _crear_periodo(uow)

        nc1 = uow.credit_notes.get(1)
        nc2 = uow.credit_notes.get(2)
        assert nc1.id is not None and nc2.id is not None

        asignadas = AsignarNotasCreditoAPeriodo(uow)([nc1.id, nc2.id], periodo_id)
        assert len(asignadas) == 2
        assert all(nc.periodo_id == periodo_id for nc in asignadas)
        assert uow.credit_notes.get(nc1.id).periodo_id == periodo_id
        assert uow.credit_notes.get(nc2.id).periodo_id == periodo_id


def test_asignar_varias_nc_a_periodo_cerrado_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        r1 = _crear_reclamo(uow)
        _crear_nc_pago(uow, r1)
        nc1 = uow.credit_notes.get(1)
        assert nc1.id is not None
        periodo_id = _crear_periodo(uow, cerrado=True)

        with pytest.raises(DomainError):
            AsignarNotasCreditoAPeriodo(uow)([nc1.id], periodo_id)
