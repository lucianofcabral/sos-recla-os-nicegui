"""Headless render test of the shared document section.

Mounts ``seccion_documentos`` as the app root through the NiceGUI test
simulation and asserts the attached document is visible in the rendered
list. Runs in a plain sync test through ``asyncio.run`` to avoid needing
pytest-asyncio/anyio. Restores the NiceGUI global client registry
afterwards so tests that rely on the auto-created pseudo client keep
working.
"""

from __future__ import annotations

import asyncio

from nicegui.client import Client
from nicegui.testing.user_simulation import user_simulation

from src.domain.domain_enums import TipoEntidadEnum
from src.domain.models.entities import Documento, EntidadDocumento, Grupo, Reclamo
from src.ui import dialogos
from tests.fakes.unit_of_work import FakeUnitOfWork


def _uow_con_documento() -> tuple[FakeUnitOfWork, int]:
    uow = FakeUnitOfWork()
    reclamo = uow.reclamos.save(
        Reclamo(cliente='ACME', poliza='P-001', dominio='AB123CD')
    )
    assert reclamo.id is not None
    doc = uow.documentos.save(
        Documento(
            document_hash='a' * 64,
            tipo='adjunto',
            nombre='factura.pdf',
            contenido=b'pdf',
            tamanio=3,
            mime='application/pdf',
        )
    )
    uow.entidad_documentos.save(
        EntidadDocumento(
            document_hash=doc.document_hash,
            tipo_entidad=TipoEntidadEnum.RECLAMO,
            entidad_id=reclamo.id,
        )
    )
    return uow, reclamo.id


def test_seccion_documentos_muestra_adjuntos(monkeypatch) -> None:
    uow, reclamo_id = _uow_con_documento()
    monkeypatch.setattr(dialogos, 'uow_per_request', lambda: uow)

    def root() -> None:
        dialogos.seccion_documentos(TipoEntidadEnum.RECLAMO, reclamo_id)

    async def _correr() -> None:
        async with user_simulation(root=root) as user:
            await user.open('/')
            await user.should_see('factura.pdf')
            await user.should_not_see('Sin documentos adjuntos')

    asyncio.run(_correr())
    # user_simulation leaves a client in the global registry; remove it so
    # other tests still auto-create the pseudo client they rely on.
    Client.instances.clear()


def _uow_con_documento_de_grupo() -> tuple[FakeUnitOfWork, int]:
    uow = FakeUnitOfWork()
    grupo = uow.grupos.save(Grupo(grupo='LOTE UI'))
    assert grupo.id is not None
    doc = uow.documentos.save(
        Documento(
            document_hash='b' * 64,
            tipo='adjunto',
            nombre='grupo.pdf',
            contenido=b'pdf',
            tamanio=3,
            mime='application/pdf',
        )
    )
    uow.entidad_documentos.save(
        EntidadDocumento(
            document_hash=doc.document_hash,
            tipo_entidad=TipoEntidadEnum.GRUPO,
            entidad_id=grupo.id,
        )
    )
    return uow, grupo.id


def test_seccion_documentos_grupo_muestra_adjuntos(monkeypatch) -> None:
    """The GRUPO entity renders its attached documents like RECLAMO/PERIODO."""
    uow, grupo_id = _uow_con_documento_de_grupo()
    monkeypatch.setattr(dialogos, 'uow_per_request', lambda: uow)

    def root() -> None:
        dialogos.seccion_documentos(TipoEntidadEnum.GRUPO, grupo_id)

    async def _correr() -> None:
        async with user_simulation(root=root) as user:
            await user.open('/')
            await user.should_see('grupo.pdf')
            await user.should_not_see('Sin documentos adjuntos')

    asyncio.run(_correr())
    Client.instances.clear()


def test_dialogo_grupo_muestra_seccion_documentos(monkeypatch) -> None:
    """The group dialog exposes attach + list of GRUPO documents."""
    uow, grupo_id = _uow_con_documento_de_grupo()
    monkeypatch.setattr(dialogos, 'uow_per_request', lambda: uow)

    def root() -> None:
        dialogos.open_grupo_tres_arr(grupo_id, lambda: None)

    async def _correr() -> None:
        async with user_simulation(root=root) as user:
            await user.open('/')
            await user.should_see('grupo.pdf')
            await user.should_see('Adjuntar documentos')

    asyncio.run(_correr())
    Client.instances.clear()
