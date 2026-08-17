"""Shared NiceGUI widgets and helpers (pure presentation: rows + callbacks only)."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, cast

from nicegui import events, ui

MAX_ERRORS_SHOWN = 50


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def row_action_button(
    table,
    column: str,
    icon: str | None = None,
    handler=None,
    *,
    props: str = 'flat dense',
    event: str = 'click',
    payload: str = 'props.row',
) -> None:
    """Add a row-action button to a table column (body-cell slot + click handler)."""
    with table.add_slot(f'body-cell-{column}'), table.cell(column):
        ui.button(icon=icon).props(props).on(
            event,
            js_handler=f'() => emit({payload})',
            handler=handler,
        )


PAGO_COLUMNS: list[dict] = [
    {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha'},
    {'name': 'forma', 'label': 'Forma', 'field': 'forma'},
    {'name': 'pagador', 'label': 'Pagador', 'field': 'pagador'},
    {'name': 'destinatario', 'label': 'Destinatario', 'field': 'destinatario'},
    {'name': 'monto', 'label': 'Importe', 'field': 'monto', 'align': 'right'},
]


def pagos_table(
    rows: list[dict],
    *,
    columns: list[dict] | None = None,
    row_key: str = 'pago_id',
    actions: str | None = None,
    on_action=None,
    action_props: str = 'flat dense',
    classes: str = 'w-full',
) -> ui.table:
    """Render a pagos table with the standard 5-column set or a custom column set.

    ``actions`` names the column hosting the per-row delete button; its column
    definition is appended when not already present in ``columns``.
    """
    effective = list(PAGO_COLUMNS) if columns is None else list(columns)
    if actions is not None and not any(col.get('name') == actions for col in effective):
        effective.append(
            {'name': actions, 'label': '', 'field': actions, 'align': 'center'}
        )
    table = ui.table(columns=effective, rows=rows, row_key=row_key).classes(classes)
    if actions is not None and on_action is not None:
        row_action_button(table, actions, 'delete', on_action, props=action_props)
    return table


def make_remove_handler(
    rows: list[dict], on_remove: Callable[[], None]
) -> Callable[[events.GenericEventArguments], None]:
    """Return a quitar-por-idx handler that pops the row and re-renders."""

    def _handler(e: events.GenericEventArguments) -> None:
        args = cast(dict[str, Any], e.args)
        idx = int(args.get('idx', -1))
        if 0 <= idx < len(rows):
            rows.pop(idx)
        on_remove()

    return _handler


@contextmanager
def modal(title: str | None = None, width: str = 'w-96') -> Iterator[ui.dialog]:
    """Dialog shell: card(width) + column + optional h6 title; yields the dialog.

    ``title=None`` leaves the header to the caller (mutable group header case).
    """
    with (
        ui.dialog() as dialog,
        ui.card().classes(f'{width} max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        if title is not None:
            ui.label(title).classes('text-h6')
        yield dialog


def form_footer(
    dialog,
    on_save=None,
    *,
    save_label: str = 'Guardar',
    cancel_label: str = 'Cancelar',
    extra_right: list[dict[str, Any]] | None = None,
) -> None:
    """Render the footer row: flat cancel + primary save button.

    ``extra_right`` dicts ``{label, icon, props, handler}`` nest in a ``gap-2``
    row with the save button; ``on_save=None`` renders a cancel-only footer.
    """
    with ui.row().classes('justify-between w-full'):
        ui.button(cancel_label, on_click=dialog.close).props('flat')
        if on_save is not None:
            if extra_right:
                with ui.row().classes('gap-2'):
                    for item in extra_right:
                        ui.button(
                            item['label'],
                            icon=item.get('icon'),
                            on_click=item['handler'],
                        ).props(item.get('props', ''))
                    ui.button(save_label, on_click=on_save).props(
                        'unelevated color=primary'
                    )
            else:
                ui.button(save_label, on_click=on_save).props(
                    'unelevated color=primary'
                )


def error_label(text: str = '') -> ui.label:
    """Return a label pre-styled for inline form errors."""
    return ui.label(text).classes('text-negative')
