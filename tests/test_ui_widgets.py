"""Headless tests for src/ui/widgets.py core helpers (backs R6 and R7)."""

from __future__ import annotations

import ast
import pathlib
from typing import Any

from nicegui import events, ui

from src.ui import widgets


def test_ui_widgets() -> None:
    """MAX_ERRORS_SHOWN, _text and make_remove_handler behave as before the refactor."""
    assert widgets.MAX_ERRORS_SHOWN == 50

    assert widgets._text(None) is None
    assert widgets._text('   ') is None
    assert widgets._text('  abc  ') == 'abc'
    assert widgets._text(123) == '123'

    removed: list[int] = []
    rows: list[dict[str, Any]] = [{'idx': 0}, {'idx': 1}, {'idx': 2}]
    handler = widgets.make_remove_handler(rows, lambda: removed.append(len(rows)))
    handler(events.GenericEventArguments(sender=None, client=None, args={'idx': 1}))
    assert [row['idx'] for row in rows] == [0, 2]
    assert removed == [2]
    handler(events.GenericEventArguments(sender=None, client=None, args={'idx': 99}))
    assert [row['idx'] for row in rows] == [0, 2]
    assert removed == [2, 2]
    handler(events.GenericEventArguments(sender=None, client=None, args={'idx': -1}))
    assert [row['idx'] for row in rows] == [0, 2]
    assert removed == [2, 2, 2]


def _module_imports(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or '')
    return names


def test_ui_widgets_purity() -> None:
    """widgets.py and labels.py must not import ORM/UoW/query layers (backs R7)."""
    widgets_imports = _module_imports(pathlib.Path('src/ui/widgets.py'))
    assert widgets_imports == {
        'nicegui',
        'collections.abc',
        'contextlib',
        'datetime',
        'typing',
    }

    labels_imports = _module_imports(pathlib.Path('src/ui/labels.py'))
    assert labels_imports == {'src.domain.domain_enums'}


def _inside_dialog(dialog: ui.dialog) -> ui.column:
    """Return the modal's inner column (dialog -> card -> column)."""
    card = dialog.slots['default'].children[0]
    return card.slots['default'].children[0]


def test_ui_widgets_modal() -> None:
    """modal() renders the h6 title inside the column and yields the dialog."""
    with widgets.modal('Nuevo Pago') as dialog:
        assert isinstance(dialog, ui.dialog)
    inner = _inside_dialog(dialog)
    titles = [
        child.text
        for child in inner.slots['default'].children
        if isinstance(child, ui.label)
    ]
    assert titles == ['Nuevo Pago']


def test_ui_widgets_modal_without_title() -> None:
    """modal(title=None) leaves the header to the caller (grupo mutable header)."""
    with widgets.modal(title=None, width='w-[44rem]') as dialog:
        assert isinstance(dialog, ui.dialog)
    inner = _inside_dialog(dialog)
    assert inner.slots['default'].children == []


def _footer_button_texts(col: ui.column) -> list[str]:
    texts: list[str] = []

    def walk(element) -> None:
        for slot in element.slots.values():
            for child in slot.children:
                if isinstance(child, ui.button):
                    texts.append(child.text)
                walk(child)

    walk(col)
    return texts


def test_ui_widgets_form_footer() -> None:
    """Standard footer: flat cancel + primary save, no nested rows."""
    dialog = ui.dialog()
    with ui.column() as col:
        widgets.form_footer(dialog, on_save=lambda: None)
    footer_row = col.slots['default'].children[0]
    assert [child.text for child in footer_row.slots['default'].children] == [
        'Cancelar',
        'Guardar',
    ]
    assert len(footer_row.slots['default'].children) == 2


def test_ui_widgets_form_footer_custom_labels() -> None:
    """Custom save_label/cancel_label override the defaults."""
    dialog = ui.dialog()
    with ui.column() as col:
        widgets.form_footer(
            dialog,
            on_save=lambda: None,
            save_label='Aplicar',
            cancel_label='Cerrar',
        )
    assert _footer_button_texts(col) == ['Cerrar', 'Aplicar']


def test_ui_widgets_form_footer_cancel_only() -> None:
    """on_save=None renders the cancel-only footer (grupo case)."""
    dialog = ui.dialog()
    with ui.column() as col:
        widgets.form_footer(dialog, on_save=None, cancel_label='Cerrar')
    assert _footer_button_texts(col) == ['Cerrar']


def test_ui_widgets_form_footer_extra_right() -> None:
    """extra_right buttons nest with the save button (lote case)."""
    dialog = ui.dialog()
    with ui.column() as col:
        widgets.form_footer(
            dialog,
            on_save=lambda: None,
            save_label='Guardar lote',
            extra_right=[
                {
                    'label': 'Pagar todas juntas',
                    'icon': 'payments',
                    'props': 'flat color=primary',
                    'handler': lambda: None,
                }
            ],
        )
    assert _footer_button_texts(col) == [
        'Cancelar',
        'Pagar todas juntas',
        'Guardar lote',
    ]


def test_ui_widgets_error_label() -> None:
    """error_label() returns a label carrying the given message text."""
    err = widgets.error_label('No se pudo guardar')
    assert isinstance(err, ui.label)
    assert err.text == 'No se pudo guardar'
    assert widgets.error_label().text == ''


def test_ui_widgets_pagos_table_action() -> None:
    """pagos_table appends the actions column and wires the row-action slot."""
    table = widgets.pagos_table(
        [
            {
                'id': 1,
                'fecha': '01/01/2024',
                'forma': 'Transferencia',
                'pagador': 'SM',
                'destinatario': 'Prestador',
                'monto': '1.000,00',
            }
        ],
        row_key='id',
        actions='editar',
        action_icon='edit',
        on_action=lambda e: None,
    )
    columns = [col['name'] for col in table._props['columns']]
    assert columns == ['fecha', 'forma', 'pagador', 'destinatario', 'monto', 'editar']
    assert 'body-cell-editar' in table.slots


def test_ui_widgets_pagos_table_no_actions() -> None:
    """pagos_table without actions keeps the standard 5-column set."""
    table = widgets.pagos_table([])
    columns = [col['name'] for col in table._props['columns']]
    assert columns == ['fecha', 'forma', 'pagador', 'destinatario', 'monto']
