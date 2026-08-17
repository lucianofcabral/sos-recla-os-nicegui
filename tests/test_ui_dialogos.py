"""Headless tests for the pure helpers in src/ui/dialogos.py."""

from __future__ import annotations

from datetime import date

from src.domain.domain_enums import AgenteEnum, FormaPagoEnum
from src.domain.dto.edit import PagoEdit
from src.ui import dialogos


def test_pago_edit_payload_normal() -> None:
    """Normal pagos carry every editable field in the PagoEdit payload."""
    edit = dialogos._pago_edit_payload(
        pago_id=7,
        es_nc=False,
        monto=1250.5,
        fecha_pago='2024-03-01',
        forma_pago=FormaPagoEnum.TRANSFERENCIA,
        pagador=AgenteEnum.SM,
        destinatario=AgenteEnum.PRESTADOR,
    )
    assert isinstance(edit, PagoEdit)
    assert edit.model_dump(exclude_unset=True) == {
        'id': 7,
        'monto': 1250.5,
        'fecha_pago': date(2024, 3, 1),
        'forma_pago': FormaPagoEnum.TRANSFERENCIA,
        'pagador': AgenteEnum.SM,
        'destinatario': AgenteEnum.PRESTADOR,
    }


def test_pago_edit_payload_nc_only_editable_fields() -> None:
    """Nota de crédito pagos only send id/monto/fecha_pago (actors stay fixed)."""
    edit = dialogos._pago_edit_payload(
        pago_id=7,
        es_nc=True,
        monto=900.0,
        fecha_pago=date(2024, 3, 1),
        forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
        pagador=AgenteEnum.SOS,
        destinatario=AgenteEnum.SM,
    )
    assert edit.model_dump(exclude_unset=True) == {
        'id': 7,
        'monto': 900.0,
        'fecha_pago': date(2024, 3, 1),
    }


def test_pago_edit_payload_accepts_date_object() -> None:
    """The payload builder normalizes both ISO strings and date objects."""
    edit = dialogos._pago_edit_payload(
        pago_id=1,
        es_nc=True,
        monto=100.0,
        fecha_pago=date(2024, 5, 2),
    )
    assert edit.fecha_pago == date(2024, 5, 2)
