from datetime import date

from pydantic import BaseModel, Field

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    RoleEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)


class PeriodoCreate(BaseModel):
    anio: int
    mes: int
    nombre_corto: str | None = None
    nombre_largo: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class FacturaCreate(BaseModel):
    periodo_id: int | None = None
    nro_factura: str = Field(min_length=3, max_length=20)
    importe: float = 0.0
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None


class ReclamoCreate(BaseModel):
    tipo_reclamo: TipoReclamoEnum | None = None
    cliente: str | None = None
    poliza: str
    dominio: str
    importe_reclamado: float = 0.0
    comentario: str | None = None


class ReclamoSosCreate(BaseModel):
    reclamo: ReclamoCreate
    nro_gestion: int
    categoria: str | None = None
    motivo: str | None = None
    usuario_carga: str | None = None
    usuario_respuesta: str | None = None
    status: str | None = None
    itr: int | None = None


class TresArrReclamoCreate(BaseModel):
    reclamo: ReclamoCreate
    grupo: str | None = None
    grupo_id: int | None = None


class OtrosReclamoCreate(BaseModel):
    reclamo: ReclamoCreate


class PagoReclamoCreate(BaseModel):
    """Pago fields for dialogs that create the reclamo first (no reclamo_id)."""

    fecha_pago: date = Field(default_factory=date.today)
    forma_pago: FormaPagoEnum
    pagador: AgenteEnum
    destinatario: AgenteEnum
    monto: float


class PagoCreate(BaseModel):
    reclamo_id: int
    fecha_pago: date = Field(default_factory=date.today)
    forma_pago: FormaPagoEnum
    pagador: AgenteEnum
    destinatario: AgenteEnum
    monto: float


class CreditNoteCreate(BaseModel):
    reclamo_id: int
    monto: float
    fecha_pago: date = Field(default_factory=date.today)
    periodo_id: int | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: RoleEnum | None = None


class DocumentoCreate(BaseModel):
    document_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    tipo: str = Field(min_length=1, max_length=100)
    nombre: str = Field(min_length=1, max_length=255)
    contenido: bytes | None = None
    tamanio: int = Field(0, ge=0)
    mime: str = Field('', max_length=100)
    descripcion: str = Field('', max_length=255)


class EntidadDocumento(BaseModel):
    document_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    tipo_entidad: TipoEntidadEnum
    entidad_id: int


class GestionLoteItem(BaseModel):
    reclamo: ReclamoCreate
    documentos: list[DocumentoCreate] = []


class LoteTresArrCreate(BaseModel):
    grupo: str = Field(min_length=1, max_length=100)
    usuario_creacion: str | None = None
    gestiones: list[GestionLoteItem] = []
    generar_pagos: bool = True
