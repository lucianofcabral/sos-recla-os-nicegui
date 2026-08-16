"""Shared NiceGUI widgets and helpers (pure presentation: rows + callbacks only)."""

from collections.abc import Callable
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
