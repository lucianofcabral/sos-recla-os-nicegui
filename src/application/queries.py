"""Thin query wrappers so the UI depends on functions, not the protocol."""

from src.domain.dto.read import (
    CicloCard,
    NotaCreditoSinAsignarItem,
    PagoListFilter,
    PagoListItem,
    ReclamoHomeFilter,
    ReclamoHomeItem,
)
from src.domain.ports.queries import QueryPort


def list_home(
    uow: QueryPort, filtro: ReclamoHomeFilter | None = None
) -> list[ReclamoHomeItem]:
    return uow.list_home(filtro)


def list_grupos(uow: QueryPort) -> list[str]:
    return uow.list_grupos()


def list_pagos_con_detalle(
    uow: QueryPort, filtro: PagoListFilter | None = None
) -> list[PagoListItem]:
    return uow.list_pagos_con_detalle(filtro)


def list_ciclos(uow: QueryPort) -> list[CicloCard]:
    return uow.list_ciclos()


def list_notas_credito_por_periodo(
    uow: QueryPort, periodo_id: int
) -> list[NotaCreditoSinAsignarItem]:
    return uow.list_notas_credito_por_periodo(periodo_id)


def list_notas_credito_sin_asignar(
    uow: QueryPort,
) -> list[NotaCreditoSinAsignarItem]:
    return uow.list_notas_credito_sin_asignar()
