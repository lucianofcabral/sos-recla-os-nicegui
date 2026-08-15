"""Ciclos page: billing cycle cards and the new cycle dialog."""

from __future__ import annotations

from nicegui import ui

from src.application.format import format_money
from src.application.queries import list_ciclos
from src.domain.models.entities import User
from src.ui.deps import uow_per_request
from src.ui.dialogos import open_nuevo_ciclo
from src.ui.layout import page


def _render_card(ciclo) -> None:
    with ui.card().classes('w-72'), ui.column().classes('gap-1 w-full'):
        ui.label(ciclo.nombre_corto or '').classes('text-h6')
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


@page('Ciclos', path='/ciclos')
def ciclos(user: User) -> None:
    container = ui.column().classes('w-full gap-4')

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
                _render_card(ciclo)

    with ui.column().classes('w-full q-px-md q-py-md'):
        with ui.row().classes('gap-2'):
            ui.button(
                'Nuevo Ciclo',
                icon='add_circle_outline',
                on_click=lambda: open_nuevo_ciclo(render),
            )
        render()
