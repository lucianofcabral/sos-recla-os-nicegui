"""Tests for document attachment use cases (DocumentoAdjuntar, DocumentoEliminar, DocumentoListarPorEntidad)."""

import pytest

from src.application.use_cases.documento import (
    DocumentoAdjuntar,
    DocumentoEliminar,
    DocumentoListarPorEntidad,
)
from src.domain.domain_enums import TipoEntidadEnum
from src.domain.dto.create import DocumentoCreate
from src.domain.exceptions import DomainError
from tests.fakes.unit_of_work import FakeUnitOfWork


def _make_doccreate(**overrides) -> DocumentoCreate:
    defaults = {
        'document_hash': 'a' * 64,
        'tipo': 'adjunto',
        'nombre': 'test.pdf',
        'contenido': b'pdf-bytes',
        'tamanio': 9,
        'mime': 'application/pdf',
        'descripcion': '',
    }
    defaults.update(overrides)
    return DocumentoCreate(**defaults)


def test_adjuntar_documento_nuevo() -> None:
    uow = FakeUnitOfWork()
    doc = DocumentoAdjuntar(uow)(TipoEntidadEnum.RECLAMO, 1, _make_doccreate())
    assert doc.document_hash == 'a' * 64
    assert doc.nombre == 'test.pdf'
    found = uow.documentos.get_by_hash('a' * 64)
    assert found is not None
    vinculos = uow.entidad_documentos.list()
    assert len(vinculos) == 1
    assert vinculos[0].tipo_entidad == TipoEntidadEnum.RECLAMO
    assert vinculos[0].entidad_id == 1
    assert uow.committed is True


def test_adjuntar_mismo_hash_dos_veces_es_idempotente() -> None:
    uow = FakeUnitOfWork()
    doc_create = _make_doccreate()
    doc1 = DocumentoAdjuntar(uow)(TipoEntidadEnum.RECLAMO, 1, doc_create)
    doc2 = DocumentoAdjuntar(uow)(TipoEntidadEnum.RECLAMO, 1, doc_create)
    assert doc1.document_hash == doc2.document_hash
    found = uow.documentos.get_by_hash('a' * 64)
    assert found is not None
    vinculos = uow.entidad_documentos.list()
    assert len(vinculos) == 1


def test_adjuntar_mismo_hash_distinta_entidad_crea_vinculo() -> None:
    uow = FakeUnitOfWork()
    doc_create = _make_doccreate()
    DocumentoAdjuntar(uow)(TipoEntidadEnum.RECLAMO, 1, doc_create)
    DocumentoAdjuntar(uow)(TipoEntidadEnum.PERIODO, 2, doc_create)
    vinculos = uow.entidad_documentos.list()
    assert len(vinculos) == 2
    found = uow.documentos.get_by_hash('a' * 64)
    assert found is not None


def test_adjuntar_tipo_entidad_invalido_falla() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(DomainError):
        DocumentoAdjuntar(uow)(None, 1, _make_doccreate())


def test_eliminar_documento_borra_vinculo_y_huerfano() -> None:
    uow = FakeUnitOfWork()
    doc_create = _make_doccreate()
    DocumentoAdjuntar(uow)(TipoEntidadEnum.RECLAMO, 1, doc_create)
    assert uow.documentos.get_by_hash('a' * 64) is not None
    DocumentoEliminar(uow)(TipoEntidadEnum.RECLAMO, 1, 'a' * 64)
    assert uow.documentos.get_by_hash('a' * 64) is None
    assert len(uow.entidad_documentos.list()) == 0
    assert uow.committed is True


def test_eliminar_documento_conserve_si_otro_vinculo() -> None:
    uow = FakeUnitOfWork()
    doc_create = _make_doccreate()
    DocumentoAdjuntar(uow)(TipoEntidadEnum.RECLAMO, 1, doc_create)
    DocumentoAdjuntar(uow)(TipoEntidadEnum.PERIODO, 2, doc_create)
    DocumentoEliminar(uow)(TipoEntidadEnum.RECLAMO, 1, 'a' * 64)
    assert uow.documentos.get_by_hash('a' * 64) is not None
    vinculos = uow.entidad_documentos.list()
    assert len(vinculos) == 1
    assert vinculos[0].entidad_id == 2


def test_eliminar_inexistente_no_falla() -> None:
    uow = FakeUnitOfWork()
    DocumentoEliminar(uow)(TipoEntidadEnum.RECLAMO, 1, 'f' * 64)
    assert uow.committed is True


def test_listar_por_entidad() -> None:
    uow = FakeUnitOfWork()
    DocumentoAdjuntar(uow)(
        TipoEntidadEnum.RECLAMO,
        1,
        _make_doccreate(document_hash='a' * 64, nombre='a.pdf'),
    )
    DocumentoAdjuntar(uow)(
        TipoEntidadEnum.RECLAMO,
        1,
        _make_doccreate(document_hash='b' * 64, nombre='b.pdf'),
    )
    DocumentoAdjuntar(uow)(
        TipoEntidadEnum.PERIODO,
        2,
        _make_doccreate(document_hash='c' * 64, nombre='c.pdf'),
    )
    docs = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.RECLAMO, 1)
    assert len(docs) == 2
    names = {d.nombre for d in docs}
    assert names == {'a.pdf', 'b.pdf'}


def test_listar_por_entidad_vacia() -> None:
    uow = FakeUnitOfWork()
    docs = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.RECLAMO, 1)
    assert docs == []
