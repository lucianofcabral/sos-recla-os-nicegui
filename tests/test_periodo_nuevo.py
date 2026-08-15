"""Tests for the PeriodoNuevo use case."""

from __future__ import annotations

from src.application.use_cases.periodo import PeriodoNuevo
from src.domain.dto.create import PeriodoCreate
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_periodo_nuevo_computes_anio_mes_and_default_nombre_corto() -> None:
    uow = FakeUnitOfWork()
    with uow:
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=5))
    assert periodo.anio_mes == 202605
    assert periodo.nombre_corto == '05/2026'
    assert uow.committed is True
    assert uow.periodos.list() == [periodo]


def test_periodo_nuevo_respects_explicit_nombre_corto() -> None:
    uow = FakeUnitOfWork()
    with uow:
        periodo = PeriodoNuevo(uow)(
            PeriodoCreate(
                anio=2026,
                mes=5,
                nombre_corto='Mayo 2026',
                nombre_largo='Primer semestre',
            )
        )
    assert periodo.nombre_corto == 'Mayo 2026'
    assert periodo.nombre_largo == 'Primer semestre'
    assert uow.periodos.list()[0].nombre_corto == 'Mayo 2026'
    assert uow.periodos.list()[0].anio_mes == 202605
