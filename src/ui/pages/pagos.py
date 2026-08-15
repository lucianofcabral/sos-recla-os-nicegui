"""Pagos page: listing of payments with the new/delete payment dialogs."""

from __future__ import annotations

from typing import Any, cast

from nicegui import events, ui

from src.application.format import format_date, format_money
from src.application.queries import list_pagos_con_detalle
from src.application.use_cases.nota_credito import NotaCreditoBorrar
from src.application.use_cases.pago import PagoBorrar
from src.domain.domain_enums import FormaPagoEnum
from src.domain.dto.read import PagoListItem
from src.domain.exceptions import DomainError
from src.domain.models.entities import User
from src.ui.deps import uow_per_request
from src.ui.dialogos import FORMA_PAGO_LABELS, open_nuevo_pago
from src.ui.layout import page

COLUMNS: list[dict] = [
    {'name': 'fecha_pago', 'label': 'Fecha Ingresado', 'field': 'fecha_pago'},
    {'name': 'pagador', 'label': 'Pagador', 'field': 'pagador'},
    {'name': 'destinatario', 'label': 'Destinatario', 'field': 'destinatario'},
    {'name': 'forma_pago', 'label': 'Forma de Pago', 'field': 'forma_pago'},
    {'name': 'dominio', 'label': 'Dominio', 'field': 'dominio'},
    {'name': 'poliza', 'label': 'Póliza', 'field': 'poliza'},
    {'name': 'cliente', 'label': 'Cliente', 'field': 'cliente'},
    {'name': 'nro_gestion', 'label': 'Nro. Gestión SOS', 'field': 'nro_gestion'},
    {'name': 'monto', 'label': 'Importe', 'field': 'monto', 'align': 'right'},
    {
        'name': 'eliminar',
        'label': 'Eliminar',
        'field': 'eliminar',
        'align': 'center',
    },
]


def _row(item: PagoListItem, credit_note_by_pago: dict[int, int]) -> dict:
    row = {
        'pago_id': item.pago_id,
        'fecha_pago': format_date(item.fecha_pago),
        'pagador': item.pagador.value if item.pagador is not None else '',
        'destinatario': item.destinatario.value
        if item.destinatario is not None
        else '',
        'forma_pago': (
            FORMA_PAGO_LABELS.get(item.forma_pago, '')
            if item.forma_pago is not None
            else ''
        ),
        'dominio': item.dominio or '',
        'poliza': item.poliza or '',
        'cliente': item.cliente or '',
        'nro_gestion': str(item.nro_gestion) if item.nro_gestion is not None else '',
        'monto': format_money(item.monto),
        'credit_note_id': None,
    }
    if item.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO:
        row['credit_note_id'] = credit_note_by_pago.get(item.pago_id)
    return row


def _credit_notes_by_pago_id(uow) -> dict[int, int]:
    """Map pago_id -> credit_note_id for nota de crédito pagos."""
    notes: list = list(uow.credit_notes.list_by_periodo(None))
    for periodo in uow.periodos.list():
        if periodo.id is not None:
            notes.extend(uow.credit_notes.list_by_periodo(periodo.id))
    result: dict[int, int] = {}
    for note in notes:
        if note.pago_id is not None and note.id is not None:
            result[note.pago_id] = note.id
    return result


def _load_rows() -> list[dict]:
    with uow_per_request() as uow:
        items = list_pagos_con_detalle(uow)
        credit_note_by_pago = _credit_notes_by_pago_id(uow)
    return [_row(item, credit_note_by_pago) for item in items]


@page('Pagos', path='/pagos')
def pagos(user: User) -> None:
    with ui.column().classes('w-full q-px-md q-py-md'):
        with ui.row().classes('gap-2'):
            ui.button(
                'Nuevo Pago',
                icon='add_circle_outline',
                on_click=lambda: open_nuevo_pago(refresh_table),
            )

        table = ui.table(columns=COLUMNS, rows=_load_rows(), row_key='pago_id')

        def refresh_table() -> None:
            table.update_rows(_load_rows())

        def on_delete(e: events.GenericEventArguments) -> None:
            row = cast(Any, e.args)
            pago_id = int(row['pago_id'])
            credit_note_id = row.get('credit_note_id')
            try:
                with uow_per_request() as uow:
                    if credit_note_id is not None:
                        NotaCreditoBorrar(uow)(int(credit_note_id))
                    else:
                        PagoBorrar(uow)(pago_id)
            except DomainError as exc:
                ui.notify(str(exc), type='negative')
                return
            refresh_table()

        with table.add_slot('body-cell-eliminar'), table.cell('eliminar'):
            ui.button(icon='delete').props('flat dense color=negative').on(
                'click',
                js_handler='() => emit(props.row)',
                handler=on_delete,
            )
