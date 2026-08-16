"""Display label maps for the UI (single source of truth, byte-identical strings)."""

from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoReclamoEnum

TIPO_LABELS: dict[TipoReclamoEnum, str] = {
    TipoReclamoEnum.SOS: 'SOS',
    TipoReclamoEnum.TRESA: '3 Arroyos',
    TipoReclamoEnum.OTROS: 'Gestión',
}

TIPO_ENUM: dict[str, TipoReclamoEnum] = {
    'sos': TipoReclamoEnum.SOS,
    'tresa': TipoReclamoEnum.TRESA,
    'especial': TipoReclamoEnum.OTROS,
}

TIPO_KEY: dict[TipoReclamoEnum, str] = {enum: key for key, enum in TIPO_ENUM.items()}

TIPO_FILTRO_OPTIONS: dict[TipoReclamoEnum | None, str] = {
    None: 'Todos',
    TipoReclamoEnum.SOS: 'SOS',
    TipoReclamoEnum.TRESA: '3 Arroyos',
    TipoReclamoEnum.OTROS: 'Gestión',
}

FORMA_PAGO_LABELS: dict[FormaPagoEnum, str] = {
    FormaPagoEnum.TRANSFERENCIA: 'Transferencia',
    FormaPagoEnum.NOTA_DE_CREDITO: 'Nota de Crédito',
    FormaPagoEnum.NC_POLIZA: 'NC Póliza',
    FormaPagoEnum.EFECTIVO: 'Efectivo',
    FormaPagoEnum.CHEQUE: 'Cheque',
    FormaPagoEnum.CUENTA_CORRIENTE: 'Cuenta Corriente',
}

AGENTE_LABELS: dict[AgenteEnum, str] = {agente: agente.value for agente in AgenteEnum}
