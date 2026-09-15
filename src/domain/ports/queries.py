"""Query port: read-only projections exposed by the unit of work."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.dto.read import (
    CicloCard,
    GrupoReclamoItem,
    NotaCreditoSinAsignarItem,
    PagoListFilter,
    PagoListItem,
    PagoListPage,
    ReclamoHomeFilter,
    ReclamoHomeItem,
    ReclamoHomePage,
)


@runtime_checkable
class QueryPort(Protocol):
    """Read-only queries over the unit of work for the UI lists."""

    def list_home(
        self, filtro: ReclamoHomeFilter | None = None
    ) -> list[ReclamoHomeItem]: ...

    def list_home_pagina(
        self,
        filtro: ReclamoHomeFilter | None = None,
        *,
        offset: int = 0,
        limit: int | None = 20,
        sort_by: str | None = None,
        descending: bool = False,
    ) -> ReclamoHomePage: ...

    def list_grupos(self) -> list[str]: ...

    def list_pagos_con_detalle(
        self, filtro: PagoListFilter | None = None
    ) -> list[PagoListItem]: ...

    def list_pagos_pagina(
        self,
        filtro: PagoListFilter | None = None,
        *,
        offset: int = 0,
        limit: int | None = 20,
    ) -> PagoListPage: ...

    def list_grupo_detalle(self, grupo_id: int) -> list[GrupoReclamoItem]: ...

    def list_ciclos(self) -> list[CicloCard]: ...

    def list_notas_credito_por_periodo(
        self, periodo_id: int
    ) -> list[NotaCreditoSinAsignarItem]: ...

    def list_notas_credito_sin_asignar(self) -> list[NotaCreditoSinAsignarItem]: ...
