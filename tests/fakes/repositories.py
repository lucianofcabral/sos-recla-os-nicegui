from __future__ import annotations

from typing import Any, Protocol, cast

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


class EntityWithId(Protocol):
    """Protocol for the fake repos' storage to query entity ids."""

    id: int | None

    def model_copy(
        self, *, update: dict[str, Any] | None = None, deep: bool = False
    ) -> EntityWithId: ...


class _InMemoryRepository[EntityT: EntityWithId]:
    """Base in-memory repo: dict storage keyed by id with auto-increment ids."""

    def __init__(self) -> None:
        self._store: dict[int, EntityT] = {}
        self._next_id: int = 1

    def _next_available_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def _save(self, entity: EntityT) -> EntityT:
        if entity.id is None:
            entity = cast(
                EntityT, entity.model_copy(update={'id': self._next_available_id()})
            )
        elif entity.id in self._store:
            raise DuplicateEntityError(f'entity with id {entity.id} already exists')
        assert entity.id is not None
        self._store[entity.id] = entity
        return entity


class FakeReclamoRepository(_InMemoryRepository[Reclamo]):
    """In-memory implementation of ReclamoRepositoryPort."""

    def list(self, active_only: bool = True) -> list[Reclamo]:
        if active_only:
            return [e for e in self._store.values() if e.active]
        return list(self._store.values())

    def get(self, reclamo_id: int) -> Reclamo:
        try:
            return self._store[reclamo_id]
        except KeyError as exc:
            raise EntityNotFoundError(f'reclamo {reclamo_id} not found') from exc

    def save(self, reclamo: Reclamo) -> Reclamo:
        return self._save(reclamo)

    def update(self, reclamo: Reclamo) -> Reclamo:
        if reclamo.id is None or reclamo.id not in self._store:
            raise EntityNotFoundError(f'reclamo {reclamo.id} not found')
        self._store[reclamo.id] = reclamo
        return reclamo

    def set_active(self, reclamo_id: int, active: bool) -> None:
        current = self.get(reclamo_id)
        self._store[reclamo_id] = current.model_copy(update={'active': active})


class FakeReclamoSosRepository(_InMemoryRepository[ReclamoSos]):
    """In-memory implementation of ReclamoSosRepositoryPort."""

    def get_by_reclamo_id(self, reclamo_id: int) -> ReclamoSos | None:
        for sos in self._store.values():
            if sos.reclamo_id == reclamo_id:
                return sos
        return None

    def get_by_nro_gestion(self, nro_gestion: int) -> ReclamoSos | None:
        for sos in self._store.values():
            if sos.nro_gestion == nro_gestion:
                return sos
        return None

    def save(self, reclamo_sos: ReclamoSos) -> ReclamoSos:
        return self._save(reclamo_sos)

    def update(self, reclamo_sos: ReclamoSos) -> ReclamoSos:
        if reclamo_sos.id is None or reclamo_sos.id not in self._store:
            raise EntityNotFoundError(f'reclamo sos {reclamo_sos.id} not found')
        self._store[reclamo_sos.id] = reclamo_sos
        return reclamo_sos


class FakeTresArrReclamoRepository(_InMemoryRepository[TresArrReclamo]):
    """In-memory implementation of TresArrReclamoRepositoryPort."""

    def get_by_reclamo_id(self, reclamo_id: int) -> TresArrReclamo | None:
        for tres_arr in self._store.values():
            if tres_arr.reclamo_id == reclamo_id:
                return tres_arr
        return None

    def save(self, tres_arr: TresArrReclamo) -> TresArrReclamo:
        return self._save(tres_arr)

    def update(self, tres_arr: TresArrReclamo) -> TresArrReclamo:
        if tres_arr.id is None or tres_arr.id not in self._store:
            raise EntityNotFoundError(f'tres arr {tres_arr.id} not found')
        self._store[tres_arr.id] = tres_arr
        return tres_arr


class FakeGrupoRepository(_InMemoryRepository[Grupo]):
    """In-memory implementation of GrupoRepositoryPort."""

    def get_by_nombre(self, grupo: str) -> Grupo | None:
        for existing in self._store.values():
            if existing.grupo == grupo:
                return existing
        return None

    def save(self, grupo: Grupo) -> Grupo:
        if self.get_by_nombre(grupo.grupo) is not None:
            raise DuplicateEntityError(f'grupo {grupo.grupo!r} already exists')
        return self._save(grupo)

    def list(self) -> list[Grupo]:
        return sorted(self._store.values(), key=lambda g: g.grupo)


class FakePagoRepository(_InMemoryRepository[Pago]):
    """In-memory implementation of PagoRepositoryPort."""

    def list(self, reclamo_id: int | None = None) -> list[Pago]:
        pagos = list(self._store.values())
        if reclamo_id is None:
            return pagos
        return [p for p in pagos if p.reclamo_id == reclamo_id]

    def get(self, pago_id: int) -> Pago:
        try:
            return self._store[pago_id]
        except KeyError as exc:
            raise EntityNotFoundError(f'pago {pago_id} not found') from exc

    def save(self, pago: Pago) -> Pago:
        if pago.id is not None and pago.id in self._store:
            self._store[pago.id] = pago
            return pago
        return self._save(pago)

    def delete(self, pago_id: int) -> None:
        if pago_id not in self._store:
            raise EntityNotFoundError(f'pago {pago_id} not found')
        del self._store[pago_id]


class FakePeriodoRepository(_InMemoryRepository[Periodo]):
    """In-memory implementation of PeriodoRepositoryPort."""

    def list(self) -> list[Periodo]:
        return list(self._store.values())

    def get(self, periodo_id: int) -> Periodo:
        try:
            return self._store[periodo_id]
        except KeyError as exc:
            raise EntityNotFoundError(f'periodo {periodo_id} not found') from exc

    def save(self, periodo: Periodo) -> Periodo:
        return self._save(periodo)


class FakeFacturaRepository(_InMemoryRepository[Factura]):
    """In-memory implementation of FacturaRepositoryPort."""

    def list_by_periodo(self, periodo_id: int) -> list[Factura]:
        return [f for f in self._store.values() if f.periodo_id == periodo_id]

    def save(self, factura: Factura) -> Factura:
        return self._save(factura)


class FakeCreditNoteRepository(_InMemoryRepository[CreditNote]):
    """In-memory implementation of CreditNoteRepositoryPort."""

    def list_by_periodo(self, periodo_id: int) -> list[CreditNote]:
        return [c for c in self._store.values() if c.periodo_id == periodo_id]

    def get(self, credit_note_id: int) -> CreditNote:
        try:
            return self._store[credit_note_id]
        except KeyError as exc:
            raise EntityNotFoundError(
                f'credit note {credit_note_id} not found'
            ) from exc

    def save(self, credit_note: CreditNote) -> CreditNote:
        return self._save(credit_note)

    def update(self, credit_note: CreditNote) -> CreditNote:
        if credit_note.id is None or credit_note.id not in self._store:
            raise EntityNotFoundError(f'credit note {credit_note.id} not found')
        self._store[credit_note.id] = credit_note
        return credit_note

    def delete(self, credit_note_id: int) -> None:
        if credit_note_id not in self._store:
            raise EntityNotFoundError(f'credit note {credit_note_id} not found')
        del self._store[credit_note_id]


class FakeUserRepository(_InMemoryRepository[User]):
    """In-memory implementation of UserRepositoryPort."""

    def get_by_username(self, username: str) -> User | None:
        for user in self._store.values():
            if user.username == username:
                return user
        return None

    def get(self, user_id: int) -> User:
        try:
            return self._store[user_id]
        except KeyError as exc:
            raise EntityNotFoundError(f'user {user_id} not found') from exc

    def save(self, user: User) -> User:
        if self.get_by_username(user.username) is not None:
            raise DuplicateEntityError(f'username {user.username!r} already exists')
        return self._save(user)


class FakeDocumentoRepository:
    """In-memory implementation of DocumentoRepositoryPort (hash-keyed).

    ``Documento`` has no ``id`` field, so it cannot reuse
    ``_InMemoryRepository`` (which keys entities by id); storage is a plain
    dict keyed by ``document_hash``.
    """

    def __init__(self) -> None:
        self._store: dict[str, Documento] = {}

    def get_by_hash(self, document_hash: str) -> Documento | None:
        return self._store.get(document_hash)

    def save(self, documento: Documento) -> Documento:
        if documento.document_hash in self._store:
            raise DuplicateEntityError(
                f'document with hash {documento.document_hash!r} already exists'
            )
        self._store[documento.document_hash] = documento
        return documento

    def list(self) -> list[Documento]:
        return list(self._store.values())


class FakeEntidadDocumentoRepository:
    """In-memory implementation of EntidadDocumentoRepositoryPort.

    ``EntidadDocumento`` has no ``id`` field, so storage is a plain dict
    keyed by ``(document_hash, tipo_entidad, entidad_id)``.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str, int], EntidadDocumento] = {}

    def save(self, entidad: EntidadDocumento) -> EntidadDocumento:
        key = self._key(entidad)
        if key in self._store:
            raise DuplicateEntityError(f'link {key!r} already exists')
        self._store[key] = entidad
        return entidad

    def list(self) -> list[EntidadDocumento]:
        return list(self._store.values())

    @staticmethod
    def _key(entidad: EntidadDocumento) -> tuple[str, str, int]:
        tipo = entidad.tipo_entidad.value if entidad.tipo_entidad is not None else ''
        return (entidad.document_hash, tipo, entidad.entidad_id or 0)
