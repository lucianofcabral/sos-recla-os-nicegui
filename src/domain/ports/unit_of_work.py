"""
Puerto de la unidad de trabajo.
"""

from __future__ import annotations

from typing import Protocol, Self

from src.domain.ports.repositories import (
    CreditNoteRepositoryPort,
    DocumentoRepositoryPort,
    EntidadDocumentoRepositoryPort,
    FacturaRepositoryPort,
    GrupoRepositoryPort,
    PagoRepositoryPort,
    PeriodoRepositoryPort,
    ReclamoRepositoryPort,
    ReclamoSosRepositoryPort,
    TresArrReclamoRepositoryPort,
    UserRepositoryPort,
)


class UnitOfWorkPort(Protocol):
    """
    Puerto de la unidad de trabajo.

    El commit es explícito: los use cases lo llaman; al salir del contexto
    solo se hace rollback.
    """

    reclamos: ReclamoRepositoryPort
    reclamos_sos: ReclamoSosRepositoryPort
    tres_arr: TresArrReclamoRepositoryPort
    grupos: GrupoRepositoryPort
    pagos: PagoRepositoryPort
    periodos: PeriodoRepositoryPort
    facturas: FacturaRepositoryPort
    credit_notes: CreditNoteRepositoryPort
    users: UserRepositoryPort
    documentos: DocumentoRepositoryPort
    entidad_documentos: EntidadDocumentoRepositoryPort

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool: ...

    def commit(self) -> None: ...
