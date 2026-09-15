"""Headless tests for the pure helpers in src/ui/dialogos.py."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from nicegui.client import Client
from nicegui.testing.user_simulation import user_simulation

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


def test_upsert_gestion_agrega_al_final_cuando_no_hay_seleccion() -> None:
    """Without a selected index the pending gestión is appended."""
    gestiones: list[dict[str, Any]] = []
    idx = dialogos._upsert_gestion(gestiones, None, {'cliente': 'A'})
    assert idx == 0
    assert gestiones == [{'cliente': 'A'}]


def test_upsert_gestion_actualiza_en_sitio_sin_duplicar() -> None:
    """Selecting a pending gestión updates that row, never adds a new one."""
    gestiones: list[dict[str, Any]] = [{'cliente': 'A'}, {'cliente': 'B'}]
    idx = dialogos._upsert_gestion(gestiones, 1, {'cliente': 'B2'})
    assert idx == 1
    assert len(gestiones) == 2
    assert gestiones[0] == {'cliente': 'A'}
    assert gestiones[1] == {'cliente': 'B2'}


def test_contar_documentos_distintos_dedupea_por_hash() -> None:
    """Two files with the same bytes count as one distinct document."""
    archivos = [
        {'nombre': 'a.pdf', 'contenido': b'igual'},
        {'nombre': 'a-copia.pdf', 'contenido': b'igual'},
        {'nombre': 'b.pdf', 'contenido': b'distinto'},
    ]
    assert dialogos._contar_documentos_distintos(archivos) == 2


def test_contar_documentos_distintos_vacio() -> None:
    assert dialogos._contar_documentos_distintos([]) == 0


def test_lote_dialogo_expone_cargas_separadas() -> None:
    """The lote dialog has a group-level upload and a per-gestión upload."""

    def root() -> None:
        dialogos.open_nuevo_lote_tres_arr(lambda: None)

    async def _correr() -> None:
        async with user_simulation(root=root) as user:
            await user.open('/')
            await user.should_see('Documentos del grupo')
            await user.should_see('Documentos de la gestión')

    asyncio.run(_correr())
    Client.instances.clear()
