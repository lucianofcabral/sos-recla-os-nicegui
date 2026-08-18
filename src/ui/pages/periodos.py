"""Periodos page: billing cycle cards, unassigned NCs, and the new period dialog."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from src.application.export_excel import exportar_notas_credito_excel
from src.application.format import format_money
from src.application.queries import (
    list_ciclos,
    list_notas_credito_por_periodo,
    list_notas_credito_sin_asignar,
)
from src.application.use_cases.nota_credito import (
    AsignarNotasCreditoAPeriodo,
    DesasignarNotaCreditoAPeriodo,
)
from src.application.use_cases.periodo import (
    PeriodoActualizar,
    PeriodoCerrar,
    PeriodoReabrir,
)
from src.domain.dto.edit import PeriodoEdit
from src.domain.exceptions import DomainError
from src.domain.models.entities import User
from src.ui.deps import uow_per_request
from src.ui.dialogos import open_nuevo_ciclo
from src.ui.layout import page
from src.ui.widgets import date_picker, error_label, form_footer, modal

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

CARDS_PER_PAGE = 8


def _render_card(ciclo, on_click) -> None:
    with (
        ui.card()
        .classes('w-72 cursor-pointer hover:shadow-lg transition-shadow')
        .on('click', lambda: on_click(ciclo.periodo_id)),
        ui.column().classes('gap-1 w-full'),
    ):
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

    def _open_editar_periodo(periodo_id: int) -> None:
        with uow_per_request() as uow:
            ciclo = next(
                (c for c in list_ciclos(uow) if c.periodo_id == periodo_id), None
            )
            ncs = list_notas_credito_por_periodo(uow, periodo_id)
            periodo = uow.periodos.get(periodo_id)

        if ciclo is None:
            return

        nc_table_ref: list[ui.table | None] = [None]

        def _nc_rows() -> list[dict]:
            return [
                {
                    'credit_note_id': nc.credit_note_id,
                    'pago_id': nc.pago_id,
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
                for nc in ncs
            ]

        def _render_ncs(nc_container: ui.column) -> None:
            nc_container.clear()
            with nc_container:
                if not ncs:
                    ui.label('Sin notas de crédito asignadas').classes('text-caption')
                    nc_table_ref[0] = None
                    return
                nc_table_ref[0] = ui.table(
                    columns=_NC_COLUMNS,
                    rows=_nc_rows(),
                    row_key='credit_note_id',
                    selection='multiple' if not ciclo.cerrado else 'none',
                ).classes('w-full')

        def _reload_ncs() -> None:
            nonlocal ncs
            with uow_per_request() as uow:
                ncs = list_notas_credito_por_periodo(uow, periodo_id)
            _render_ncs(nc_container)
            _update_btn_states()

        def _update_btn_states() -> None:
            has_ncs = bool(ncs)
            if has_ncs:
                btn_descargar.enable()
            else:
                btn_descargar.disable()
            if not ciclo.cerrado and btn_liberar is not None:
                has_selection = (
                    bool(nc_table_ref[0].selected) if nc_table_ref[0] else False
                )
                if has_ncs and has_selection:
                    btn_liberar.enable()
                else:
                    btn_liberar.disable()

        with modal(
            ciclo.nombre_corto or f'Periodo {periodo_id}', width='w-[44rem]'
        ) as dialog:
            with ui.row().classes('gap-4 w-full'):
                fecha_inicio = date_picker(
                    'Fecha Inicio',
                    value=periodo.fecha_inicio,
                )
                fecha_fin = date_picker(
                    'Fecha Fin',
                    value=periodo.fecha_fin,
                )

            err = error_label()

            with ui.row().classes('justify-between w-full items-center'):
                ui.label('Notas de Crédito').classes('text-subtitle2')
                with ui.row().classes('gap-2'):
                    btn_descargar = ui.button(
                        'Descargar Excel',
                        icon='download',
                    ).props('outlined')
                    if not ncs:
                        btn_descargar.disable()

                    if not ciclo.cerrado:
                        btn_liberar = ui.button(
                            'Desasignar seleccionadas',
                            icon='remove_circle_outline',
                        ).props('flat color=negative')
                        if not ncs:
                            btn_liberar.disable()
                    else:
                        btn_liberar = None

            nc_container = ui.column().classes('gap-1 w-full')
            _render_ncs(nc_container)

            def _on_nc_selection(e=None) -> None:
                _update_btn_states()

            if nc_table_ref[0] is not None:
                nc_table_ref[0].on('selection', _on_nc_selection)

            def _descargar_ncs_excel() -> None:
                if not ncs:
                    return
                excel_bytes = exportar_notas_credito_excel(_nc_rows())
                filename = (
                    f'nc_periodo_{ciclo.nombre_corto or periodo_id}'
                    f'_{date.today().strftime("%Y%m%d")}.xlsx'
                )
                ui.download(excel_bytes, filename=filename)
                ui.notify(
                    f'Descargando {len(ncs)} nota{"s" if len(ncs) > 1 else ""} '
                    f'de crédito en Excel',
                    type='info',
                )

            btn_descargar.on('click', _descargar_ncs_excel)

            if not ciclo.cerrado and btn_liberar is not None:

                def _desasignar_ncs() -> None:
                    tbl = nc_table_ref[0]
                    selected = tbl.selected if tbl else []
                    if not selected:
                        return
                    selected_ids = [
                        int(row['credit_note_id'])
                        for row in selected
                        if 'credit_note_id' in row
                    ]
                    if not selected_ids:
                        return
                    try:
                        with uow_per_request() as uow:
                            for nc_id in selected_ids:
                                DesasignarNotaCreditoAPeriodo(uow)(nc_id)
                    except DomainError as exc:
                        ui.notify(str(exc), type='negative')
                        return
                    cant = len(selected_ids)
                    ui.notify(
                        f'{cant} nota{"s" if cant > 1 else ""} de crédito '
                        f'desasignada{"s" if cant > 1 else ""}',
                        type='positive',
                    )
                    _reload_ncs()

                btn_liberar.on('click', _desasignar_ncs)

            with ui.row().classes('justify-between w-full items-center'):
                if ciclo.cerrado:
                    ui.button(
                        'Reabrir periodo',
                        icon='lock_open',
                        on_click=lambda: (
                            dialog.close(),
                            _confirm_reabrir(periodo_id),
                        ),
                    ).props('flat color=primary')
                else:
                    ui.button(
                        'Cerrar periodo',
                        icon='lock',
                        on_click=lambda: (
                            dialog.close(),
                            _confirm_cerrar(periodo_id),
                        ),
                    ).props('flat color=negative')

            def _guardar_fechas() -> None:
                err.set_text('')
                try:
                    with uow_per_request() as uow:
                        PeriodoActualizar(uow)(
                            PeriodoEdit(
                                id=periodo_id,
                                fecha_inicio=(
                                    date.fromisoformat(fecha_inicio.value)
                                    if fecha_inicio.value
                                    else None
                                ),
                                fecha_fin=(
                                    date.fromisoformat(fecha_fin.value)
                                    if fecha_fin.value
                                    else None
                                ),
                            )
                        )
                except DomainError as exc:
                    err.set_text(str(exc))
                    return
                ui.notify('Fechas actualizadas', type='positive')
                dialog.close()
                render()

            form_footer(dialog, on_save=_guardar_fechas, save_label='Guardar fechas')
        dialog.open()

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

        sorted_cards = sorted(cards, key=lambda c: c.anio_mes or 0, reverse=True)
        total = len(sorted_cards)
        page_count = max(1, (total + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE)
        current_page = [0]

        def _render_cards_page() -> None:
            cards_container.clear()
            start = current_page[0] * CARDS_PER_PAGE
            end = start + CARDS_PER_PAGE
            page_cards = sorted_cards[start:end]

            with cards_container:
                if not sorted_cards:
                    ui.label('Todavía no hay periodos. Creá el primero.').classes(
                        'text-subtitle1'
                    )
                    return

                with ui.row().classes('gap-4 items-stretch flex-wrap'):
                    for ciclo in page_cards:
                        _render_card(
                            ciclo,
                            on_click=_open_editar_periodo,
                        )

                if page_count > 1:
                    with ui.row().classes('justify-center w-full items-center gap-2'):
                        ui.button(
                            icon='chevron_left',
                            on_click=lambda: (
                                current_page.__setitem__(
                                    0, max(0, current_page[0] - 1)
                                ),
                                _render_cards_page(),
                            ),
                        ).props('flat' + (' disable' if current_page[0] == 0 else ''))
                        ui.label(
                            f'Página {current_page[0] + 1} de {page_count}'
                        ).classes('text-caption')
                        ui.button(
                            icon='chevron_right',
                            on_click=lambda: (
                                current_page.__setitem__(
                                    0,
                                    min(page_count - 1, current_page[0] + 1),
                                ),
                                _render_cards_page(),
                            ),
                        ).props(
                            'flat'
                            + (' disable' if current_page[0] >= page_count - 1 else '')
                        )

        cards_container = ui.column().classes('w-full')

        with container:
            _render_cards_page()

    with ui.column().classes('w-full q-px-md q-py-md'):
        with ui.row().classes('gap-2'):
            ui.button(
                'Nuevo Periodo',
                icon='add_circle_outline',
                on_click=lambda: open_nuevo_ciclo(render),
            ).props('unelevated color=primary')
        render()
