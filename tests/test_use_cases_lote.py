"""Tests for the Tres Arroyos lot use case (grupo + gestiones + pagos)."""

import hashlib

import pytest

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
        assert entidades[0].tipo_entidad == TipoEntidadEnum.GRUPO
        assert entidades[0].entidad_id == grupo.id


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
