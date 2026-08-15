from enum import StrEnum


class RoleEnum(StrEnum):
    ADMIN = 'ADMIN'
    USER = 'USER'


class TipoReclamoEnum(StrEnum):
    SOS = 'SOS'
    TRESA = 'Tres Arroyos'
    OTROS = 'Otros'


class AgenteEnum(StrEnum):
    SOS = 'SOS'
    SM = 'SM'
    ASEGURADO = 'Asegurado'
    PRESTADOR = 'Prestador'
    PRODUCTOR = 'Productor'


class FormaPagoEnum(StrEnum):
    TRANSFERENCIA = 'Transferencia'
    NOTA_DE_CREDITO = 'Nota de Crédito'
    NC_POLIZA = 'NC Póliza'
    EFECTIVO = 'Efectivo'
    CHEQUE = 'Cheque'
    CUENTA_CORRIENTE = 'Cuenta Corriente'


class TipoEntidadEnum(StrEnum):
    RECLAMO = 'RECLAMO'
    GRUPO = 'GRUPO'
    PAGO = 'PAGO'
    FACTURA = 'FACTURA'
    PERIODO = 'PERIODO'
