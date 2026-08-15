"""Shared dialogs for the UI pages (alta/editar reclamo, nuevo pago, nuevo ciclo, lote)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date
from typing import Any, cast

from nicegui import events, run, ui
from pydantic import ValidationError

from src.application.format import format_date, format_money
from src.application.import_excel_sos import (
    ImportExcelSosReport,
    importar_excel_sos,
)
from src.application.use_cases.lote import LoteTresArrNuevo
from src.application.use_cases.pago import PagoNuevo
from src.application.use_cases.periodo import PeriodoNuevo
from src.application.use_cases.reclamo import (
    OtrosReclamoActualizar,
    OtrosReclamoConPagosNuevo,
    OtrosReclamoNuevo,
    SosReclamoActualizar,
    SosReclamoNuevo,
    TresArrReclamoActualizar,
    TresArrReclamoNuevo,
)
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoReclamoEnum
from src.domain.dto.create import (
    DocumentoCreate,
    GestionLoteItem,
    LoteTresArrCreate,
    OtrosReclamoCreate,
    PagoCreate,
    PagoReclamoCreate,
    PeriodoCreate,
    ReclamoCreate,
    ReclamoSosCreate,
    TresArrReclamoCreate,
)
from src.domain.dto.edit import OtrosReclamoEdit, ReclamoSosEdit, TresArrReclamoEdit
from src.domain.exceptions import DomainError
from src.domain.models.entities import Pago, User
from src.ui.deps import uow_per_request

TIPO_LABELS: dict[TipoReclamoEnum, str] = {
    TipoReclamoEnum.SOS: 'SOS',
    TipoReclamoEnum.TRESA: '3 Arroyos',
    TipoReclamoEnum.OTROS: 'Gestión',
}

TIPO_ENUM: dict[str, TipoReclamoEnum] = {
    'sos': TipoReclamoEnum.SOS,
    'tresa': TipoReclamoEnum.TRESA,
    'especial': TipoReclamoEnum.OTROS,
}

FORMA_PAGO_LABELS: dict[FormaPagoEnum, str] = {
    FormaPagoEnum.TRANSFERENCIA: 'Transferencia',
    FormaPagoEnum.NOTA_DE_CREDITO: 'Nota de Crédito',
    FormaPagoEnum.NC_POLIZA: 'NC Póliza',
    FormaPagoEnum.EFECTIVO: 'Efectivo',
    FormaPagoEnum.CHEQUE: 'Cheque',
    FormaPagoEnum.CUENTA_CORRIENTE: 'Cuenta Corriente',
}

AGENTE_LABELS: dict[AgenteEnum, str] = {agente: agente.value for agente in AgenteEnum}

MAX_ERRORS_SHOWN = 50


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validation_text(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        loc = '.'.join(str(part) for part in error.get('loc', ()))
        message = str(error.get('msg', ''))
        parts.append(f'{loc}: {message}' if loc else message)
    return 'Datos inválidos: ' + '; '.join(parts)


def _file_hash(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _crear_reclamo(tipo: str, values: dict[str, Any]) -> None:
    base = ReclamoCreate(
        tipo_reclamo=TIPO_ENUM[tipo],
        cliente=_text(values.get('cliente')),
        poliza=_text(values.get('poliza')) or '',
        dominio=_text(values.get('dominio')) or '',
        importe_reclamado=float(values.get('importe_reclamado') or 0.0),
        comentario=_text(values.get('comentario')),
    )
    with uow_per_request() as uow:
        if tipo == 'sos':
            nro = values.get('nro_gestion')
            if nro in (None, ''):
                raise DomainError('El Nro. de Gestión SOS es obligatorio')
            SosReclamoNuevo(uow)(ReclamoSosCreate(reclamo=base, nro_gestion=int(nro)))
        elif tipo == 'tresa':
            TresArrReclamoNuevo(uow)(
                TresArrReclamoCreate(reclamo=base, grupo=_text(values.get('grupo')))
            )
        else:
            OtrosReclamoNuevo(uow)(OtrosReclamoCreate(reclamo=base))


def _editar_reclamo(tipo: str, reclamo_id: int, values: dict[str, Any]) -> None:
    with uow_per_request() as uow:
        if tipo == 'sos':
            nro = values.get('nro_gestion')
            if nro in (None, ''):
                raise DomainError('El Nro. de Gestión SOS es obligatorio')
            SosReclamoActualizar(uow)(
                ReclamoSosEdit(
                    id=reclamo_id,
                    nro_gestion=int(nro),
                    cliente=_text(values.get('cliente')),
                    poliza=_text(values.get('poliza')) or '',
                    dominio=_text(values.get('dominio')) or '',
                    importe_reclamado=float(values.get('importe_reclamado') or 0.0),
                    comentario=_text(values.get('comentario')),
                )
            )
        elif tipo == 'tresa':
            TresArrReclamoActualizar(uow)(
                TresArrReclamoEdit(
                    id=reclamo_id,
                    grupo=_text(values.get('grupo')),
                    cliente=_text(values.get('cliente')),
                    poliza=_text(values.get('poliza')) or '',
                    dominio=_text(values.get('dominio')) or '',
                    importe_reclamado=float(values.get('importe_reclamado') or 0.0),
                    comentario=_text(values.get('comentario')),
                )
            )
        else:
            OtrosReclamoActualizar(uow)(
                OtrosReclamoEdit(
                    id=reclamo_id,
                    cliente=_text(values.get('cliente')),
                    poliza=_text(values.get('poliza')) or '',
                    dominio=_text(values.get('dominio')) or '',
                    importe_reclamado=float(values.get('importe_reclamado') or 0.0),
                    comentario=_text(values.get('comentario')),
                )
            )


def _valores_actuales(tipo: str, reclamo_id: int) -> dict[str, Any]:
    """Load current values of a reclamo to prefill the edit dialog."""
    with uow_per_request() as uow:
        reclamo = uow.reclamos.get(reclamo_id)
        values: dict[str, Any] = {
            'cliente': reclamo.cliente,
            'poliza': reclamo.poliza,
            'dominio': reclamo.dominio,
            'importe_reclamado': reclamo.importe_reclamado,
            'comentario': reclamo.comentario,
        }
        if tipo == 'sos':
            sos = uow.reclamos_sos.get_by_reclamo_id(reclamo_id)
            values['nro_gestion'] = sos.nro_gestion if sos is not None else None
        elif tipo == 'tresa':
            tresa = uow.tres_arr.get_by_reclamo_id(reclamo_id)
            values['grupo'] = tresa.grupo if tresa is not None else None
    return values


def _pagos_del_reclamo(reclamo_id: int) -> list[Pago]:
    with uow_per_request() as uow:
        return uow.pagos.list(reclamo_id=reclamo_id)


def _load_reclamos() -> dict[int, str]:
    with uow_per_request() as uow:
        items = uow.reclamos.list(active_only=True)
    return {
        reclamo.id: (
            f'{reclamo.dominio or ""} · {reclamo.poliza or ""} · '
            f'{reclamo.cliente or ""} '
            f'({TIPO_LABELS[reclamo.tipo_reclamo] if reclamo.tipo_reclamo else ""})'
        )
        for reclamo in items
        if reclamo.id is not None
    }


def open_alta_reclamo(tipo: str, refresh: Callable[[], None]) -> None:
    with (
        ui.dialog() as dialog,
        ui.card().classes('w-[32rem] max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        ui.label(f'Nuevo reclamo {TIPO_LABELS[TIPO_ENUM[tipo]]}').classes('text-h6')
        with ui.grid(columns=2).classes('gap-4 w-full'):
            cliente = ui.input('Cliente').props('outlined')
            poliza = ui.input('Póliza').props('outlined')
            dominio = ui.input('Dominio').props('outlined')
            importe = ui.number('Importe Reclamado', format='%.2f', value=0).props(
                'outlined'
            )
            comentario = ui.textarea('Comentario').props('outlined rows=2')
            nro_gestion = (
                ui.number('Nro. de Gestión SOS').props('outlined')
                if tipo == 'sos'
                else None
            )
            grupo = ui.input('Grupo').props('outlined') if tipo == 'tresa' else None

        pagos: list[dict[str, Any]] = []
        if tipo == 'especial':
            ui.label('Pagos del reclamo').classes('text-subtitle1')
            with ui.row().classes('gap-2 w-full flex-wrap'):
                fecha_pago = ui.date(value=date.today())
                forma_pago = ui.select(options=FORMA_PAGO_LABELS, label='Forma de Pago')
                monto_pago = ui.number('Importe', format='%.2f', value=0).props(
                    'outlined'
                )
                pagador_pago = ui.select(options=AGENTE_LABELS, label='Pagador').props(
                    'outlined'
                )
                destinatario_pago = ui.select(
                    options=AGENTE_LABELS, label='Destinatario'
                ).props('outlined')
            nota = ui.label('Nota de crédito: SOS paga a SM').classes('text-caption')
            nota.bind_visibility_from(
                forma_pago, 'value', lambda v: v == FormaPagoEnum.NOTA_DE_CREDITO
            )
            pagador_pago.bind_visibility_from(
                forma_pago, 'value', lambda v: v != FormaPagoEnum.NOTA_DE_CREDITO
            )
            destinatario_pago.bind_visibility_from(
                forma_pago, 'value', lambda v: v != FormaPagoEnum.NOTA_DE_CREDITO
            )

            pagos_container = ui.column().classes('gap-1 w-full')

            def _render_pagos() -> None:
                pagos_container.clear()
                if not pagos:
                    with pagos_container:
                        ui.label('Sin pagos cargados').classes('text-caption')
                    return
                with pagos_container:
                    table = ui.table(
                        columns=[
                            {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha'},
                            {'name': 'forma', 'label': 'Forma', 'field': 'forma'},
                            {
                                'name': 'pagador',
                                'label': 'Pagador',
                                'field': 'pagador',
                            },
                            {
                                'name': 'destinatario',
                                'label': 'Destinatario',
                                'field': 'destinatario',
                            },
                            {
                                'name': 'monto',
                                'label': 'Importe',
                                'field': 'monto',
                                'align': 'right',
                            },
                            {
                                'name': 'quitar',
                                'label': '',
                                'field': 'quitar',
                                'align': 'center',
                            },
                        ],
                        rows=[
                            {
                                'idx': idx,
                                'fecha': format_date(p['fecha']),
                                'forma': FORMA_PAGO_LABELS.get(p['forma'], ''),
                                'pagador': AGENTE_LABELS.get(p['pagador'], ''),
                                'destinatario': AGENTE_LABELS.get(
                                    p['destinatario'], ''
                                ),
                                'monto': format_money(p['monto']),
                            }
                            for idx, p in enumerate(pagos)
                        ],
                        row_key='idx',
                    ).classes('w-full')
                    with table.add_slot('body-cell-quitar'), table.cell('quitar'):
                        ui.button(icon='delete').props('flat dense').on(
                            'click',
                            js_handler='() => emit(props.row)',
                            handler=_on_quitar_pago,
                        )

            def _on_quitar_pago(e: events.GenericEventArguments) -> None:
                args = cast(dict[str, Any], e.args)
                idx = int(args.get('idx', -1))
                if 0 <= idx < len(pagos):
                    pagos.pop(idx)
                _render_pagos()

            def _agregar_pago() -> None:
                error.set_text('')
                if forma_pago.value is None:
                    error.set_text('Seleccioná la forma de pago')
                    return
                monto_val = float(monto_pago.value or 0.0)
                if monto_val <= 0:
                    error.set_text('monto debe ser mayor a cero')
                    return
                es_nc = forma_pago.value == FormaPagoEnum.NOTA_DE_CREDITO
                if es_nc:
                    pagador_val = AgenteEnum.SOS
                    destinatario_val = AgenteEnum.SM
                else:
                    pagador_val = pagador_pago.value
                    destinatario_val = destinatario_pago.value
                    if pagador_val == destinatario_val:
                        error.set_text('el pagador no puede ser igual al destinatario')
                        return
                fecha_val = fecha_pago.value
                pagos.append(
                    {
                        'fecha': (
                            fecha_val
                            if isinstance(fecha_val, date)
                            else date.fromisoformat(fecha_val)
                        ),
                        'forma': forma_pago.value,
                        'pagador': pagador_val,
                        'destinatario': destinatario_val,
                        'monto': monto_val,
                    }
                )
                monto_pago.set_value(0)
                forma_pago.set_value(None)
                fecha_pago.set_value(date.today())
                _render_pagos()

            ui.button(
                'Agregar pago',
                icon='playlist_add',
                on_click=_agregar_pago,
            ).props('unelevated color=primary')
            _render_pagos()

        error = ui.label('').classes('text-negative')

        def guardar() -> None:
            error.set_text('')
            values = {
                'cliente': cliente.value,
                'poliza': poliza.value,
                'dominio': dominio.value,
                'importe_reclamado': importe.value,
                'comentario': comentario.value,
            }
            if nro_gestion is not None:
                values['nro_gestion'] = nro_gestion.value
            if grupo is not None:
                values['grupo'] = grupo.value
            try:
                if tipo == 'especial':
                    with uow_per_request() as uow:
                        base = ReclamoCreate(
                            tipo_reclamo=TIPO_ENUM[tipo],
                            cliente=_text(values.get('cliente')),
                            poliza=_text(values.get('poliza')) or '',
                            dominio=_text(values.get('dominio')) or '',
                            importe_reclamado=float(
                                values.get('importe_reclamado') or 0.0
                            ),
                            comentario=_text(values.get('comentario')),
                        )
                        lista_pagos = [
                            PagoReclamoCreate(
                                fecha_pago=p['fecha'],
                                forma_pago=p['forma'],
                                pagador=p['pagador'],
                                destinatario=p['destinatario'],
                                monto=p['monto'],
                            )
                            for p in pagos
                        ]
                        OtrosReclamoConPagosNuevo(uow)(
                            OtrosReclamoCreate(reclamo=base), lista_pagos
                        )
                else:
                    _crear_reclamo(tipo, values)
            except DomainError as exc:
                error.set_text(str(exc))
                return
            except ValidationError as exc:
                error.set_text(_validation_text(exc))
                return
            if tipo == 'especial':
                cantidad = len(pagos)
                ui.notify(
                    f'Gestión guardada: {cantidad} pagos'
                    if cantidad
                    else 'Gestión guardada',
                    type='positive',
                )
            dialog.close()
            refresh()

        with ui.row().classes('justify-between w-full'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar', on_click=guardar).props('unelevated color=primary')
    dialog.open()


def open_editar_reclamo(
    tipo: str, reclamo_id: int, refresh: Callable[[], None]
) -> None:
    current = _valores_actuales(tipo, reclamo_id)
    pagos = _pagos_del_reclamo(reclamo_id)
    with (
        ui.dialog() as dialog,
        ui.card().classes('w-[38rem] max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        ui.label(f'Editar reclamo {TIPO_LABELS[TIPO_ENUM[tipo]]}').classes('text-h6')
        with ui.grid(columns=2).classes('gap-4 w-full'):
            cliente = ui.input('Cliente', value=current.get('cliente') or '').props(
                'outlined'
            )
            poliza = ui.input('Póliza', value=current.get('poliza') or '').props(
                'outlined'
            )
            dominio = ui.input('Dominio', value=current.get('dominio') or '').props(
                'outlined'
            )
            importe = ui.number(
                'Importe Reclamado',
                format='%.2f',
                value=current.get('importe_reclamado') or 0.0,
            ).props('outlined')
            comentario = ui.textarea(
                'Comentario', value=current.get('comentario') or ''
            ).props('outlined rows=2')
            nro_gestion = (
                ui.number(
                    'Nro. de Gestión SOS', value=current.get('nro_gestion') or 0
                ).props('outlined readonly')
                if tipo == 'sos'
                else None
            )
            grupo = (
                ui.input('Grupo', value=current.get('grupo') or '')
                if tipo == 'tresa'
                else None
            )
        error = ui.label('').classes('text-negative')

        ui.label('Pagos del reclamo').classes('text-subtitle2')
        if pagos:
            ui.table(
                columns=[
                    {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha'},
                    {'name': 'forma', 'label': 'Forma', 'field': 'forma'},
                    {'name': 'pagador', 'label': 'Pagador', 'field': 'pagador'},
                    {
                        'name': 'destinatario',
                        'label': 'Destinatario',
                        'field': 'destinatario',
                    },
                    {
                        'name': 'monto',
                        'label': 'Importe',
                        'field': 'monto',
                        'align': 'right',
                    },
                ],
                rows=[
                    {
                        'id': pago.id,
                        'fecha': format_date(pago.fecha_pago),
                        'forma': (
                            FORMA_PAGO_LABELS.get(pago.forma_pago, '')
                            if pago.forma_pago is not None
                            else ''
                        ),
                        'pagador': (
                            AGENTE_LABELS.get(pago.pagador, '')
                            if pago.pagador is not None
                            else ''
                        ),
                        'destinatario': (
                            AGENTE_LABELS.get(pago.destinatario, '')
                            if pago.destinatario is not None
                            else ''
                        ),
                        'monto': format_money(pago.monto),
                    }
                    for pago in pagos
                ],
                row_key='id',
            ).classes('w-full')
        else:
            ui.label('Sin pagos registrados').classes('text-caption')

        def guardar() -> None:
            error.set_text('')
            values = {
                'cliente': cliente.value,
                'poliza': poliza.value,
                'dominio': dominio.value,
                'importe_reclamado': importe.value,
                'comentario': comentario.value,
            }
            if nro_gestion is not None:
                values['nro_gestion'] = nro_gestion.value
            if grupo is not None:
                values['grupo'] = grupo.value
            try:
                _editar_reclamo(tipo, reclamo_id, values)
            except DomainError as exc:
                error.set_text(str(exc))
                return
            except ValidationError as exc:
                error.set_text(_validation_text(exc))
                return
            dialog.close()
            refresh()

        with ui.row().classes('justify-between w-full'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar', on_click=guardar).props('unelevated color=primary')
    dialog.open()


def open_nuevo_pago(refresh: Callable[[], None]) -> None:
    reclamos = _load_reclamos()
    if not reclamos:
        ui.notify('No hay reclamos activos para registrar un pago', type='warning')
        return
    with (
        ui.dialog() as dialog,
        ui.card().classes('w-96 max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        ui.label('Nuevo Pago').classes('text-h6')
        reclamo = ui.select(
            options=reclamos, label='Reclamo (Dominio · Póliza · Cliente · Tipo)'
        )
        fecha = ui.date(value=date.today())
        forma = ui.select(options=FORMA_PAGO_LABELS, label='Forma de Pago')
        monto = ui.number('Importe', format='%.2f', value=0).props('outlined')
        pagador = ui.select(options=AGENTE_LABELS, label='Pagador').props('outlined')
        destinatario = ui.select(options=AGENTE_LABELS, label='Destinatario').props(
            'outlined'
        )
        nota = ui.label('Nota de crédito: SOS paga a SM').classes('text-caption')
        nota.bind_visibility_from(
            forma, 'value', lambda v: v == FormaPagoEnum.NOTA_DE_CREDITO
        )
        pagador.bind_visibility_from(
            forma, 'value', lambda v: v != FormaPagoEnum.NOTA_DE_CREDITO
        )
        destinatario.bind_visibility_from(
            forma, 'value', lambda v: v != FormaPagoEnum.NOTA_DE_CREDITO
        )
        error = ui.label('').classes('text-negative')

        def guardar() -> None:
            error.set_text('')
            if reclamo.value is None or forma.value is None:
                error.set_text('Reclamo y Forma de Pago son obligatorios')
                return
            es_nc = forma.value == FormaPagoEnum.NOTA_DE_CREDITO
            data = PagoCreate(
                reclamo_id=reclamo.value,
                fecha_pago=fecha.value,
                forma_pago=forma.value,
                monto=float(monto.value),
                pagador=AgenteEnum.SOS if es_nc else pagador.value,
                destinatario=AgenteEnum.SM if es_nc else destinatario.value,
            )
            try:
                with uow_per_request() as uow:
                    PagoNuevo(uow)(data)
            except DomainError as exc:
                error.set_text(str(exc))
                return
            except ValidationError as exc:
                error.set_text(_validation_text(exc))
                return
            dialog.close()
            refresh()

        with ui.row().classes('justify-between w-full'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar', on_click=guardar).props('unelevated color=primary')
    dialog.open()


def open_nuevo_lote_tres_arr(
    refresh: Callable[[], None], user: User | None = None
) -> None:
    """Open the batch dialog for Tres Arroyos lots (grupo + gestiones)."""
    gestiones: list[dict[str, Any]] = []
    archivos: list[dict[str, Any]] = []
    generar_pagos: ui.checkbox | None = None

    def _render_pendientes() -> None:
        pending_container.clear()
        if not gestiones:
            with pending_container:
                ui.label('Sin gestiones cargadas').classes('text-caption')
            return
        with pending_container:
            table = ui.table(
                columns=[
                    {'name': 'cliente', 'label': 'Cliente', 'field': 'cliente'},
                    {'name': 'dominio', 'label': 'Dominio', 'field': 'dominio'},
                    {'name': 'poliza', 'label': 'Póliza', 'field': 'poliza'},
                    {
                        'name': 'importe',
                        'label': 'Importe',
                        'field': 'importe',
                        'align': 'right',
                    },
                    {
                        'name': 'documentos',
                        'label': 'N° docs',
                        'field': 'documentos',
                        'align': 'center',
                    },
                    {
                        'name': 'quitar',
                        'label': '',
                        'field': 'quitar',
                        'align': 'center',
                    },
                ],
                rows=[
                    {
                        'idx': idx,
                        'cliente': gest['cliente'] or '—',
                        'dominio': gest['dominio'] or '—',
                        'poliza': gest['poliza'] or '—',
                        'importe': format_money(gest['importe']),
                        'documentos': len(gest['documentos']),
                    }
                    for idx, gest in enumerate(gestiones)
                ],
                row_key='idx',
            ).classes('w-full')
            with table.add_slot('body-cell-quitar'), table.cell('quitar'):
                ui.button(icon='delete').props('flat dense').on(
                    'click',
                    js_handler='() => emit(props.row)',
                    handler=_on_quitar,
                )

    def _on_quitar(e: events.GenericEventArguments) -> None:
        args = cast(dict[str, Any], e.args)
        idx = int(args.get('idx', -1))
        if 0 <= idx < len(gestiones):
            gestiones.pop(idx)
        _render_pendientes()

    def _agregar_gestion() -> None:
        error.set_text('')
        cliente_val = _text(cliente.value)
        dominio_val = _text(dominio.value)
        if not cliente_val and not dominio_val:
            error.set_text('Complete al menos Cliente o Dominio')
            return
        gestiones.append(
            {
                'cliente': cliente_val,
                'dominio': dominio_val or '',
                'poliza': _text(poliza.value) or '',
                'importe': float(importe.value or 0.0),
                'comentario': _text(comentario.value),
                'documentos': list(archivos),
            }
        )
        archivos.clear()
        cliente.set_value('')
        poliza.set_value('')
        dominio.set_value('')
        importe.set_value(0)
        comentario.set_value('')
        upload.reset()
        _render_pendientes()

    def _pagar_todas() -> None:
        """Set importes on gestiones without one so all end up paid on save."""
        sin_importe = [
            gest for gest in gestiones if float(gest.get('importe') or 0.0) <= 0
        ]
        if not gestiones:
            error.set_text('Debe cargar al menos una gestión')
            return
        if not sin_importe:
            ui.notify(
                'Todas las gestiones ya tienen importe: se pagarán al guardar',
                type='info',
            )
            return
        if generar_pagos is not None:
            generar_pagos.set_value(True)
        with (
            ui.dialog() as dialog,
            ui.card().classes('w-[32rem] max-w-full'),
            ui.column().classes('gap-2 w-full'),
        ):
            ui.label('Pagar todas juntas').classes('text-h6')
            ui.label(
                'Cargá el importe de las gestiones sin monto; '
                'todas quedarán pagadas (SM → Prestador) al guardar.'
            ).classes('text-caption')
            campos: list[ui.number] = []
            for gest in sin_importe:
                label = f'{gest.get("cliente") or gest.get("dominio") or "Gestión"}'
                campo = ui.number(f'{label} — Importe', format='%.2f', value=0).props(
                    'outlined'
                )
                campos.append(campo)

            def _aplicar_importes() -> None:
                for gest, campo in zip(sin_importe, campos, strict=True):
                    gest['importe'] = float(campo.value or 0.0)
                dialog.close()
                _render_pendientes()
                ui.notify(
                    'Importes cargados: al guardar, todas las gestiones se pagan',
                    type='positive',
                )

            with ui.row().classes('justify-between w-full'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Aplicar', on_click=_aplicar_importes).props(
                    'unelevated color=primary'
                )
        dialog.open()

    with (
        ui.dialog() as dialog,
        ui.card().classes('w-[42rem] max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        ui.label('Nuevo Lote 3 Arroyos').classes('text-h6')
        grupo = ui.input('Grupo (lote)').props('outlined')
        generar_pagos = ui.checkbox(
            'Generar pagos (SM → Prestador por transferencia)',
            value=True,
        )
        ui.label('Gestiones').classes('text-subtitle1')
        with ui.grid(columns=2).classes('gap-4 w-full'):
            cliente = ui.input('Cliente').props('outlined')
            poliza = ui.input('Póliza').props('outlined')
            dominio = ui.input('Dominio').props('outlined')
            importe = ui.number('Importe Reclamado', format='%.2f', value=0).props(
                'outlined'
            )
            comentario = ui.textarea('Comentario').props('outlined rows=2')

        async def _on_upload(e: events.UploadEventArguments) -> None:
            contenido = await e.file.read()
            archivos.append(
                {
                    'nombre': e.file.name,
                    'mime': e.file.content_type or '',
                    'contenido': contenido,
                }
            )

        upload = ui.upload(
            label='Documentos de la gestión (se adjuntan al lote)',
            auto_upload=True,
            multiple=True,
            on_upload=_on_upload,
        ).props('accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xlsx"')

        ui.button(
            'Agregar gestión',
            icon='playlist_add',
            on_click=_agregar_gestion,
        ).props('unelevated color=primary')
        pending_container = ui.column().classes('gap-1 w-full')
        _render_pendientes()

        error = ui.label('').classes('text-negative')

        def guardar() -> None:
            error.set_text('')
            grupo_nombre = _text(grupo.value)
            if not grupo_nombre:
                error.set_text('El grupo es obligatorio')
                return
            if not gestiones:
                error.set_text('Debe cargar al menos una gestión')
                return
            items = [
                GestionLoteItem(
                    reclamo=ReclamoCreate(
                        tipo_reclamo=TipoReclamoEnum.TRESA,
                        cliente=gest['cliente'],
                        poliza=gest['poliza'] or '',
                        dominio=gest['dominio'] or '',
                        importe_reclamado=gest['importe'],
                        comentario=gest['comentario'],
                    ),
                    documentos=[
                        DocumentoCreate(
                            document_hash=_file_hash(file['contenido']),
                            tipo='adjunto',
                            nombre=file['nombre'],
                            contenido=file['contenido'],
                            tamanio=len(file['contenido']),
                            mime=file['mime'],
                        )
                        for file in gest['documentos']
                    ],
                )
                for gest in gestiones
            ]
            data = LoteTresArrCreate(
                grupo=grupo_nombre,
                usuario_creacion=user.username if user is not None else None,
                gestiones=items,
                generar_pagos=generar_pagos.value
                if generar_pagos is not None
                else True,
            )
            try:
                with uow_per_request() as uow:
                    result = LoteTresArrNuevo(uow)(data)
            except DomainError as exc:
                error.set_text(str(exc))
                return
            except ValidationError as exc:
                error.set_text(_validation_text(exc))
                return
            dialog.close()
            partes = [
                f'{result.gestiones_creadas} gestiones',
                f'{result.pagos_creados} pagos',
                f'{result.documentos_adjuntados} documentos',
            ]
            if result.gestiones_sin_pago:
                partes.append(f'{result.gestiones_sin_pago} sin pago')
            ui.notify('Lote guardado: ' + ', '.join(partes), type='positive')
            refresh()

        with ui.row().classes('justify-between w-full'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            with ui.row().classes('gap-2'):
                ui.button(
                    'Pagar todas juntas',
                    icon='payments',
                    on_click=_pagar_todas,
                ).props('flat color=primary')
                ui.button('Guardar lote', on_click=guardar).props(
                    'unelevated color=primary'
                )
    dialog.open()


def open_nuevo_ciclo(refresh: Callable[[], None]) -> None:
    with (
        ui.dialog() as dialog,
        ui.card().classes('w-96 max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        ui.label('Nuevo Ciclo').classes('text-h6')
        today = date.today()
        anio = ui.number('Año', value=today.year).props('outlined')
        mes = ui.number('Mes', value=today.month).props('outlined')
        nombre_corto = ui.input('Nombre Corto (opcional)').props('outlined')
        error = ui.label('').classes('text-negative')

        def guardar() -> None:
            error.set_text('')
            try:
                with uow_per_request() as uow:
                    PeriodoNuevo(uow)(
                        PeriodoCreate(
                            anio=int(anio.value),
                            mes=int(mes.value),
                            nombre_corto=nombre_corto.value or None,
                        )
                    )
            except DomainError as exc:
                error.set_text(str(exc))
                return
            except ValidationError as exc:
                error.set_text('Datos inválidos: ' + str(exc))
                return
            dialog.close()
            refresh()

        with ui.row().classes('justify-between w-full'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar', on_click=guardar).props('unelevated color=primary')
    dialog.open()


def open_importar_sos(refresh: Callable[[], None]) -> None:
    """Dialog to import SOS reclamos from the Excel file (upsert por N° Gestión)."""
    state: dict[str, bytes | None] = {'contenido': None}

    def _preview(contenido: bytes) -> ImportExcelSosReport:
        with uow_per_request() as uow:
            return importar_excel_sos(contenido=contenido, uow=uow, dry_run=True)

    def _importar_excel(contenido: bytes) -> ImportExcelSosReport:
        with uow_per_request() as uow:
            return importar_excel_sos(contenido=contenido, uow=uow)

    def _render_errores(errores: list[str]) -> None:
        errores_container.clear()
        if len(errores) > MAX_ERRORS_SHOWN:
            errores_container.classes(add='max-h-[10rem] overflow-auto')
        else:
            errores_container.classes(remove='max-h-[10rem] overflow-auto')
        if not errores:
            return
        with errores_container:
            for mensaje in errores[:MAX_ERRORS_SHOWN]:
                ui.label(mensaje).classes('text-negative text-caption')
            if len(errores) > MAX_ERRORS_SHOWN:
                rest = len(errores) - MAX_ERRORS_SHOWN
                ui.label(f'... y {rest} errores más.').classes('text-caption')

    with (
        ui.dialog() as dialog,
        ui.card().classes('w-[38rem] max-w-full'),
        ui.column().classes('gap-2 w-full'),
    ):
        ui.label('Importar SOS desde Excel').classes('text-h6')
        ui.label(
            'Seleccioná el archivo Gestión Reclamos Y Reintegros.xlsx '
            '(upsert por N° Gestión)'
        ).classes('text-caption')

        async def _handle_upload(e: events.UploadEventArguments) -> None:
            contenido = await e.file.read()
            state['contenido'] = contenido
            filename.set_text(f'Archivo: {e.file.name}')
            error.set_text('')
            import_button.set_enabled(False)
            try:
                report = await run.io_bound(_preview, contenido)
            except ValueError as exc:
                error.set_text(str(exc))
                preview.set_text('')
                _render_errores([])
                return
            preview.set_text(
                f'{report.creados} para crear, {report.actualizados} para actualizar'
            )
            _render_errores(report.errores)
            import_button.set_enabled(True)

        upload = ui.upload(
            label='Seleccionar archivo .xlsx',
            auto_upload=True,
            on_upload=_handle_upload,
        ).props('accept=".xlsx"')

        filename = ui.label('').classes('text-caption text-grey-7')
        preview = ui.label('').classes('text-caption')
        error = ui.label('').classes('text-negative')
        errores_container = ui.column().classes('gap-0 w-full')

        async def _run_import() -> None:
            contenido = state['contenido']
            if contenido is None:
                ui.notify('Seleccioná un archivo .xlsx primero', type='warning')
                return
            import_button.set_enabled(False)
            upload.set_enabled(False)
            try:
                report = await run.io_bound(_importar_excel, contenido)
            except Exception as exc:
                ui.notify(f'Error al importar: {exc}', type='negative')
                upload.set_enabled(True)
                import_button.set_enabled(True)
                return
            dialog.close()
            partes = [
                f'{report.creados} creados',
                f'{report.actualizados} actualizados',
            ]
            if report.errores:
                partes.append(f'{len(report.errores)} errores')
            ui.notify('Importación finalizada: ' + ', '.join(partes), type='positive')
            refresh()

        import_button = ui.button(
            'Importar',
            icon='upload',
            on_click=_run_import,
        ).props('unelevated color=primary')
        import_button.set_enabled(False)

        ui.button('Cancelar', on_click=dialog.close).props('flat')
    dialog.open()
