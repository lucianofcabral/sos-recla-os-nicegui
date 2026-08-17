"""Periodos page: billing cycle cards, unassigned NCs, and the new period dialog."""

from __future__ import annotations

from datetime import date
from functools import partial

from nicegui import ui

from src.application.export_excel import exportar_notas_credito_excel
from src.application.format import format_money
from src.application.queries import list_ciclos, list_notas_credito_sin_asignar
from src.application.use_cases.nota_credito import AsignarNotasCreditoAPeriodo
from src.application.use_cases.periodo import PeriodoCerrar, PeriodoReabrir
from src.domain.exceptions import DomainError
from src.domain.models.entities import User
from src.ui.deps import uow_per_request
from src.ui.dialogos import open_nuevo_ciclo
from src.ui.layout import page
from src.ui.widgets import error_label, form_footer, modal

_NC_COLUMNS = [
    {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left'},
    {'name': 'dominio', 'label': 'Dominio', 'field': 'dominio', 'align': 'left'},
    {'name': 'cliente', 'label': 'Cliente', 'field': 'cliente', 'align': 'left'},
    {'name': 'poliza', 'label': 'Póliza', 'field': 'poliza', 'align': 'left'},
    {
        'name': 'nro_gestion',
        'label': 'Nro. Gestión',
        'field': 'nro_gestion',
        'align': 'left',
    },
    {'name': 'importe', 'label': 'Importe', 'field': 'importe', 'align': 'right'},
]


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


@page('Periodos', path='/periodos')
def periodos(user: User) -> None:
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

    def _abrir_asignar_dialog(tbl: ui.table, open_periodos: list) -> None:
        selected_rows = tbl.selected
        if not selected_rows or not open_periodos:
            return
        selected_ids = [
            int(row['credit_note_id'])
            for row in selected_rows
            if 'credit_note_id' in row
        ]
        if not selected_ids:
            return

        periodo_options = {
            c.periodo_id: c.nombre_corto or f'Periodo {c.periodo_id}'
            for c in open_periodos
        }
        selected_periodo_id = open_periodos[0].periodo_id

        with modal('Asignar notas de crédito') as dialog:
            cant = len(selected_ids)
            msg = (
                f'Se asignará{"n" if cant > 1 else ""} {cant} '
                f'nota{"s" if cant > 1 else ""} de crédito al periodo seleccionado:'
            )
            ui.label(msg).classes('text-body2')
            periodo_select = (
                ui.select(
                    options=periodo_options,
                    value=selected_periodo_id,
                    label='Periodo abierto',
                )
                .classes('w-full')
                .props('outlined')
            )
            err = error_label()

            def _do_assign() -> None:
                p_id = periodo_select.value
                if p_id is None:
                    err.set_text('Seleccioná un periodo')
                    return
                try:
                    with uow_per_request() as uow:
                        AsignarNotasCreditoAPeriodo(uow)(selected_ids, int(p_id))
                except DomainError as exc:
                    err.set_text(str(exc))
                    return
                dialog.close()
                exito_msg = (
                    f'{cant} nota{"s" if cant > 1 else ""} de crédito '
                    f'asignada{"s" if cant > 1 else ""}'
                )
                ui.notify(exito_msg, type='positive')
                render()

            form_footer(dialog, on_save=_do_assign, save_label='Asignar')
        dialog.open()

    def _descargar_excel(tbl: ui.table) -> None:
        selected_rows = tbl.selected
        if not selected_rows:
            return
        excel_bytes = exportar_notas_credito_excel(selected_rows)
        filename = f'notas_credito_{date.today().strftime("%Y%m%d")}.xlsx'
        ui.download(excel_bytes, filename=filename)
        cant = len(selected_rows)
        ui.notify(
            f'Descargando {cant} nota{"s" if cant > 1 else ""} de crédito en Excel',
            type='info',
        )

    def render() -> None:
        container.clear()
        with uow_per_request() as uow:
            cards = list_ciclos(uow)
            ncs_sin_asignar = list_notas_credito_sin_asignar(uow)
        open_cards = [c for c in cards if not c.cerrado]

        with container:
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Notas de crédito sin asignar').classes('text-h6')
                with ui.row().classes('gap-2'):
                    btn_asignar = ui.button(
                        'Asignar a Periodo',
                        icon='assignment',
                        on_click=lambda: _abrir_asignar_dialog(table, open_cards),
                    ).props('unelevated color=primary')
                    btn_asignar.disable()
                    if not open_cards:
                        btn_asignar.tooltip('No hay periodos abiertos disponibles')

                    btn_excel = ui.button(
                        'Descargar Excel',
                        icon='download',
                        on_click=lambda: _descargar_excel(table),
                    ).props('outlined')
                    btn_excel.disable()

            if ncs_sin_asignar:
                rows = [
                    {
                        'credit_note_id': nc.credit_note_id,
                        'fecha': (
                            nc.fecha_pago.strftime('%d/%m/%Y') if nc.fecha_pago else '-'
                        ),
                        'fecha_pago': (
                            nc.fecha_pago.strftime('%d/%m/%Y') if nc.fecha_pago else ''
                        ),
                        'dominio': nc.dominio or '-',
                        'cliente': nc.cliente or '-',
                        'poliza': nc.poliza or '-',
                        'nro_gestion': (str(nc.nro_gestion) if nc.nro_gestion else '-'),
                        'importe': format_money(nc.monto or 0.0),
                        'monto': nc.monto or 0.0,
                    }
                    for nc in ncs_sin_asignar
                ]

                def _on_selection_change(e=None) -> None:
                    has_selection = bool(table.selected)
                    if has_selection and bool(open_cards):
                        btn_asignar.enable()
                    else:
                        btn_asignar.disable()

                    if has_selection:
                        btn_excel.enable()
                    else:
                        btn_excel.disable()

                table = ui.table(
                    columns=_NC_COLUMNS,
                    rows=rows,
                    row_key='credit_note_id',
                    selection='multiple',
                    on_select=_on_selection_change,
                ).classes('w-full')
                table.on('selection', _on_selection_change)
            else:
                ui.label('No hay notas de crédito sin asignar.').classes('text-caption')
            ui.separator()

        if not cards:
            with container, ui.column().classes('items-center gap-2'):
                ui.label('Todavía no hay periodos. Creá el primero.').classes(
                    'text-subtitle1'
                )
                ui.button(
                    'Nuevo Periodo',
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
                'Nuevo Periodo',
                icon='add_circle_outline',
                on_click=lambda: open_nuevo_ciclo(render),
            )
        render()
