"""Smoke tests: importing the UI and scripts modules must not start a server."""

from __future__ import annotations

import importlib
import pathlib


def test_ui_and_scripts_modules_import() -> None:
    for module in (
        'src.ui.main',
        'src.ui.deps',
        'src.ui.layout',
        'src.ui.dialogos',
        'src.ui.labels',
        'src.ui.widgets',
        'src.ui.pages.login',
        'src.ui.pages.home',
        'src.ui.pages.pagos',
        'src.ui.pages.periodos',
        'src.ui.pages.migracion',
        'scripts.bootstrap',
    ):
        importlib.import_module(module)


def test_main_imports_do_not_blank() -> None:
    import src.ui.main

    assert callable(src.ui.main.start)


def test_ui_run_guarded_by_main_guard() -> None:
    main_source = pathlib.Path('src/ui/main.py').read_text()
    assert 'ui.run(' in main_source
    assert 'reload=False' in main_source
    guard_index = main_source.index("if __name__ == '__main__':")
    start_call_index = main_source.index('start()\n')
    run_index = main_source.index('ui.run(')
    assert guard_index < start_call_index
    assert run_index < start_call_index


def test_dialogos_exports_document_section() -> None:
    import src.ui.dialogos

    assert callable(src.ui.dialogos.seccion_documentos)
