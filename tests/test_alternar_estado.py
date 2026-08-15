"""Tests for the ReclamoAlternarEstado use case."""

from __future__ import annotations

import pytest

from src.application.use_cases.reclamo import ReclamoAlternarEstado, SosReclamoNuevo
from src.domain.dto.create import ReclamoCreate, ReclamoSosCreate
from src.domain.exceptions import EntityNotFoundError
from tests.fakes.unit_of_work import FakeUnitOfWork


def _crear_sos(uow: FakeUnitOfWork) -> int:
    sos = SosReclamoNuevo(uow)(
        ReclamoSosCreate(
            reclamo=ReclamoCreate(cliente='ACME', poliza='P-001', dominio='AB1'),
            nro_gestion=1,
        )
    )
    assert sos.reclamo_id is not None
    return sos.reclamo_id


def test_toggle_activo_inactivo_activo() -> None:
    uow = FakeUnitOfWork()
    with uow:
        reclamo_id = _crear_sos(uow)
        alternar = ReclamoAlternarEstado(uow)
        inactivo = alternar(reclamo_id)
        assert inactivo.active is False
        assert uow.reclamos.get(reclamo_id).active is False
        activo = alternar(reclamo_id)
        assert activo.active is True
        assert activo.id == reclamo_id
        assert uow.committed is True


def test_alternar_reclamo_inexistente_raises() -> None:
    uow = FakeUnitOfWork()
    with uow, pytest.raises(EntityNotFoundError):
        ReclamoAlternarEstado(uow)(999)
