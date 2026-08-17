"""Query port: read-only projections exposed by the unit of work."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.dto.read import (
    CicloCard,
    GrupoReclamoItem,
    PagoListFilter,
    PagoListItem,
    ReclamoHomeFilter,
    ReclamoHomeItem,
)


@runtime_checkable
class QueryPort(Protocol):
    """Read-only queries over the unit of work for the UI lists."""

    def list_home(
        self, filtro: ReclamoHomeFilter | None = None
    ) -> list[ReclamoHomeItem]: ...

    def list_grupos(self) -> list[str]: ...

    def list_pagos_con_detalle(
        self, filtro: PagoListFilter | None = None
    ) -> list[PagoListItem]: ...

    def list_grupo_detalle(self, grupo_id: int) -> list[GrupoReclamoItem]: ...

    def list_ciclos(self) -> list[CicloCard]: ...
