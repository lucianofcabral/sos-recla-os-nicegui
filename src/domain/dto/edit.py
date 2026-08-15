from datetime import date

from pydantic import BaseModel, Field

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    RoleEnum,
    TipoEntidadEnum,
)


class PeriodoEdit(BaseModel):
    anio: int
    mes: int
    anio_mes: int | None = None
    nombre_corto: str | None = None
    nombre_largo: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class FacturaEdit(BaseModel):
    id: int | None = None
    nro_factura: str | None = Field(None, min_length=3, max_length=20)
    importe: float | None = None
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None


class ReclamoEdit(BaseModel):
    id: int
    cliente: str | None = None
    poliza: str | None = None
    dominio: str | None = None
    importe_reclamado: float | None = None
    comentario: str | None = None


class ReclamoSosEdit(BaseModel):
    id: int
    nro_gestion: int | None = None
    categoria: str | None = None
    motivo: str | None = None
    usuario_carga: str | None = None
    usuario_respuesta: str | None = None
    status: str | None = None
    itr: int | None = None
    cliente: str | None = None
    poliza: str | None = None
    dominio: str | None = None
    importe_reclamado: float | None = None
    comentario: str | None = None


class TresArrReclamoEdit(BaseModel):
    id: int
    grupo: str | None = None
    grupo_id: int | None = None
    cliente: str | None = None
    poliza: str | None = None
    dominio: str | None = None
    importe_reclamado: float | None = None
    comentario: str | None = None


class OtrosReclamoEdit(BaseModel):
    id: int
    cliente: str | None = None
    poliza: str | None = None
    dominio: str | None = None
    importe_reclamado: float | None = None
    comentario: str | None = None


class PagoEdit(BaseModel):
    id: int
    fecha_pago: date | None = None
    forma_pago: FormaPagoEnum | None = None
    pagador: AgenteEnum | None = None
    destinatario: AgenteEnum | None = None
    monto: float | None = None


class UserEdit(BaseModel):
    id: int
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password_hash: str | None = None
    role: RoleEnum | None = None


class DocumentoEdit(BaseModel):
    document_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    tipo: str | None = Field(None, min_length=1, max_length=100)
    nombre: str | None = Field(None, min_length=1, max_length=255)
    contenido: bytes | None = None
    tamanio: int | None = Field(None, ge=0)
    mime: str | None = Field(None, max_length=100)
    descripcion: str | None = Field(None, max_length=255)


class EntidadDocumento(BaseModel):
    document_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    tipo_entidad: TipoEntidadEnum | None = None
    entidad_id: int | None = None
