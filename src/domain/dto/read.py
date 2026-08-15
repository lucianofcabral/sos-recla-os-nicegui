"""Read models for the UI lists (denormalized projections)."""

from datetime import date, datetime

from pydantic import BaseModel

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoReclamoEnum,
)


class ReclamoHomeItem(BaseModel):
    """Row for the home reclamos listing."""

    reclamo_id: int
    tipo_reclamo: TipoReclamoEnum | None = None
    cliente: str | None = None
    poliza: str = ''
    dominio: str = ''
    importe_reclamado: float = 0.0
    active: bool = True
    created_at: datetime | None = None
    nro_gestion: int | None = None
    has_pagos: bool = False
    has_credit_note: bool = False


class ReclamoHomeFilter(BaseModel):
    """Optional filter criteria for the home reclamos listing."""

    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    importe_min: float | None = None
    importe_max: float | None = None
    con_pagos: bool | None = None
    con_nota_credito: bool | None = None
    active: bool | None = None
    tipo_reclamo: TipoReclamoEnum | None = None
    grupo: str | None = None
    texto: str | None = None

    def matches(self, item: ReclamoHomeItem, grupo: str | None = None) -> bool:
        """Return True when the item satisfies every set criterion."""
        if self.fecha_desde is not None or self.fecha_hasta is not None:
            if item.created_at is None:
                return False
            fecha = item.created_at.date()
            if self.fecha_desde is not None and fecha < self.fecha_desde:
                return False
            if self.fecha_hasta is not None and fecha > self.fecha_hasta:
                return False
        if self.importe_min is not None and item.importe_reclamado < self.importe_min:
            return False
        if self.importe_max is not None and item.importe_reclamado > self.importe_max:
            return False
        if self.con_pagos is not None and item.has_pagos != self.con_pagos:
            return False
        if (
            self.con_nota_credito is not None
            and item.has_credit_note != self.con_nota_credito
        ):
            return False
        if self.active is not None and item.active != self.active:
            return False
        if self.tipo_reclamo is not None and item.tipo_reclamo != self.tipo_reclamo:
            return False
        if self.grupo is not None and grupo != self.grupo:
            return False
        if self.texto:
            haystack = ' '.join(
                text
                for text in (
                    item.dominio or '',
                    item.poliza or '',
                    str(item.nro_gestion or ''),
                )
                if text
            ).lower()
            if self.texto.lower() not in haystack:
                return False
        return True


class PagoListItem(BaseModel):
    """Row for the pagos listing with embedded reclamo details."""

    pago_id: int
    fecha_pago: date | None = None
    forma_pago: FormaPagoEnum | None = None
    pagador: AgenteEnum | None = None
    destinatario: AgenteEnum | None = None
    monto: float | None = None
    dominio: str | None = None
    poliza: str | None = None
    cliente: str | None = None
    nro_gestion: int | None = None


class CicloCard(BaseModel):
    """Summary card for a billing cycle."""

    periodo_id: int
    nombre_corto: str | None = None
    anio_mes: int | None = None
    cant_documentos: int = 0
    suma_importe_facturas: float = 0.0
    cant_notas_credito: int = 0
    suma_importe_notas_credito: float = 0.0


class LoteTresArrResult(BaseModel):
    """Report of a created Tres Arroyos lot, for the UI summary."""

    grupo_id: int
    grupo: str
    gestiones_creadas: int
    pagos_creados: int
    documentos_adjuntados: int
    gestiones_sin_pago: int
