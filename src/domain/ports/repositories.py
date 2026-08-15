"""
Puertos de repositorio (interfaces) para el dominio de reclamos.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.exceptions import DuplicateEntityError, EntityNotFoundError
from src.domain.models.entities import (
    CreditNote,
    Documento,
    EntidadDocumento,
    Factura,
    Grupo,
    Pago,
    Periodo,
    Reclamo,
    ReclamoSos,
    TresArrReclamo,
    User,
)


@runtime_checkable
class ReclamoRepositoryPort(Protocol):
    """Puerto del repositorio de reclamos."""

    def list(self, active_only: bool = True) -> list[Reclamo]: ...

    def get(self, reclamo_id: int) -> Reclamo:
        """Obtiene un reclamo por id; lanza EntityNotFoundError si no existe."""
        raise EntityNotFoundError

    def save(self, reclamo: Reclamo) -> Reclamo: ...

    def update(self, reclamo: Reclamo) -> Reclamo: ...

    def set_active(self, reclamo_id: int, active: bool) -> None: ...


@runtime_checkable
class ReclamoSosRepositoryPort(Protocol):
    """Puerto del repositorio de reclamos SOS."""

    def get_by_reclamo_id(self, reclamo_id: int) -> ReclamoSos | None: ...

    def get_by_nro_gestion(self, nro_gestion: int) -> ReclamoSos | None: ...

    def save(self, reclamo_sos: ReclamoSos) -> ReclamoSos: ...

    def update(self, reclamo_sos: ReclamoSos) -> ReclamoSos: ...


@runtime_checkable
class TresArrReclamoRepositoryPort(Protocol):
    """Puerto del repositorio de reclamos de Tres Arroyos."""

    def get_by_reclamo_id(self, reclamo_id: int) -> TresArrReclamo | None: ...

    def list_by_grupo_id(self, grupo_id: int) -> list[TresArrReclamo]: ...

    def save(self, tres_arr: TresArrReclamo) -> TresArrReclamo: ...

    def update(self, tres_arr: TresArrReclamo) -> TresArrReclamo: ...


@runtime_checkable
class GrupoRepositoryPort(Protocol):
    """Puerto del repositorio de grupos de reclamos de Tres Arroyos."""

    def get(self, grupo_id: int) -> Grupo:
        """Obtiene un grupo por id; lanza EntityNotFoundError si no existe."""
        raise EntityNotFoundError

    def get_by_nombre(self, grupo: str) -> Grupo | None: ...

    def save(self, grupo: Grupo) -> Grupo:
        """Guarda un grupo; lanza DuplicateEntityError si el nombre ya existe."""
        raise DuplicateEntityError

    def update(self, grupo: Grupo) -> Grupo: ...

    def list(self) -> list[Grupo]: ...


@runtime_checkable
class PagoRepositoryPort(Protocol):
    """Puerto del repositorio de pagos."""

    def list(self, reclamo_id: int | None = None) -> list[Pago]: ...

    def get(self, pago_id: int) -> Pago:
        """Obtiene un pago por id; lanza EntityNotFoundError si no existe."""
        raise EntityNotFoundError

    def save(self, pago: Pago) -> Pago: ...

    def delete(self, pago_id: int) -> None: ...


@runtime_checkable
class PeriodoRepositoryPort(Protocol):
    """Puerto del repositorio de periodos de facturación."""

    def list(self) -> list[Periodo]: ...

    def get(self, periodo_id: int) -> Periodo:
        """Obtiene un periodo por id; lanza EntityNotFoundError si no existe."""
        raise EntityNotFoundError

    def save(self, periodo: Periodo) -> Periodo: ...


@runtime_checkable
class FacturaRepositoryPort(Protocol):
    """Puerto del repositorio de facturas."""

    def list_by_periodo(self, periodo_id: int) -> list[Factura]: ...

    def save(self, factura: Factura) -> Factura: ...


@runtime_checkable
class CreditNoteRepositoryPort(Protocol):
    """Puerto del repositorio de notas de crédito."""

    def list_by_periodo(self, periodo_id: int) -> list[CreditNote]: ...

    def get(self, credit_note_id: int) -> CreditNote:
        """Obtiene una nota de crédito por id; lanza EntityNotFoundError si no existe."""
        raise EntityNotFoundError

    def save(self, credit_note: CreditNote) -> CreditNote: ...

    def update(self, credit_note: CreditNote) -> CreditNote: ...

    def delete(self, credit_note_id: int) -> None: ...


@runtime_checkable
class UserRepositoryPort(Protocol):
    """Puerto del repositorio de usuarios."""

    def get_by_username(self, username: str) -> User | None: ...

    def get(self, user_id: int) -> User:
        """Obtiene un usuario por id; lanza EntityNotFoundError si no existe."""
        raise EntityNotFoundError

    def save(self, user: User) -> User:
        """Guarda un usuario; lanza DuplicateEntityError si el username ya existe."""
        raise DuplicateEntityError


@runtime_checkable
class DocumentoRepositoryPort(Protocol):
    """Puerto del repositorio de documentos."""

    def save(self, documento: Documento) -> Documento: ...

    def get_by_hash(self, document_hash: str) -> Documento | None: ...


@runtime_checkable
class EntidadDocumentoRepositoryPort(Protocol):
    """Puerto del repositorio de vínculos entre documentos y entidades."""

    def save(self, entidad: EntidadDocumento) -> EntidadDocumento: ...
