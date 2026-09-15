"""Home page: reclamos listing with the three alta dialogs."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from nicegui import events, ui

from src.application.format import format_date, format_money
from src.application.queries import list_grupos, list_home_pagina
from src.application.use_cases.reclamo import ReclamoAlternarEstado
from src.domain.dto.read import ReclamoHomeFilter, ReclamoHomeItem
from src.domain.models.entities import User
from src.ui.deps import uow_per_request
from src.ui.dialogos import (
    open_alta_reclamo,
    open_editar_reclamo,
    open_editar_tresa,
    open_importar_sos,
    open_nuevo_lote_tres_arr,
)
from src.ui.labels import TIPO_FILTRO_OPTIONS, TIPO_KEY, TIPO_LABELS
from src.ui.layout import page
from src.ui.widgets import _text, date_picker, row_action_button

COLUMNS: list[dict] = [
    {'name': 'dominio', 'label': 'Dominio', 'field': 'dominio', 'sortable': True},
    {
        'name': 'fecha_ingresado',
        'label': 'Fecha Ingresado',
        'field': 'fecha_ingresado',
        'sortable': True,
    },
    {'name': 'poliza', 'label': 'Póliza', 'field': 'poliza', 'sortable': True},
    {'name': 'cliente', 'label': 'Cliente', 'field': 'cliente', 'sortable': True},
    {
        'name': 'nro_gestion',
        'label': 'Nro. Gestión SOS',
        'field': 'nro_gestion',
    },
    {
        'name': 'tipo_reclamo',
        'label': 'Tipo de Reclamo',
        'field': 'tipo_reclamo',
        'sortable': True,
    },
    {
        'name': 'importe_reclamado',
        'label': 'Importe Reclamado',
        'field': 'importe_reclamado',
        'align': 'right',
    },
    {
        'name': 'has_pagos',
        'label': 'Con Pagos',
        'field': 'has_pagos',
        'align': 'center',
    },
    {
        'name': 'has_credit_note',
        'label': 'Con Nota de Crédito',
        'field': 'has_credit_note',
        'align': 'center',
    },
    {
        'name': 'editar',
        'label': 'Editar',
        'field': 'editar',
        'align': 'center',
    },
    {
        'name': 'activar',
        'label': 'Activar/Inactivar',
        'field': 'activar',
        'align': 'center',
    },
]


ROWS_PER_PAGE = 20

SORT_FIELD_BY_COLUMN: dict[str, str] = {
    'dominio': 'dominio',
    'fecha_ingresado': 'created_at',
    'poliza': 'poliza',
    'cliente': 'cliente',
    'tipo_reclamo': 'tipo_reclamo',
}


def _row(item: ReclamoHomeItem) -> dict:
    return {
        'reclamo_id': item.reclamo_id,
        'tipo': TIPO_KEY.get(item.tipo_reclamo, '') if item.tipo_reclamo else '',
        'dominio': item.dominio or '',
        'fecha_ingresado': format_date(item.created_at),
        'poliza': item.poliza or '',
        'cliente': item.cliente or '',
        'nro_gestion': item.nro_gestion if item.nro_gestion is not None else '—',
        'tipo_reclamo': TIPO_LABELS.get(item.tipo_reclamo, '')
        if item.tipo_reclamo
        else '',
        'importe_reclamado': format_money(item.importe_reclamado),
        'has_pagos': bool(item.has_pagos),
        'has_credit_note': bool(item.has_credit_note),
        'active': bool(item.active),
    }


def _parse_fecha(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _checkbox_par(si: bool, no: bool) -> bool | None:
    if si and not no:
        return True
    if no and not si:
        return False
    return None


@page('Inicio')
def home(user: User) -> None:
    with ui.column().classes('w-full q-px-md q-py-md'):
        with ui.row().classes('gap-2'):
            ui.button(
                'Importar Excel SOS',
                icon='upload_file',
                on_click=lambda: open_importar_sos(refresh_table),
            )
            ui.button(
                'Nueva 3 Arroyos',
                icon='add_circle_outline',
                on_click=lambda: open_nuevo_lote_tres_arr(refresh_table, user),
            )
            ui.button(
                'Nueva Gestión',
                icon='add_circle_outline',
                on_click=lambda: open_alta_reclamo('especial', refresh_table),
            )

        with ui.card().classes('w-full'):
            with ui.row().classes('gap-6 items-center q-py-sm flex-wrap'):
                con_pagos = ui.checkbox('Con Pagos')
                sin_pagos = ui.checkbox('Sin Pagos')
                ui.separator().props('vertical')
                con_credito = ui.checkbox('Con Nota de Crédito')
                sin_credito = ui.checkbox('Sin Nota de Crédito')
                ui.separator().props('vertical')
                activos = ui.checkbox('Activos')
                inactivos = ui.checkbox('Inactivos')
                ui.separator().props('vertical')
                ui.button('Filtrar', on_click=lambda: _aplicar_filtro()).props(
                    'unelevated color=primary'
                )
                ui.button('Limpiar', on_click=lambda: _limpiar_filtro()).props('flat')
            with ui.row().classes('gap-4 items-end flex-wrap'):
                fecha_desde = date_picker('Desde')
                fecha_hasta = date_picker('Hasta')
                importe_min = ui.number('Importe min', value=None).props(
                    'outlined dense clearable'
                )
                importe_max = ui.number('Importe max', value=None).props(
                    'outlined dense clearable'
                )
                tipo = ui.select(
                    options=TIPO_FILTRO_OPTIONS,
                    label='Tipo de Reclamo',
                    value=None,
                ).props('outlined dense')
                with uow_per_request() as uow:
                    grupo_filter_opciones = list_grupos(uow)
                grupo_filter = ui.select(
                    options=grupo_filter_opciones,
                    label='Grupo',
                    value=None,
                    with_input=True,
                    clearable=True,
                ).props('outlined dense')
                texto = ui.input('Buscar (todos los campos)').props(
                    'outlined dense clearable :debounce="500"'
                )

        def _build_filtro() -> ReclamoHomeFilter | None:
            filtro = ReclamoHomeFilter(
                fecha_desde=_parse_fecha(fecha_desde.value),
                fecha_hasta=_parse_fecha(fecha_hasta.value),
                importe_min=importe_min.value,
                importe_max=importe_max.value,
                con_pagos=_checkbox_par(con_pagos.value, sin_pagos.value),
                con_nota_credito=_checkbox_par(con_credito.value, sin_credito.value),
                active=_checkbox_par(activos.value, inactivos.value),
                tipo_reclamo=tipo.value,
                grupo=_text(grupo_filter.value),
                texto=_text(texto.value),
            )
            if all(
                value is None
                for value in (
                    filtro.fecha_desde,
                    filtro.fecha_hasta,
                    filtro.importe_min,
                    filtro.importe_max,
                    filtro.con_pagos,
                    filtro.con_nota_credito,
                    filtro.active,
                    filtro.tipo_reclamo,
                    filtro.grupo,
                    filtro.texto,
                )
            ):
                return None
            return filtro

        def _fetch_page(
            offset: int, limit: int, sort_by: str | None, descending: bool
        ) -> tuple[list[dict], int]:
            filtro = _build_filtro()
            with uow_per_request() as uow:
                page = list_home_pagina(
                    uow,
                    filtro,
                    offset=offset,
                    limit=limit,
                    sort_by=sort_by,
                    descending=descending,
                )
            return [_row(item) for item in page.items], page.total

        first_rows, total = _fetch_page(0, ROWS_PER_PAGE, None, False)
        table = ui.table(
            columns=COLUMNS,
            rows=first_rows,
            row_key='reclamo_id',
            pagination={'rowsPerPage': ROWS_PER_PAGE, 'rowsNumber': total, 'page': 1},
        ).classes('q-ma-auto')

        current_sort: str | None = None
        current_descending: bool = False

        def _render_page(
            page: int, rows_per_page: int, sort_col: str | None, descending: bool
        ) -> None:
            nonlocal current_sort, current_descending
            current_sort = sort_col
            current_descending = descending
            sort_by = SORT_FIELD_BY_COLUMN.get(sort_col) if sort_col else None
            offset = (page - 1) * rows_per_page
            rows, total = _fetch_page(offset, rows_per_page, sort_by, descending)
            table.update_rows(rows)
            pagination: dict = {
                'page': page,
                'rowsPerPage': rows_per_page,
                'rowsNumber': total,
            }
            if sort_col is not None:
                pagination['sortBy'] = sort_col
                pagination['descending'] = descending
            table.pagination = pagination

        def _on_pagination_change(e: events.ValueChangeEventArguments) -> None:
            pag = e.value or {}
            _render_page(
                int(pag.get('page', 1)),
                int(pag.get('rowsPerPage', ROWS_PER_PAGE)),
                pag.get('sortBy'),
                bool(pag.get('descending')),
            )

        table.on_pagination_change(_on_pagination_change)

        def refresh_table() -> None:
            _render_page(1, ROWS_PER_PAGE, current_sort, current_descending)

        def _aplicar_filtro() -> None:
            refresh_table()

        def _limpiar_filtro() -> None:
            fecha_desde.set_value('')
            fecha_hasta.set_value('')
            importe_min.set_value(None)
            importe_max.set_value(None)
            con_pagos.set_value(False)
            sin_pagos.set_value(False)
            con_credito.set_value(False)
            sin_credito.set_value(False)
            activos.set_value(False)
            inactivos.set_value(False)
            tipo.set_value(None)
            grupo_filter.set_value(None)
            texto.set_value('')
            refresh_table()

        def on_toggle(e: events.GenericEventArguments) -> None:
            reclamo_id = int(cast(Any, e.args))
            with uow_per_request() as uow:
                ReclamoAlternarEstado(uow)(reclamo_id)
            refresh_table()

        def on_edit(e: events.GenericEventArguments) -> None:
            args = cast(dict[str, Any], e.args)
            reclamo_id = int(args['reclamo_id'])
            tipo = args.get('tipo', '')
            if tipo:
                if tipo == 'tresa':
                    open_editar_tresa(reclamo_id, refresh_table)
                else:
                    open_editar_reclamo(tipo, reclamo_id, refresh_table)

        with table.add_slot('body-cell-has_pagos'), table.cell('has_pagos'):
            ui.badge().props("""
                    :color="props.value ? 'green' : 'grey-7'"
                    :label="props.value ? 'Sí' : 'No'"
                """)
        with table.add_slot('body-cell-has_credit_note'), table.cell('has_credit_note'):
            ui.badge().props("""
                    :color="props.value ? 'green' : 'grey-7'"
                    :label="props.value ? 'Sí' : 'No'"
                """)
        row_action_button(table, 'editar', 'edit', on_edit)
        row_action_button(
            table,
            'activar',
            None,
            on_toggle,
            props="""
                    flat dense
                    :label="props.row.active ? 'Inactivar' : 'Activar'"
                    :color="props.row.active ? 'orange' : 'green'"
                """,
            payload='props.row.reclamo_id',
        )
