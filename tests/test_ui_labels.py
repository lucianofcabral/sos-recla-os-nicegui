"""Label map parity tests (backs R1: single source of truth, byte-identical strings)."""

from __future__ import annotations

from types import MappingProxyType

from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoReclamoEnum
from src.ui import labels


def test_ui_labels_parity() -> None:
    """Every label map in labels.py matches the pre-refactor values byte-for-byte."""
    assert MappingProxyType(labels.TIPO_LABELS) == MappingProxyType(
        {
            TipoReclamoEnum.SOS: 'SOS',
            TipoReclamoEnum.TRESA: '3 Arroyos',
            TipoReclamoEnum.OTROS: 'Gestión',
        }
    )
    assert MappingProxyType(labels.TIPO_ENUM) == MappingProxyType(
        {
            'sos': TipoReclamoEnum.SOS,
            'tresa': TipoReclamoEnum.TRESA,
            'especial': TipoReclamoEnum.OTROS,
        }
    )
    assert MappingProxyType(labels.TIPO_KEY) == MappingProxyType(
        {
            TipoReclamoEnum.SOS: 'sos',
            TipoReclamoEnum.TRESA: 'tresa',
            TipoReclamoEnum.OTROS: 'especial',
        }
    )
    assert MappingProxyType(labels.TIPO_FILTRO_OPTIONS) == MappingProxyType(
        {
            None: 'Todos',
            TipoReclamoEnum.SOS: 'SOS',
            TipoReclamoEnum.TRESA: '3 Arroyos',
            TipoReclamoEnum.OTROS: 'Gestión',
        }
    )
    assert MappingProxyType(labels.FORMA_PAGO_LABELS) == MappingProxyType(
        {
            FormaPagoEnum.TRANSFERENCIA: 'Transferencia',
            FormaPagoEnum.NOTA_DE_CREDITO: 'Nota de Crédito',
            FormaPagoEnum.NC_POLIZA: 'NC Póliza',
            FormaPagoEnum.EFECTIVO: 'Efectivo',
            FormaPagoEnum.CHEQUE: 'Cheque',
            FormaPagoEnum.CUENTA_CORRIENTE: 'Cuenta Corriente',
        }
    )
    assert MappingProxyType(labels.AGENTE_LABELS) == MappingProxyType(
        {
            AgenteEnum.SOS: 'SOS',
            AgenteEnum.SM: 'SM',
            AgenteEnum.ASEGURADO: 'Asegurado',
            AgenteEnum.PRESTADOR: 'Prestador',
            AgenteEnum.PRODUCTOR: 'Productor',
        }
    )
