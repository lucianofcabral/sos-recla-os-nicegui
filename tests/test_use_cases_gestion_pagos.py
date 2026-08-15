"""Tests for OtrosReclamoConPagosNuevo (reclamo + pagos in one transaction)."""

import pytest

from src.application.use_cases.reclamo import OtrosReclamoConPagosNuevo
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoReclamoEnum
from src.domain.dto.create import (
    OtrosReclamoCreate,
    PagoReclamoCreate,
    ReclamoCreate,
)
from src.domain.exceptions import DomainError
from tests.fakes.unit_of_work import FakeUnitOfWork


def _reclamo_data() -> ReclamoCreate:
    return ReclamoCreate(
        cliente='ACME',
        poliza='P-001',
        dominio='AB123CD',
        importe_reclamado=15000.0,
        comentario='sin novedades',
    )


def _pago(**overrides: object) -> PagoReclamoCreate:
    values: dict[str, object] = {
        'forma_pago': FormaPagoEnum.TRANSFERENCIA,
        'pagador': AgenteEnum.ASEGURADO,
        'destinatario': AgenteEnum.SM,
        'monto': 1000.0,
    }
    values.update(overrides)
    return PagoReclamoCreate(**values)


def test_crea_reclamo_y_dos_pagos_en_una_transaccion() -> None:
    with FakeUnitOfWork() as uow:
        pagos = [
            _pago(),
            _pago(
                forma_pago=FormaPagoEnum.EFECTIVO,
                pagador=AgenteEnum.SM,
                destinatario=AgenteEnum.PRESTADOR,
                monto=500.0,
            ),
        ]
        reclamo = OtrosReclamoConPagosNuevo(uow)(
            OtrosReclamoCreate(reclamo=_reclamo_data()), pagos
        )
        assert reclamo.id is not None
        assert reclamo.tipo_reclamo == TipoReclamoEnum.OTROS
        assert reclamo.active is True
        assert uow.committed is True
        assert len(uow.reclamos.list(active_only=False)) == 1
        guardados = uow.pagos.list(reclamo_id=reclamo.id)
        assert len(guardados) == 2
        assert all(pago.reclamo_id == reclamo.id for pago in guardados)
        assert {pago.monto for pago in guardados} == {500.0, 1000.0}


def test_pago_nc_fuerza_sos_sm_y_crea_credit_note() -> None:
    with FakeUnitOfWork() as uow:
        pago_nc = _pago(forma_pago=FormaPagoEnum.NOTA_DE_CREDITO)
        reclamo = OtrosReclamoConPagosNuevo(uow)(
            OtrosReclamoCreate(reclamo=_reclamo_data()), [pago_nc]
        )
        assert reclamo.id is not None
        guardados = uow.pagos.list(reclamo_id=reclamo.id)
        assert len(guardados) == 1
        pago = guardados[0]
        assert pago.pagador == AgenteEnum.SOS
        assert pago.destinatario == AgenteEnum.SM
        nc = uow.credit_notes.get(1)
        assert nc.pago_id == pago.id
        assert nc.periodo_id is None
        assert uow.committed is True


def test_pago_monto_invalido_no_crea_nada() -> None:
    with FakeUnitOfWork() as uow:
        with pytest.raises(DomainError):
            OtrosReclamoConPagosNuevo(uow)(
                OtrosReclamoCreate(reclamo=_reclamo_data()), [_pago(monto=0)]
            )
        assert uow.reclamos.list(active_only=False) == []
        assert uow.pagos.list() == []
        assert uow.credit_notes._store == {}
        assert uow.committed is False


def test_pago_pagador_igual_destinatario_no_crea_nada() -> None:
    with FakeUnitOfWork() as uow:
        with pytest.raises(DomainError):
            OtrosReclamoConPagosNuevo(uow)(
                OtrosReclamoCreate(reclamo=_reclamo_data()),
                [_pago(pagador=AgenteEnum.SM, destinatario=AgenteEnum.SM)],
            )
        assert uow.reclamos.list(active_only=False) == []
        assert uow.pagos.list() == []


def test_error_en_segundo_pago_rolls_back_todo() -> None:
    with FakeUnitOfWork() as uow:
        with pytest.raises(DomainError):
            OtrosReclamoConPagosNuevo(uow)(
                OtrosReclamoCreate(reclamo=_reclamo_data()),
                [_pago(), _pago(monto=-5)],
            )
        assert uow.reclamos.list(active_only=False) == []
        assert uow.pagos.list() == []
        assert uow.committed is False


def test_sin_pagos_crea_reclamo_normal() -> None:
    with FakeUnitOfWork() as uow:
        reclamo = OtrosReclamoConPagosNuevo(uow)(
            OtrosReclamoCreate(reclamo=_reclamo_data())
        )
        assert reclamo.id is not None
        assert reclamo.tipo_reclamo == TipoReclamoEnum.OTROS
        assert uow.pagos.list() == []
        assert uow.committed is True
