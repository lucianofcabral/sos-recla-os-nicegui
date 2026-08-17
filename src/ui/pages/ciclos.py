"""Ciclos page: billing cycle cards and the new cycle dialog."""

from __future__ import annotations

from functools import partial

from nicegui import ui

from src.application.format import format_money
from src.application.queries import list_ciclos
from src.application.use_cases.periodo import PeriodoCerrar, PeriodoReabrir
from src.domain.exceptions import DomainError
from src.domain.models.entities import User
from src.ui.deps import uow_per_request
from src.ui.dialogos import open_nuevo_ciclo
from src.ui.layout import page
from src.ui.widgets import form_footer, modal


def _render_card(ciclo, on_cerrar, on_reabrir) -> None:
    with ui.card().classes('w-72'), ui.column().classes('gap-1 w-full'):
        with ui.row().classes('justify-between w-full items-center'):
            ui.label(ciclo.nombre_corto or '').classes('text-h6')
            if ciclo.cerrado:
                ui.badge('Cerrado').props('color=grey')
        with ui.row().classes('justify-between w-full'):
            ui.label('Cant. Documentos').classes('text-caption')
            ui.label(str(ciclo.cant_documentos)).classes('text-body-2')
        with ui.row().classes('justify-between w-full'):
            ui.label('Suma Importe Facturas').classes('text-caption')
            ui.label(format_money(ciclo.suma_importe_facturas)).classes('text-body-2')
        with ui.row().classes('justify-between w-full'):
            ui.label('Cant. Notas de Crédito').classes('text-caption')
            ui.label(str(ciclo.cant_notas_credito)).classes('text-body-2')
        with ui.row().classes('justify-between w-full'):
            ui.label('Suma Importe Notas de Crédito').classes('text-caption')
            ui.label(format_money(ciclo.suma_importe_notas_credito)).classes(
                'text-body-2'
            )
        if ciclo.cerrado:
            ui.button('Reabrir', icon='lock_open', on_click=on_reabrir).props(
                'flat dense'
            )
        else:
            ui.button('Cerrar', icon='lock', on_click=on_cerrar).props('flat dense')


@page('Ciclos', path='/ciclos')
def ciclos(user: User) -> None:
    container = ui.column().classes('w-full gap-4')

    def _cerrar(periodo_id: int, dialog: ui.dialog | None = None) -> None:
        if dialog is not None:
            dialog.close()
        try:
            with uow_per_request() as uow:
                PeriodoCerrar(uow)(periodo_id)
        except DomainError as exc:
            ui.notify(str(exc), type='negative')
            return
        ui.notify('Periodo cerrado', type='positive')
        render()

    def _reabrir(periodo_id: int, dialog: ui.dialog | None = None) -> None:
        if dialog is not None:
            dialog.close()
        try:
            with uow_per_request() as uow:
                PeriodoReabrir(uow)(periodo_id)
        except DomainError as exc:
            ui.notify(str(exc), type='negative')
            return
        ui.notify('Periodo reabierto', type='positive')
        render()

    def _confirm_cerrar(periodo_id: int) -> None:
        with modal('Cerrar periodo') as dialog:
            ui.label(
                '¿Cerrar este periodo? No se podrán borrar ni editar '
                'notas de crédito asociadas.'
            )
            form_footer(
                dialog,
                on_save=lambda: _cerrar(periodo_id, dialog),
                save_label='Cerrar periodo',
            )
        dialog.open()

    def _confirm_reabrir(periodo_id: int) -> None:
        with modal('Reabrir periodo') as dialog:
            ui.label(
                '¿Reabrir este periodo? Las notas de crédito asociadas '
                'volverán a ser editables.'
            )
            form_footer(
                dialog,
                on_save=lambda: _reabrir(periodo_id, dialog),
                save_label='Reabrir',
            )
        dialog.open()

    def render() -> None:
        container.clear()
        with uow_per_request() as uow:
            cards = list_ciclos(uow)
        if not cards:
            with container, ui.column().classes('items-center gap-2'):
                ui.label('Todavía no hay ciclos. Creá el primero.').classes(
                    'text-subtitle1'
                )
                ui.button(
                    'Nuevo Ciclo',
                    icon='add_circle_outline',
                    on_click=lambda: open_nuevo_ciclo(render),
                )
            return
        with container, ui.row().classes('gap-4 items-stretch'):
            for ciclo in cards:
                _render_card(
                    ciclo,
                    on_cerrar=partial(_confirm_cerrar, ciclo.periodo_id),
                    on_reabrir=partial(_confirm_reabrir, ciclo.periodo_id),
                )

    with ui.column().classes('w-full q-px-md q-py-md'):
        with ui.row().classes('gap-2'):
            ui.button(
                'Nuevo Ciclo',
                icon='add_circle_outline',
                on_click=lambda: open_nuevo_ciclo(render),
            )
        render()
