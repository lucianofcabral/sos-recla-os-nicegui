"""SQLModel tables and row-to-entity conversions for the persistence layer."""

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    RoleEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)
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


def _tipo_reclamo_enum(value: str | None) -> TipoReclamoEnum | None:
    if not value:
        return None
    return TipoReclamoEnum(value)


def _forma_pago_enum(value: str | None) -> FormaPagoEnum | None:
    if not value:
        return None
    return FormaPagoEnum(value)


def _agente_enum(value: str | None) -> AgenteEnum | None:
    if not value:
        return None
    return AgenteEnum(value)


def _role_enum(value: str | None) -> RoleEnum | None:
    if not value:
        return None
    return RoleEnum(value)


def _is_loaded(instance: SQLModel, attr: str) -> bool:
    """Return True when a relationship attribute has already been loaded.

    Checking the instance dict avoids triggering a lazy load during mapping.
    """
    return attr in instance.__dict__


class PeriodoRow(SQLModel, table=True):
    """Table row for a billing period."""

    __tablename__ = 'periodos'

    id: int | None = Field(default=None, primary_key=True)
    anio: int | None = None
    mes: int | None = None
    anio_mes: int | None = None
    nombre_corto: str | None = None
    nombre_largo: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    facturas: list['FacturaRow'] = Relationship(back_populates='periodo')
    credit_notes: list['CreditNoteRow'] = Relationship(back_populates='periodo')

    def to_entity(self) -> Periodo:
        return Periodo(
            id=self.id,
            anio=self.anio,
            mes=self.mes,
            anio_mes=self.anio_mes,
            nombre_corto=self.nombre_corto,
            nombre_largo=self.nombre_largo,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
        )

    @classmethod
    def from_entity(cls, entity: Periodo) -> 'PeriodoRow':
        return cls(
            id=entity.id,
            anio=entity.anio,
            mes=entity.mes,
            anio_mes=entity.anio_mes,
            nombre_corto=entity.nombre_corto,
            nombre_largo=entity.nombre_largo,
            fecha_inicio=entity.fecha_inicio,
            fecha_fin=entity.fecha_fin,
        )


class FacturaRow(SQLModel, table=True):
    """Table row for an invoice."""

    __tablename__ = 'facturas'

    id: int | None = Field(default=None, primary_key=True)
    periodo_id: int | None = Field(default=None, foreign_key='periodos.id')
    nro_factura: str
    importe: float = Field(default=0.0)
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None

    periodo: PeriodoRow | None = Relationship(back_populates='facturas')

    def to_entity(self) -> Factura:
        periodo = (
            self.periodo.to_entity()
            if _is_loaded(self, 'periodo') and self.periodo is not None
            else None
        )
        return Factura(
            id=self.id,
            periodo_id=self.periodo_id,
            periodo=periodo,
            nro_factura=self.nro_factura,
            importe=self.importe,
            fecha_emision=self.fecha_emision,
            fecha_vencimiento=self.fecha_vencimiento,
        )

    @classmethod
    def from_entity(cls, entity: Factura) -> 'FacturaRow':
        return cls(
            id=entity.id,
            periodo_id=entity.periodo_id,
            nro_factura=entity.nro_factura,
            importe=entity.importe,
            fecha_emision=entity.fecha_emision,
            fecha_vencimiento=entity.fecha_vencimiento,
        )


class ReclamoRow(SQLModel, table=True):
    """Table row for a reclamo."""

    __tablename__ = 'reclamos'

    id: int | None = Field(default=None, primary_key=True)
    tipo_reclamo: str = Field(default='')
    cliente: str | None = None
    poliza: str | None = None
    dominio: str | None = None
    importe_reclamado: float = Field(default=0.0)
    comentario: str | None = None
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

    reclamo_sos: Optional['ReclamoSosRow'] = Relationship(back_populates='reclamo')
    tres_arr: Optional['TresArrRow'] = Relationship(back_populates='reclamo')
    pagos: list['PagoRow'] = Relationship(back_populates='reclamo')

    def to_entity(self) -> Reclamo:
        return Reclamo(
            id=self.id,
            tipo_reclamo=_tipo_reclamo_enum(self.tipo_reclamo),
            cliente=self.cliente,
            poliza=self.poliza,
            dominio=self.dominio,
            importe_reclamado=self.importe_reclamado,
            comentario=self.comentario,
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: Reclamo) -> 'ReclamoRow':
        return cls(
            id=entity.id,
            tipo_reclamo=(
                entity.tipo_reclamo.value if entity.tipo_reclamo is not None else ''
            ),
            cliente=entity.cliente,
            poliza=entity.poliza,
            dominio=entity.dominio,
            importe_reclamado=(
                entity.importe_reclamado
                if entity.importe_reclamado is not None
                else 0.0
            ),
            comentario=entity.comentario,
            active=entity.active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class ReclamoSosRow(SQLModel, table=True):
    """Table row for a SOS reclamo record."""

    __tablename__ = 'reclamos_sos'

    id: int | None = Field(default=None, primary_key=True)
    reclamo_id: int | None = Field(default=None, foreign_key='reclamos.id', unique=True)
    nro_gestion: int
    categoria: str | None = None
    motivo: str | None = None
    usuario_carga: str | None = None
    usuario_respuesta: str | None = None
    status: str | None = None
    itr: int | None = None

    reclamo: ReclamoRow | None = Relationship(back_populates='reclamo_sos')

    def to_entity(self) -> ReclamoSos:
        reclamo = (
            self.reclamo.to_entity()
            if _is_loaded(self, 'reclamo') and self.reclamo is not None
            else None
        )
        return ReclamoSos(
            id=self.id,
            reclamo_id=self.reclamo_id,
            reclamo=reclamo,
            nro_gestion=self.nro_gestion,
            categoria=self.categoria,
            motivo=self.motivo,
            usuario_carga=self.usuario_carga,
            usuario_respuesta=self.usuario_respuesta,
            status=self.status,
            itr=self.itr,
        )

    @classmethod
    def from_entity(cls, entity: ReclamoSos) -> 'ReclamoSosRow':
        return cls(
            id=entity.id,
            reclamo_id=entity.reclamo_id,
            nro_gestion=entity.nro_gestion,
            categoria=entity.categoria,
            motivo=entity.motivo,
            usuario_carga=entity.usuario_carga,
            usuario_respuesta=entity.usuario_respuesta,
            status=entity.status,
            itr=entity.itr,
        )


class GrupoRow(SQLModel, table=True):
    """Table row for a Tres Arroyos group."""

    __tablename__ = 'grupos'

    id: int | None = Field(default=None, primary_key=True)
    grupo: str = Field(unique=True)
    fecha_creacion: datetime | None = None
    usuario_creacion: str | None = None

    def to_entity(self) -> Grupo:
        return Grupo(
            id=self.id,
            grupo=self.grupo,
            fecha_creacion=self.fecha_creacion,
            usuario_creacion=self.usuario_creacion,
        )

    @classmethod
    def from_entity(cls, entity: Grupo) -> 'GrupoRow':
        return cls(
            id=entity.id,
            grupo=entity.grupo,
            fecha_creacion=entity.fecha_creacion,
            usuario_creacion=entity.usuario_creacion,
        )


class TresArrRow(SQLModel, table=True):
    """Table row for a Tres Arroyos reclamo record."""

    __tablename__ = 'tres_arr'

    id: int | None = Field(default=None, primary_key=True)
    reclamo_id: int | None = Field(default=None, foreign_key='reclamos.id', unique=True)
    grupo: str | None = None
    grupo_id: int | None = Field(default=None, foreign_key='grupos.id')

    reclamo: ReclamoRow | None = Relationship(back_populates='tres_arr')

    def to_entity(self) -> TresArrReclamo:
        reclamo = (
            self.reclamo.to_entity()
            if _is_loaded(self, 'reclamo') and self.reclamo is not None
            else None
        )
        return TresArrReclamo(
            id=self.id,
            reclamo_id=self.reclamo_id,
            reclamo=reclamo,
            grupo=self.grupo,
            grupo_id=self.grupo_id,
        )

    @classmethod
    def from_entity(cls, entity: TresArrReclamo) -> 'TresArrRow':
        return cls(
            id=entity.id,
            reclamo_id=entity.reclamo_id,
            grupo=entity.grupo,
            grupo_id=entity.grupo_id,
        )


class PagoRow(SQLModel, table=True):
    """Table row for a payment linked to a reclamo."""

    __tablename__ = 'pagos'

    id: int | None = Field(default=None, primary_key=True)
    reclamo_id: int | None = Field(default=None, foreign_key='reclamos.id')
    fecha_pago: date | None = None
    forma_pago: str = Field(default='')
    pagador: str = Field(default='')
    destinatario: str = Field(default='')
    monto: float = Field(default=0.0)

    reclamo: ReclamoRow | None = Relationship(back_populates='pagos')
    credit_note: Optional['CreditNoteRow'] = Relationship(back_populates='pago')

    def to_entity(self) -> Pago:
        reclamo = (
            self.reclamo.to_entity()
            if _is_loaded(self, 'reclamo') and self.reclamo is not None
            else None
        )
        return Pago(
            id=self.id,
            reclamo_id=self.reclamo_id,
            reclamo=reclamo,
            fecha_pago=self.fecha_pago,
            forma_pago=_forma_pago_enum(self.forma_pago),
            pagador=_agente_enum(self.pagador),
            destinatario=_agente_enum(self.destinatario),
            monto=self.monto,
        )

    @classmethod
    def from_entity(cls, entity: Pago) -> 'PagoRow':
        return cls(
            id=entity.id,
            reclamo_id=entity.reclamo_id,
            fecha_pago=entity.fecha_pago,
            forma_pago=(
                entity.forma_pago.value if entity.forma_pago is not None else ''
            ),
            pagador=entity.pagador.value if entity.pagador is not None else '',
            destinatario=(
                entity.destinatario.value if entity.destinatario is not None else ''
            ),
            monto=entity.monto,
        )


class CreditNoteRow(SQLModel, table=True):
    """Table row for a credit note."""

    __tablename__ = 'credit_notes'

    id: int | None = Field(default=None, primary_key=True)
    pago_id: int | None = Field(default=None, foreign_key='pagos.id', unique=True)
    periodo_id: int | None = Field(default=None, foreign_key='periodos.id')
    created_date: datetime = Field(default_factory=datetime.now)

    pago: PagoRow | None = Relationship(back_populates='credit_note')
    periodo: PeriodoRow | None = Relationship(back_populates='credit_notes')

    def to_entity(self) -> CreditNote:
        pago = (
            self.pago.to_entity()
            if _is_loaded(self, 'pago') and self.pago is not None
            else None
        )
        periodo = (
            self.periodo.to_entity()
            if _is_loaded(self, 'periodo') and self.periodo is not None
            else None
        )
        return CreditNote(
            id=self.id,
            pago_id=self.pago_id,
            pago=pago,
            periodo_id=self.periodo_id,
            periodo=periodo,
            created_date=self.created_date,
        )

    @classmethod
    def from_entity(cls, entity: CreditNote) -> 'CreditNoteRow':
        return cls(
            id=entity.id,
            pago_id=entity.pago_id,
            periodo_id=entity.periodo_id,
            created_date=entity.created_date,
        )


class UserRow(SQLModel, table=True):
    """Table row for a user."""

    __tablename__ = 'users'

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str | None = None
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

    def to_entity(self) -> User:
        return User(
            id=self.id,
            username=self.username,
            password_hash=self.password_hash,
            role=_role_enum(self.role),
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: User) -> 'UserRow':
        return cls(
            id=entity.id,
            username=entity.username,
            password_hash=entity.password_hash,
            role=entity.role.value if entity.role is not None else None,
            active=entity.active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class DocumentoRow(SQLModel, table=True):
    """Table row for a stored document."""

    __tablename__ = 'documentos'

    id: int | None = Field(default=None, primary_key=True)
    document_hash: str = Field(index=True, unique=True)
    tipo: str
    nombre: str
    contenido: bytes | None = None
    tamanio: int = Field(default=0)
    mime: str = Field(default='')
    descripcion: str = Field(default='')
    creado: datetime = Field(default_factory=datetime.now)

    def to_entity(self) -> Documento:
        return Documento(
            document_hash=self.document_hash,
            tipo=self.tipo,
            nombre=self.nombre,
            contenido=self.contenido,
            tamanio=self.tamanio,
            mime=self.mime,
            descripcion=self.descripcion,
            creado=self.creado,
        )

    @classmethod
    def from_entity(cls, entity: Documento) -> 'DocumentoRow':
        return cls(
            document_hash=entity.document_hash,
            tipo=entity.tipo,
            nombre=entity.nombre,
            contenido=entity.contenido,
            tamanio=entity.tamanio,
            mime=entity.mime,
            descripcion=entity.descripcion,
            creado=entity.creado,
        )


class EntidadDocumentoRow(SQLModel, table=True):
    """Table row linking a document to a domain entity."""

    __tablename__ = 'entidad_documento'
    __table_args__ = (UniqueConstraint('document_hash', 'tipo_entidad', 'entidad_id'),)

    id: int | None = Field(default=None, primary_key=True)
    document_hash: str = Field(index=True)
    tipo_entidad: str = Field(default='')
    entidad_id: int = Field(default=0)

    def to_entity(self) -> EntidadDocumento:
        return EntidadDocumento(
            document_hash=self.document_hash,
            tipo_entidad=(
                TipoEntidadEnum(self.tipo_entidad) if self.tipo_entidad else None
            ),
            entidad_id=self.entidad_id,
        )

    @classmethod
    def from_entity(cls, entity: EntidadDocumento) -> 'EntidadDocumentoRow':
        return cls(
            document_hash=entity.document_hash,
            tipo_entidad=(
                entity.tipo_entidad.value if entity.tipo_entidad is not None else ''
            ),
            entidad_id=entity.entidad_id if entity.entidad_id is not None else 0,
        )
