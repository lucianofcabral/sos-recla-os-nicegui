"""Tests for the FacturaNueva use case."""

from __future__ import annotations

from src.application.use_cases.factura import FacturaNueva
from src.application.use_cases.periodo import PeriodoNuevo
from src.domain.dto.create import FacturaCreate, PeriodoCreate
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_factura_nueva_guarda_con_importe() -> None:
    uow = FakeUnitOfWork()
    with uow:
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=6))
        assert periodo.id is not None
        factura = FacturaNueva(uow)(
            FacturaCreate(periodo_id=periodo.id, nro_factura='A-0001', importe=1234.5)
        )
    assert factura.id is not None
    assert factura.importe == 1234.5
    assert factura.nro_factura == 'A-0001'
    assert uow.committed is True
    lista = uow.facturas.list_by_periodo(periodo.id)
    assert len(lista) == 1
    assert lista[0].importe == 1234.5


def test_factura_nueva_default_importe_zero() -> None:
    uow = FakeUnitOfWork()
    with uow:
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=7))
        assert periodo.id is not None
        factura = FacturaNueva(uow)(
            FacturaCreate(periodo_id=periodo.id, nro_factura='B-0002')
        )
    assert factura.importe == 0.0
