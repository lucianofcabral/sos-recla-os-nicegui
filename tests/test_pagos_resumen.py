"""Resumen: nota de crédito pagos must be deleted via NotaCreditoBorrar."""

from __future__ import annotations

import pytest

from src.application.use_cases.nota_credito import NotaCreditoBorrar
from src.application.use_cases.pago import PagoBorrar, PagoNuevo
from src.application.use_cases.reclamo import SosReclamoNuevo
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum
from src.domain.dto.create import PagoCreate, ReclamoCreate, ReclamoSosCreate
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


def test_eliminar_pago_nc_usa_nota_credito_borrar() -> None:
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

        with pytest.raises(DomainError):
            PagoBorrar(uow)(pago.id)

        NotaCreditoBorrar(uow)(nc.id)
        with pytest.raises(EntityNotFoundError):
            uow.pagos.get(pago.id)
        with pytest.raises(EntityNotFoundError):
            uow.credit_notes.get(nc.id)
