"""SQLModel implementations of the repository ports."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from src.adapters.sqlmodel.models import (
    CreditNoteRow,
    DocumentoRow,
    EntidadDocumentoRow,
    FacturaRow,
    GrupoRow,
    PagoRow,
    PeriodoRow,
    ReclamoRow,
    ReclamoSosRow,
    TresArrRow,
    UserRow,
)
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


class SqlModelReclamoRepository:
    """SQLModel-backed implementation of ReclamoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, active_only: bool = True) -> list[Reclamo]:
        statement = select(ReclamoRow).order_by(ReclamoRow.id)
        if active_only:
            statement = statement.where(ReclamoRow.active.is_(True))
        rows = self._session.exec(statement).all()
        return [row.to_entity() for row in rows]

    def get(self, reclamo_id: int) -> Reclamo:
        row = self._session.get(ReclamoRow, reclamo_id)
        if row is None:
            raise EntityNotFoundError(f'reclamo {reclamo_id} not found')
        return row.to_entity()

    def save(self, reclamo: Reclamo) -> Reclamo:
        row = ReclamoRow.from_entity(reclamo)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def update(self, reclamo: Reclamo) -> Reclamo:
        if reclamo.id is None:
            raise EntityNotFoundError('reclamo None not found')
        existing = self._session.get(ReclamoRow, reclamo.id)
        if existing is None:
            raise EntityNotFoundError(f'reclamo {reclamo.id} not found')
        row = self._session.merge(ReclamoRow.from_entity(reclamo))
        self._session.flush()
        return row.to_entity()

    def set_active(self, reclamo_id: int, active: bool) -> None:
        existing = self._session.get(ReclamoRow, reclamo_id)
        if existing is None:
            raise EntityNotFoundError(f'reclamo {reclamo_id} not found')
        existing.active = active
        self._session.flush()


class SqlModelReclamoSosRepository:
    """SQLModel-backed implementation of ReclamoSosRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_reclamo_id(self, reclamo_id: int) -> ReclamoSos | None:
        statement = select(ReclamoSosRow).where(ReclamoSosRow.reclamo_id == reclamo_id)
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def get_by_nro_gestion(self, nro_gestion: int) -> ReclamoSos | None:
        statement = (
            select(ReclamoSosRow)
            .where(ReclamoSosRow.nro_gestion == nro_gestion)
            .options(selectinload(ReclamoSosRow.reclamo))
        )
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def save(self, reclamo_sos: ReclamoSos) -> ReclamoSos:
        row = ReclamoSosRow.from_entity(reclamo_sos)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def update(self, reclamo_sos: ReclamoSos) -> ReclamoSos:
        if reclamo_sos.id is None:
            raise EntityNotFoundError('reclamo sos None not found')
        existing = self._session.get(ReclamoSosRow, reclamo_sos.id)
        if existing is None:
            raise EntityNotFoundError(f'reclamo sos {reclamo_sos.id} not found')
        row = self._session.merge(ReclamoSosRow.from_entity(reclamo_sos))
        self._session.flush()
        return row.to_entity()


class SqlModelTresArrRepository:
    """SQLModel-backed implementation of TresArrReclamoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_reclamo_id(self, reclamo_id: int) -> TresArrReclamo | None:
        statement = select(TresArrRow).where(TresArrRow.reclamo_id == reclamo_id)
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def list_by_grupo_id(self, grupo_id: int) -> list[TresArrReclamo]:
        statement = (
            select(TresArrRow)
            .where(TresArrRow.grupo_id == grupo_id)
            .options(selectinload(TresArrRow.reclamo))
            .order_by(TresArrRow.id)
        )
        rows = self._session.exec(statement).all()
        return [row.to_entity() for row in rows]

    def save(self, tres_arr: TresArrReclamo) -> TresArrReclamo:
        row = TresArrRow.from_entity(tres_arr)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def update(self, tres_arr: TresArrReclamo) -> TresArrReclamo:
        if tres_arr.id is None:
            raise EntityNotFoundError(f'tres arr {tres_arr.id} not found')
        existing = self._session.get(TresArrRow, tres_arr.id)
        if existing is None:
            raise EntityNotFoundError(f'tres arr {tres_arr.id} not found')
        row = self._session.merge(TresArrRow.from_entity(tres_arr))
        self._session.flush()
        return row.to_entity()


class SqlModelGrupoRepository:
    """SQLModel-backed implementation of GrupoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, grupo_id: int) -> Grupo:
        row = self._session.get(GrupoRow, grupo_id)
        if row is None:
            raise EntityNotFoundError(f'grupo {grupo_id} not found')
        return row.to_entity()

    def get_by_nombre(self, grupo: str) -> Grupo | None:
        statement = select(GrupoRow).where(GrupoRow.grupo == grupo)
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def save(self, grupo: Grupo) -> Grupo:
        if self.get_by_nombre(grupo.grupo) is not None:
            raise DuplicateEntityError(f'grupo {grupo.grupo!r} already exists')
        row = GrupoRow.from_entity(grupo)
        try:
            self._session.add(row)
            self._session.flush()
        except IntegrityError as exc:
            raise DuplicateEntityError(f'grupo {grupo.grupo!r} already exists') from exc
        return row.to_entity()

    def update(self, grupo: Grupo) -> Grupo:
        if grupo.id is None:
            raise EntityNotFoundError('grupo None not found')
        existing = self._session.get(GrupoRow, grupo.id)
        if existing is None:
            raise EntityNotFoundError(f'grupo {grupo.id} not found')
        row = self._session.merge(GrupoRow.from_entity(grupo))
        self._session.flush()
        return row.to_entity()

    def list(self) -> list[Grupo]:
        rows = self._session.exec(select(GrupoRow).order_by(GrupoRow.grupo)).all()
        return [row.to_entity() for row in rows]


class SqlModelPagoRepository:
    """SQLModel-backed implementation of PagoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, reclamo_id: int | None = None) -> list[Pago]:
        statement = (
            select(PagoRow).options(selectinload(PagoRow.reclamo)).order_by(PagoRow.id)
        )
        if reclamo_id is not None:
            statement = statement.where(PagoRow.reclamo_id == reclamo_id)
        rows = self._session.exec(statement).all()
        return [row.to_entity() for row in rows]

    def get(self, pago_id: int) -> Pago:
        statement = (
            select(PagoRow)
            .where(PagoRow.id == pago_id)
            .options(selectinload(PagoRow.reclamo))
        )
        row = self._session.exec(statement).first()
        if row is None:
            raise EntityNotFoundError(f'pago {pago_id} not found')
        return row.to_entity()

    def save(self, pago: Pago) -> Pago:
        row = PagoRow.from_entity(pago)
        if pago.id is None:
            self._session.add(row)
        else:
            row = self._session.merge(row)
        self._session.flush()
        return row.to_entity()

    def delete(self, pago_id: int) -> None:
        existing = self._session.get(PagoRow, pago_id)
        if existing is None:
            raise EntityNotFoundError(f'pago {pago_id} not found')
        self._session.delete(existing)
        self._session.flush()


class SqlModelPeriodoRepository:
    """SQLModel-backed implementation of PeriodoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[Periodo]:
        rows = self._session.exec(select(PeriodoRow).order_by(PeriodoRow.id)).all()
        return [row.to_entity() for row in rows]

    def get(self, periodo_id: int) -> Periodo:
        row = self._session.get(PeriodoRow, periodo_id)
        if row is None:
            raise EntityNotFoundError(f'periodo {periodo_id} not found')
        return row.to_entity()

    def save(self, periodo: Periodo) -> Periodo:
        row = PeriodoRow.from_entity(periodo)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def update(self, periodo: Periodo) -> Periodo:
        if periodo.id is None:
            raise EntityNotFoundError('periodo None not found')
        existing = self._session.get(PeriodoRow, periodo.id)
        if existing is None:
            raise EntityNotFoundError(f'periodo {periodo.id} not found')
        row = self._session.merge(PeriodoRow.from_entity(periodo))
        self._session.flush()
        return row.to_entity()


class SqlModelFacturaRepository:
    """SQLModel-backed implementation of FacturaRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_periodo(self, periodo_id: int) -> list[Factura]:
        statement = (
            select(FacturaRow)
            .where(FacturaRow.periodo_id == periodo_id)
            .options(selectinload(FacturaRow.periodo))
            .order_by(FacturaRow.id)
        )
        rows = self._session.exec(statement).all()
        return [row.to_entity() for row in rows]

    def save(self, factura: Factura) -> Factura:
        row = FacturaRow.from_entity(factura)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()


class SqlModelCreditNoteRepository:
    """SQLModel-backed implementation of CreditNoteRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_periodo(self, periodo_id: int) -> list[CreditNote]:
        statement = (
            select(CreditNoteRow)
            .where(CreditNoteRow.periodo_id == periodo_id)
            .options(
                selectinload(CreditNoteRow.pago),
                selectinload(CreditNoteRow.periodo),
            )
            .order_by(CreditNoteRow.id)
        )
        rows = self._session.exec(statement).all()
        return [row.to_entity() for row in rows]

    def get(self, credit_note_id: int) -> CreditNote:
        statement = (
            select(CreditNoteRow)
            .where(CreditNoteRow.id == credit_note_id)
            .options(
                selectinload(CreditNoteRow.pago),
                selectinload(CreditNoteRow.periodo),
            )
        )
        row = self._session.exec(statement).first()
        if row is None:
            raise EntityNotFoundError(f'credit note {credit_note_id} not found')
        return row.to_entity()

    def get_by_pago_id(self, pago_id: int) -> CreditNote | None:
        statement = (
            select(CreditNoteRow)
            .where(CreditNoteRow.pago_id == pago_id)
            .options(
                selectinload(CreditNoteRow.pago),
                selectinload(CreditNoteRow.periodo),
            )
        )
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def save(self, credit_note: CreditNote) -> CreditNote:
        row = CreditNoteRow.from_entity(credit_note)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def update(self, credit_note: CreditNote) -> CreditNote:
        if credit_note.id is None:
            raise EntityNotFoundError('credit note None not found')
        existing = self._session.get(CreditNoteRow, credit_note.id)
        if existing is None:
            raise EntityNotFoundError(f'credit note {credit_note.id} not found')
        row = self._session.merge(CreditNoteRow.from_entity(credit_note))
        self._session.flush()
        return row.to_entity()

    def delete(self, credit_note_id: int) -> None:
        existing = self._session.get(CreditNoteRow, credit_note_id)
        if existing is None:
            raise EntityNotFoundError(f'credit note {credit_note_id} not found')
        self._session.delete(existing)
        self._session.flush()


class SqlModelUserRepository:
    """SQLModel-backed implementation of UserRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_username(self, username: str) -> User | None:
        statement = select(UserRow).where(UserRow.username == username)
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def get(self, user_id: int) -> User:
        row = self._session.get(UserRow, user_id)
        if row is None:
            raise EntityNotFoundError(f'user {user_id} not found')
        return row.to_entity()

    def save(self, user: User) -> User:
        if self.get_by_username(user.username) is not None:
            raise DuplicateEntityError(f'username {user.username!r} already exists')
        row = UserRow.from_entity(user)
        try:
            self._session.add(row)
            self._session.flush()
        except IntegrityError as exc:
            raise DuplicateEntityError(
                f'username {user.username!r} already exists'
            ) from exc
        return row.to_entity()


class SqlModelDocumentoRepository:
    """SQLModel-backed implementation of DocumentoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_hash(self, document_hash: str) -> Documento | None:
        statement = select(DocumentoRow).where(
            DocumentoRow.document_hash == document_hash
        )
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return row.to_entity()

    def save(self, documento: Documento) -> Documento:
        row = DocumentoRow.from_entity(documento)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def list(self) -> list[Documento]:
        rows = self._session.exec(select(DocumentoRow).order_by(DocumentoRow.id)).all()
        return [row.to_entity() for row in rows]

    def list_by_entidad(self, tipo_entidad: str, entidad_id: int) -> list[Documento]:
        stmt = (
            select(DocumentoRow)
            .join(
                EntidadDocumentoRow,
                DocumentoRow.document_hash == EntidadDocumentoRow.document_hash,
            )
            .where(EntidadDocumentoRow.tipo_entidad == tipo_entidad)
            .where(EntidadDocumentoRow.entidad_id == entidad_id)
            .order_by(desc(DocumentoRow.creado))
        )
        rows = self._session.exec(stmt).all()
        return [row.to_entity() for row in rows]

    def delete_by_hash(self, document_hash: str) -> bool:
        row = self._session.exec(
            select(DocumentoRow).where(DocumentoRow.document_hash == document_hash)
        ).first()
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True


class SqlModelEntidadDocumentoRepository:
    """SQLModel-backed implementation of EntidadDocumentoRepositoryPort."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entidad: EntidadDocumento) -> EntidadDocumento:
        row = EntidadDocumentoRow.from_entity(entidad)
        self._session.add(row)
        self._session.flush()
        return row.to_entity()

    def list(self) -> list[EntidadDocumento]:
        rows = self._session.exec(
            select(EntidadDocumentoRow).order_by(EntidadDocumentoRow.id)
        ).all()
        return [row.to_entity() for row in rows]

    def list_by_entidad(
        self, tipo_entidad: str, entidad_id: int
    ) -> list[EntidadDocumento]:
        stmt = (
            select(EntidadDocumentoRow)
            .where(EntidadDocumentoRow.tipo_entidad == tipo_entidad)
            .where(EntidadDocumentoRow.entidad_id == entidad_id)
            .order_by(EntidadDocumentoRow.id)
        )
        rows = self._session.exec(stmt).all()
        return [row.to_entity() for row in rows]

    def delete_by_entidad(
        self, tipo_entidad: str, entidad_id: int, document_hash: str
    ) -> bool:
        row = self._session.exec(
            select(EntidadDocumentoRow)
            .where(EntidadDocumentoRow.tipo_entidad == tipo_entidad)
            .where(EntidadDocumentoRow.entidad_id == entidad_id)
            .where(EntidadDocumentoRow.document_hash == document_hash)
        ).first()
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def count_by_entidad(self, tipo_entidad: str, entidad_id: int) -> int:
        from sqlalchemy import func

        result = self._session.exec(
            select(func.count(EntidadDocumentoRow.id))
            .where(EntidadDocumentoRow.tipo_entidad == tipo_entidad)
            .where(EntidadDocumentoRow.entidad_id == entidad_id)
        ).one()
        return int(result)

    def count_by_hash(self, document_hash: str) -> int:
        from sqlalchemy import func

        result = self._session.exec(
            select(func.count(EntidadDocumentoRow.id)).where(
                EntidadDocumentoRow.document_hash == document_hash
            )
        ).one()
        return int(result)
