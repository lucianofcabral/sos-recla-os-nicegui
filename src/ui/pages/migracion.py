"""Migración page (ADMIN only): import a legacy SQLite DB into the app database."""

from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from pathlib import Path

from nicegui import background_tasks, events, run, ui
from sqlmodel import Session

from src.application.import_gestiones import import_gestiones
from src.domain.models.entities import User
from src.infrastructure.database import build_engine, create_schema
from src.infrastructure.import_ledger import (
    SqlModelImportLedger,
    create_import_ledger,
)
from src.infrastructure.unit_of_work import SqlModelUnitOfWork
from src.ui.layout import page
from src.ui.widgets import MAX_ERRORS_SHOWN, error_label, form_footer, modal

REPORT_LABELS: dict[str, str] = {
    'sos': 'Reclamos SOS',
    'tres_arr': 'Reclamos 3 Arroyos',
    'otros': 'Reclamos Gestión',
    'pagos': 'Pagos',
    'notas_credito': 'Notas de crédito',
    'facturas': 'Facturas',
    'periodos': 'Periodos',
    'documentos': 'Documentos',
    'entidad_documentos': 'Documentos por entidad',
}


def _migrate(old_path: str, apply: bool) -> dict:
    """Run the legacy import against the app database (blocking, worker thread)."""
    engine = build_engine()
    create_schema(engine)
    with Session(engine) as session:
        create_import_ledger(session)
        report = import_gestiones(
            old_path=old_path,
            uow=SqlModelUnitOfWork(session),
            ledger=SqlModelImportLedger(session),
            dry_run=not apply,
        )
    return report


def _remove_workspace(path: str | None) -> None:
    """Best-effort removal of an uploaded migration workspace."""
    if path is None:
        return
    shutil.rmtree(path, ignore_errors=True)


def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract a migration ZIP while rejecting path traversal entries."""
    destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        try:
            target.relative_to(destination)
        except ValueError as exc:
            raise ValueError(
                f'El ZIP contiene una ruta inválida: {member.filename}'
            ) from exc
    archive.extractall(destination)


def _prepare_upload(filename: str, data: bytes) -> tuple[str, str]:
    """Save a DB or migration ZIP and return ``(db_path, workspace)``."""
    workspace = tempfile.mkdtemp(prefix='sos-migracion-')
    try:
        suffix = Path(filename).suffix.lower()
        if suffix == '.db':
            db_path = Path(workspace) / 'gestiones.db'
            db_path.write_bytes(data)
            return str(db_path), workspace
        if suffix != '.zip':
            raise ValueError('Seleccioná un archivo .db o un ZIP de migración')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            _safe_extract_zip(archive, Path(workspace))
        databases = list(Path(workspace).rglob('*.db'))
        if len(databases) != 1:
            raise ValueError('El ZIP debe contener exactamente una base .db')
        return str(databases[0]), workspace
    except Exception:
        _remove_workspace(workspace)
        raise


@page('Migración', path='/migracion', admin_only=True)
def migracion(user: User) -> None:
    """ADMIN-only page to import a legacy SQLite database into the app database."""
    ui.label(
        'Importar una base legada (SQLite) a la base actual. Solo administradores.'
    )

    selected: dict[str, str | None] = {'path': None, 'workspace': None}
    apply_checkbox = ui.checkbox('Aplicar (escribir en la base)')
    ui.label(
        'Sin marcar, la importación es un dry run: solo cuenta y no escribe nada.'
    ).classes('text-caption text-grey-7')

    upload = ui.upload(
        label='Seleccionar archivo .db o ZIP de migración',
        auto_upload=True,
        on_upload=lambda e: _handle_upload(e),
    ).props('accept=".db,.zip"')

    import_button = ui.button(
        'Importar',
        icon='upload',
        on_click=lambda: _confirm_or_import(),
    ).props('unelevated color=primary')
    import_button.set_enabled(False)

    progress = ui.linear_progress(show_value=False).props('indeterminate')
    progress.set_visibility(False)

    report_container = ui.column().classes('w-full')

    def _set_running(running: bool) -> None:
        upload.set_enabled(not running)
        import_button.set_enabled(not running and selected['path'] is not None)
        apply_checkbox.set_enabled(not running)
        progress.set_visibility(running)

    async def _handle_upload(e: events.UploadEventArguments) -> None:
        data = await e.file.read()
        try:
            db_path, workspace = _prepare_upload(e.file.name, data)
        except (ValueError, zipfile.BadZipFile) as exc:
            ui.notify(f'Archivo inválido: {exc}', type='negative')
            e.sender.reset()
            return
        old_workspace = selected['workspace']
        selected['path'] = db_path
        selected['workspace'] = workspace
        _remove_workspace(old_workspace)
        e.sender.reset()
        import_button.set_enabled(True)
        ui.notify(f'Archivo {e.file.name} seleccionado', type='positive')

    def _confirm_or_import() -> None:
        apply = bool(apply_checkbox.value)
        if apply:
            _confirm_apply(apply)
        else:
            _start_import(apply)

    def _confirm_apply(apply: bool) -> None:
        with modal('Confirmar importación') as dialog:
            ui.label('Esto escribe los cambios en la base actual. ¿Continuar?')
            form_footer(
                dialog,
                on_save=lambda: _start_import(apply, dialog),
                save_label='Importar',
            )
        dialog.open()

    def _start_import(apply: bool, dialog: ui.dialog | None = None) -> None:
        if dialog is not None:
            dialog.close()
        if selected['path'] is None:
            ui.notify('Seleccioná un archivo .db primero', type='warning')
            return
        background_tasks.create(_importar(apply), name='import-gestiones')

    async def _importar(apply: bool) -> None:
        _set_running(True)
        try:
            report = await run.io_bound(_migrate, selected['path'], apply)
        except Exception as exc:
            ui.notify(f'Error al importar: {exc}', type='negative')
            _render_errors([str(exc)])
            return
        finally:
            _remove_workspace(selected['workspace'])
            selected['path'] = None
            selected['workspace'] = None
            upload.reset()
            _set_running(False)
        _render_report(report, apply)
        errores = report.get('errores', [])
        if errores:
            ui.notify(
                f'Importación finalizada con {len(errores)} errores',
                type='warning',
            )
        else:
            ui.notify('Importación finalizada sin errores', type='positive')

    def _render_errors(errors: list[str]) -> None:
        report_container.clear()
        with (
            report_container,
            ui.card().classes('w-full'),
            ui.column().classes('gap-2 w-full'),
        ):
            error_label('No se pudo completar la importación').classes(add='text-h6')
            ui.code('\n'.join(errors))

    def _render_report(report: dict, apply: bool) -> None:
        modo = 'ESCRITURA' if apply else 'DRY RUN'
        report_container.clear()
        with (
            report_container,
            ui.card().classes('w-full'),
            ui.column().classes('gap-2 w-full'),
        ):
            ui.label(f'Resultado de la importación ({modo})').classes('text-h6')
            with ui.grid(columns=2).classes('gap-x-8 gap-y-1 w-full'):
                for key, label in REPORT_LABELS.items():
                    ui.label(label)
                    ui.label(str(report.get(key, 0))).classes('text-right')
            errores = report.get('errores', [])
            if errores:
                error_label(f'Errores: {len(errores)}').classes(
                    add='text-weight-medium'
                )
                shown = errores[:MAX_ERRORS_SHOWN]
                ui.code('\n'.join(str(error) for error in shown))
                if len(errores) > MAX_ERRORS_SHOWN:
                    rest = len(errores) - MAX_ERRORS_SHOWN
                    ui.label(f'... y {rest} errores más.').classes('text-caption')
            else:
                ui.label('Sin errores.').classes('text-positive')
