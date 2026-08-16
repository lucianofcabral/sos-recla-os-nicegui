"""Headless tests for src/ui/widgets.py core helpers (backs R6 and R7)."""

from __future__ import annotations

import ast
import pathlib
from typing import Any

from nicegui import events

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
    assert widgets_imports == {'nicegui', 'collections.abc', 'typing'}

    labels_imports = _module_imports(pathlib.Path('src/ui/labels.py'))
    assert labels_imports == {'src.domain.domain_enums'}
