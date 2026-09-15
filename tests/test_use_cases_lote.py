"""Tests for the Tres Arroyos lot use case (grupo + gestiones + pagos)."""

import hashlib

import pytest

from src.application.use_cases.documento import DocumentoListarPorEntidad
from src.application.use_cases.lote import LoteTresArrNuevo
from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)
from src.domain.dto.create import (
    DocumentoCreate,
    GestionLoteItem,
    LoteTresArrCreate,
    ReclamoCreate,
)
from src.domain.exceptions import DomainError
from src.domain.models.entities import Grupo
from tests.fakes.unit_of_work import FakeUnitOfWork


def _reclamo_data(**overrides: object) -> ReclamoCreate:
    values: dict[str, object] = {
        'cliente': 'ACME',
        'poliza': 'P-001',
        'dominio': 'AB123CD',
        'importe_reclamado': 15000.0,
        'comentario': 'sin novedades',
    }
    values.update(overrides)
    return ReclamoCreate(**values)


def _documento(nombre: str, contenido: bytes) -> DocumentoCreate:
    return DocumentoCreate(
        document_hash=hashlib.sha256(contenido).hexdigest(),
        tipo='adjunto',
        nombre=nombre,
        contenido=contenido,
        tamanio=len(contenido),
        mime='application/pdf',
    )


def test_lote_crea_grupo_gestiones_pagos_y_documentos() -> None:
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Julio',
            usuario_creacion='admin',
            gestiones=[
                GestionLoteItem(
                    reclamo=_reclamo_data(importe_reclamado=500.0),
                    documentos=[_documento('poliza.pdf', b'pdf-data')],
                ),
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='ZZ999AA', importe_reclamado=0.0)
                ),
            ],
        )
        result = LoteTresArrNuevo(uow)(data)

        grupo = uow.grupos.get_by_nombre('LOTE JULIO')
        assert grupo is not None
        assert grupo.id == result.grupo_id
        assert grupo.usuario_creacion == 'admin'
        assert result.grupo == 'LOTE JULIO'
        assert result.gestiones_creadas == 2
        assert result.pagos_creados == 1
        assert result.documentos_adjuntados == 1
        assert result.gestiones_sin_pago == 1
        assert uow.committed is True

        tres_arr = list(uow.tres_arr._store.values())
        assert len(tres_arr) == 2
        assert all(t.grupo_id == grupo.id for t in tres_arr)
        assert all(t.grupo == 'LOTE JULIO' for t in tres_arr)

        reclamos = list(uow.reclamos._store.values())
        assert len(reclamos) == 2
        assert all(r.tipo_reclamo == TipoReclamoEnum.TRESA for r in reclamos)
        assert all(r.active is True for r in reclamos)

        pagos = list(uow.pagos._store.values())
        assert len(pagos) == 1
        pago = pagos[0]
        assert pago.pagador == AgenteEnum.SM
        assert pago.destinatario == AgenteEnum.PRESTADOR
        assert pago.forma_pago == FormaPagoEnum.TRANSFERENCIA
        assert pago.monto == 500.0

        entidades = uow.entidad_documentos.list()
        assert len(entidades) == 1
        assert entidades[0].tipo_entidad == TipoEntidadEnum.RECLAMO
        assert entidades[0].entidad_id == reclamos[0].id


def test_lote_rechaza_grupo_existente() -> None:
    with FakeUnitOfWork() as uow:
        uow.grupos.save(Grupo(grupo='Lote Viejo'))
        data = LoteTresArrCreate(
            grupo='Lote Viejo',
            gestiones=[GestionLoteItem(reclamo=_reclamo_data())],
        )
        with pytest.raises(DomainError, match="el grupo 'LOTE VIEJO' ya existe"):
            LoteTresArrNuevo(uow)(data)


def test_lote_rechaza_sin_gestiones() -> None:
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(grupo='Lote Vacio', gestiones=[])
        with pytest.raises(DomainError, match='al menos una gestión'):
            LoteTresArrNuevo(uow)(data)


def test_lote_rechaza_grupo_vacio() -> None:
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='   ',
            gestiones=[GestionLoteItem(reclamo=_reclamo_data())],
        )
        with pytest.raises(DomainError, match='El grupo es obligatorio'):
            LoteTresArrNuevo(uow)(data)


def test_lote_genera_pago_solo_si_importe_mayor_cero() -> None:
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Pagos',
            gestiones=[
                GestionLoteItem(reclamo=_reclamo_data(importe_reclamado=100.0)),
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='YY111BB', importe_reclamado=0.0)
                ),
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='XX222CC', importe_reclamado=250.0)
                ),
            ],
        )
        result = LoteTresArrNuevo(uow)(data)

        assert result.pagos_creados == 2
        assert result.gestiones_sin_pago == 1
        pagos = list(uow.pagos._store.values())
        assert len(pagos) == 2
        assert sorted(p.monto for p in pagos) == [100.0, 250.0]


def test_lote_sin_pagos_cuando_generar_pagos_false() -> None:
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Sin Pagos',
            generar_pagos=False,
            gestiones=[
                GestionLoteItem(reclamo=_reclamo_data(importe_reclamado=500.0)),
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='WW333DD', importe_reclamado=250.0)
                ),
            ],
        )
        result = LoteTresArrNuevo(uow)(data)

        assert result.pagos_creados == 0
        assert result.gestiones_sin_pago == 2
        assert list(uow.pagos._store.values()) == []
        tres_arr = list(uow.tres_arr._store.values())
        assert len(tres_arr) == 2
        grupo = uow.grupos.get_by_nombre('LOTE SIN PAGOS')
        assert grupo is not None
        assert all(t.grupo_id == grupo.id for t in tres_arr)


def test_lote_create_acepta_documentos_de_grupo() -> None:
    """LoteTresArrCreate carries group-level documents separately."""
    doc = _documento('grupo.pdf', b'grupo-bytes')
    data = LoteTresArrCreate(
        grupo='Lote DTO',
        documentos=[doc],
        gestiones=[GestionLoteItem(reclamo=_reclamo_data())],
    )
    assert data.documentos == [doc]


def test_lote_documento_de_grupo_vincula_grupo_y_cada_reclamo() -> None:
    """A group document links to the GRUPO and to every gestión's reclamo."""
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Grupo Doc',
            documentos=[_documento('grupo.pdf', b'grupo-bytes')],
            gestiones=[
                GestionLoteItem(reclamo=_reclamo_data(dominio='AA111AA')),
                GestionLoteItem(reclamo=_reclamo_data(dominio='BB222BB')),
                GestionLoteItem(reclamo=_reclamo_data(dominio='CC333CC')),
            ],
        )
        result = LoteTresArrNuevo(uow)(data)

        grupo = uow.grupos.get_by_nombre('LOTE GRUPO DOC')
        assert grupo is not None
        assert grupo.id is not None
        docs_grupo = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.GRUPO, grupo.id)
        assert [d.nombre for d in docs_grupo] == ['grupo.pdf']

        reclamos = list(uow.reclamos._store.values())
        assert len(reclamos) == 3
        for reclamo in reclamos:
            assert reclamo.id is not None
            docs = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.RECLAMO, reclamo.id)
            assert [d.nombre for d in docs] == ['grupo.pdf']

        assert len(uow.documentos.list()) == 1
        assert len(uow.entidad_documentos.list()) == 4
        assert result.documentos_adjuntados == 1
        assert uow.committed is True


def test_lote_documento_compartido_entre_gestiones_crea_un_documento_y_dos_vinculos() -> (
    None
):
    """Same content in two gestiones: one Documento row, one link per reclamo."""
    compartido = _documento('compartido.pdf', b'contenido-compartido')
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Compartido',
            gestiones=[
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='AA111AA'),
                    documentos=[compartido],
                ),
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='BB222BB'),
                    documentos=[compartido],
                ),
            ],
        )
        result = LoteTresArrNuevo(uow)(data)

        assert len(uow.documentos.list()) == 1
        vinculos = uow.entidad_documentos.list()
        assert len(vinculos) == 2
        assert {v.tipo_entidad for v in vinculos} == {TipoEntidadEnum.RECLAMO}
        reclamos = list(uow.reclamos._store.values())
        assert {v.entidad_id for v in vinculos} == {r.id for r in reclamos}
        assert result.documentos_adjuntados == 1
        assert uow.committed is True


def test_lote_documento_por_gestion_solo_visible_en_su_reclamo() -> None:
    """A per-gestión document is not visible on the GRUPO or other gestiones."""
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Aislado',
            gestiones=[
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='AA111AA'),
                    documentos=[_documento('a.pdf', b'bytes-a')],
                ),
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='BB222BB'),
                    documentos=[_documento('b.pdf', b'bytes-b')],
                ),
            ],
        )
        LoteTresArrNuevo(uow)(data)

        grupo = uow.grupos.get_by_nombre('LOTE AISLADO')
        assert grupo is not None
        assert grupo.id is not None
        reclamos = sorted(uow.reclamos._store.values(), key=lambda r: r.id or 0)
        reclamo_a, reclamo_b = reclamos
        assert reclamo_a.id is not None
        assert reclamo_b.id is not None

        docs_a = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.RECLAMO, reclamo_a.id)
        docs_b = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.RECLAMO, reclamo_b.id)
        assert [d.nombre for d in docs_a] == ['a.pdf']
        assert [d.nombre for d in docs_b] == ['b.pdf']
        assert DocumentoListarPorEntidad(uow)(TipoEntidadEnum.GRUPO, grupo.id) == []


def test_lote_mezcla_documento_de_grupo_y_por_gestion() -> None:
    """Group and per-gestión documents coexist with the right visibility."""
    with FakeUnitOfWork() as uow:
        data = LoteTresArrCreate(
            grupo='Lote Mixto',
            documentos=[_documento('grupo.pdf', b'g')],
            gestiones=[
                GestionLoteItem(
                    reclamo=_reclamo_data(dominio='AA111AA'),
                    documentos=[_documento('gestion.pdf', b'x')],
                ),
            ],
        )
        result = LoteTresArrNuevo(uow)(data)

        grupo = uow.grupos.get_by_nombre('LOTE MIXTO')
        assert grupo is not None
        assert grupo.id is not None
        reclamo = next(iter(uow.reclamos._store.values()))
        assert reclamo.id is not None

        docs_grupo = DocumentoListarPorEntidad(uow)(TipoEntidadEnum.GRUPO, grupo.id)
        docs_reclamo = DocumentoListarPorEntidad(uow)(
            TipoEntidadEnum.RECLAMO, reclamo.id
        )
        assert [d.nombre for d in docs_grupo] == ['grupo.pdf']
        assert {d.nombre for d in docs_reclamo} == {'grupo.pdf', 'gestion.pdf'}
        assert len(uow.documentos.list()) == 2
        assert len(uow.entidad_documentos.list()) == 3
        assert result.documentos_adjuntados == 2
