import pytest

from src.application.use_cases.nota_credito import (
    AsignarNotaCreditoAPeriodo,
    DesasignarNotaCreditoAPeriodo,
    NotaCreditoBorrar,
)
from src.application.use_cases.pago import PagoActualizar, PagoBorrar, PagoNuevo
from src.application.use_cases.reclamo import SosReclamoNuevo
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum
from src.domain.dto.create import (
    PagoCreate,
    ReclamoCreate,
    ReclamoSosCreate,
)
from src.domain.dto.edit import PagoEdit
from src.domain.exceptions import DomainError, EntityNotFoundError
from src.domain.models.entities import Periodo
from tests.fakes.unit_of_work import FakeUnitOfWork


def _reclamo_data() -> ReclamoCreate:
    return ReclamoCreate(
        cliente='ACME',
        poliza='P-001',
        dominio='AB123CD',
        importe_reclamado=15000.0,
        comentario='sin novedades',
    )


def _crear_reclamo(uow: FakeUnitOfWork) -> int:
    reclamo = SosReclamoNuevo(uow)(
        ReclamoSosCreate(reclamo=_reclamo_data(), nro_gestion=1001)
    )
    assert reclamo.id is not None
    return reclamo.id


def test_pago_nuevo_normal_feliz() -> None:
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
        assert uow.pagos.get(pago.id) == pago
        assert uow.committed is True


def test_pago_nuevo_con_reclamo_inexistente_raises_entity_not_found() -> None:
    with FakeUnitOfWork() as uow, pytest.raises(EntityNotFoundError):
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=999,
                forma_pago=FormaPagoEnum.TRANSFERENCIA,
                pagador=AgenteEnum.ASEGURADO,
                destinatario=AgenteEnum.SM,
                monto=1000.0,
            )
        )


def test_pago_nuevo_con_monto_cero_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        with pytest.raises(DomainError):
            PagoNuevo(uow)(
                PagoCreate(
                    reclamo_id=reclamo_id,
                    forma_pago=FormaPagoEnum.TRANSFERENCIA,
                    pagador=AgenteEnum.ASEGURADO,
                    destinatario=AgenteEnum.SM,
                    monto=0,
                )
            )


def test_pago_nuevo_con_pagador_igual_a_destinatario_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        with pytest.raises(DomainError):
            PagoNuevo(uow)(
                PagoCreate(
                    reclamo_id=reclamo_id,
                    forma_pago=FormaPagoEnum.TRANSFERENCIA,
                    pagador=AgenteEnum.SM,
                    destinatario=AgenteEnum.SM,
                    monto=500.0,
                )
            )


def test_pago_nuevo_nc_fuerza_actores_sos_sm() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        pago = PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.ASEGURADO,
                destinatario=AgenteEnum.SM,
                monto=1000.0,
            )
        )
        assert pago.pagador == AgenteEnum.SOS
        assert pago.destinatario == AgenteEnum.SM
        assert uow.committed is True


def test_pago_nuevo_nc_feliz_crea_pago_y_credit_note() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
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
        assert pago.pagador == AgenteEnum.SOS
        assert pago.destinatario == AgenteEnum.SM
        nc = uow.credit_notes.get(1)
        assert nc.pago_id == pago.id
        assert nc.periodo_id is None
        assert uow.committed is True


def test_pago_actualizar_feliz_cambia_monto() -> None:
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
        actualizado = PagoActualizar(uow)(PagoEdit(id=pago.id, monto=2500.0))
        assert actualizado.monto == 2500.0
        assert uow.pagos.get(pago.id).monto == 2500.0


def test_pago_actualizar_nc_no_permite_cambiar_actores() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
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
        with pytest.raises(DomainError):
            PagoActualizar(uow)(PagoEdit(id=pago.id, destinatario=AgenteEnum.ASEGURADO))


def test_pago_borrar_normal_elimina_el_pago() -> None:
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
        PagoBorrar(uow)(pago.id)
        with pytest.raises(EntityNotFoundError):
            uow.pagos.get(pago.id)


def test_pago_borrar_sobre_nc_raises_domain_error() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
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
        with pytest.raises(DomainError):
            PagoBorrar(uow)(pago.id)


def test_nota_credito_borrar_elimina_nc_y_su_pago() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
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
        nc = uow.credit_notes.get(1)
        assert nc.id is not None
        NotaCreditoBorrar(uow)(nc.id)
        with pytest.raises(EntityNotFoundError):
            uow.credit_notes.get(nc.id)
        with pytest.raises(EntityNotFoundError):
            uow.pagos.get(pago.id)


def test_asignar_nota_credito_a_periodo_feliz() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=1000.0,
            )
        )
        periodo = uow.periodos.save(Periodo(anio=2026, mes=1))
        assert periodo.id is not None
        nc = AsignarNotaCreditoAPeriodo(uow)(1, periodo.id)
        assert nc.periodo_id == periodo.id
        assert uow.committed is True


def test_asignar_nota_credito_a_periodo_inexistente_raises_entity_not_found() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=1000.0,
            )
        )
        with pytest.raises(EntityNotFoundError):
            AsignarNotaCreditoAPeriodo(uow)(1, 999)


def test_desasignar_nota_credito_a_periodo() -> None:
    with FakeUnitOfWork() as uow:
        reclamo_id = _crear_reclamo(uow)
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=1000.0,
            )
        )
        uow.periodos.save(Periodo(anio=2026, mes=1))
        nc = AsignarNotaCreditoAPeriodo(uow)(1, 1)
        assert nc.periodo_id == 1
        nc = DesasignarNotaCreditoAPeriodo(uow)(1)
        assert nc.periodo_id is None
