from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    RoleEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)


def normalizar_texto(value: str | None) -> str | None:
    """Uppercase a text field and collapse whitespace (edges and runs)."""
    if value is None:
        return None
    return ' '.join(value.upper().split())


def normalizar_identificador(value: str | None) -> str | None:
    """Uppercase an identifier field and remove all internal whitespace."""
    if value is None:
        return None
    return ''.join(value.upper().split())


class Periodo(BaseModel):
    """
    Representa un periodo de facturación con año y mes.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    anio: int | None = None
    mes: int | None = None
    anio_mes: int | None = None
    nombre_corto: str | None = None
    nombre_largo: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    cerrado: bool = False


class Factura(BaseModel):
    """
    Representa una factura con sus atributos principales.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    periodo_id: int | None = None
    periodo: Periodo | None = None
    nro_factura: str = Field(min_length=3, max_length=20)
    importe: float = 0.0
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None


class Reclamo(BaseModel):
    """
    Representa un reclamo con sus atributos principales.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    tipo_reclamo: TipoReclamoEnum | None = None
    cliente: str | None = None
    poliza: str | None = None
    dominio: str | None = None
    importe_reclamado: float | None = None
    comentario: str | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator('cliente', 'comentario', mode='before')
    @classmethod
    def _normalizar_texto(cls, value: object) -> object:
        return normalizar_texto(value) if isinstance(value, str) else value

    @field_validator('poliza', 'dominio', mode='before')
    @classmethod
    def _normalizar_identificador(cls, value: object) -> object:
        return normalizar_identificador(value) if isinstance(value, str) else value


class ReclamoSos(BaseModel):
    """
    Representa un reclamo de tipo SOS con sus atributos principales.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    reclamo_id: int | None = None
    reclamo: Reclamo | None = None
    nro_gestion: int | None = None
    categoria: str | None = None
    motivo: str | None = None
    usuario_carga: str | None = None
    usuario_respuesta: str | None = None
    status: str | None = None
    itr: int | None = None

    @field_validator(
        'categoria',
        'motivo',
        'usuario_carga',
        'usuario_respuesta',
        'status',
        mode='before',
    )
    @classmethod
    def _normalizar_texto(cls, value: object) -> object:
        return normalizar_texto(value) if isinstance(value, str) else value


class TresArrReclamo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    reclamo_id: int | None = None
    reclamo: Reclamo | None = None
    grupo: str | None = None
    grupo_id: int | None = None

    @field_validator('grupo', mode='before')
    @classmethod
    def _normalizar_texto(cls, value: object) -> object:
        return normalizar_texto(value) if isinstance(value, str) else value


class Grupo(BaseModel):
    """Representa un grupo de reclamos de Tres Arroyos."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    grupo: str = Field(min_length=1, max_length=100)
    fecha_creacion: datetime | None = None
    usuario_creacion: str | None = None

    @field_validator('grupo', mode='before')
    @classmethod
    def _normalizar_texto(cls, value: object) -> object:
        return normalizar_texto(value) if isinstance(value, str) else value


class Pago(BaseModel):
    """
    Representa un pago con sus atributos principales.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    reclamo_id: int | None = None
    reclamo: Reclamo | None = None
    fecha_pago: date | None = None
    forma_pago: FormaPagoEnum | None = None
    pagador: AgenteEnum | None = None
    destinatario: AgenteEnum | None = None
    monto: float | None = None


class CreditNote(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    pago_id: int | None = None
    pago: Pago | None = None
    periodo_id: int | None = None
    periodo: Periodo | None = None
    created_date: datetime = Field(default_factory=datetime.now)


class User(BaseModel):
    """
    Representa un usuario del sistema.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    username: str = Field(min_length=3, max_length=50)
    password_hash: str
    role: RoleEnum | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Documento(BaseModel):
    """
    Representa un documento con sus atributos principales.
    """

    model_config = ConfigDict(frozen=True)

    document_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    tipo: str = Field(min_length=1, max_length=100)
    nombre: str = Field(min_length=1, max_length=255)
    contenido: bytes | None = None
    tamanio: int = Field(0, ge=0)
    mime: str = Field('', max_length=100)
    descripcion: str = Field('', max_length=255)
    creado: datetime = Field(default_factory=datetime.now)


class EntidadDocumento(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    tipo_entidad: TipoEntidadEnum | None = None
    entidad_id: int | None = None
