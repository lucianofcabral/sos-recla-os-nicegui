"""Query (read-model) tests against in-memory SQLite."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoReclamoEnum,
)
from src.domain.dto.read import ReclamoHomeFilter
from src.domain.models.entities import (
    CreditNote,
    Factura,
    Grupo,
    Pago,
    Periodo,
    Reclamo,
    ReclamoSos,
    TresArrReclamo,
)
from src.infrastructure.database import create_schema
from src.infrastructure.unit_of_work import SqlModelUnitOfWork


@pytest.fixture()
def engine():
    eng = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    create_schema(eng)
    return eng


def _seed(engine) -> None:
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        periodo = uow.periodos.save(
            Periodo(anio=2026, mes=6, anio_mes=202606, nombre_corto='06/2026')
        )
        assert periodo.id is not None
        reclamo = uow.reclamos.save(
            Reclamo(
                cliente='ACME',
                poliza='P-001',
                dominio='AB123CD',
                importe_reclamado=15000.0,
            )
        )
        assert reclamo.id is not None
        uow.reclamos_sos.save(ReclamoSos(reclamo_id=reclamo.id, nro_gestion=1001))
        uow.pagos.save(
            Pago(
                reclamo_id=reclamo.id,
                forma_pago=FormaPagoEnum.TRANSFERENCIA,
                pagador=AgenteEnum.ASEGURADO,
                destinatario=AgenteEnum.PRESTADOR,
                monto=8000.0,
            )
        )
        pago_nc = uow.pagos.save(
            Pago(
                reclamo_id=reclamo.id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=5000.0,
            )
        )
        assert pago_nc.id is not None
        uow.credit_notes.save(CreditNote(pago_id=pago_nc.id, periodo_id=periodo.id))
        uow.facturas.save(
            Factura(periodo_id=periodo.id, nro_factura='A-0001', importe=3000.5)
        )
        uow.commit()


def test_sql_home_listing(engine) -> None:
    _seed(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        items = uow.list_home()
    assert len(items) == 1
    item = items[0]
    assert item.cliente == 'ACME'
    assert item.poliza == 'P-001'
    assert item.dominio == 'AB123CD'
    assert item.importe_reclamado == 15000.0
    assert item.active is True
    assert item.nro_gestion == 1001
    assert item.has_pagos is True
    assert item.has_credit_note is True


def test_sql_home_includes_inactive(engine) -> None:
    _seed(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        saved = uow.reclamos.save(
            Reclamo(cliente='OTRO', poliza='P-002', dominio='XX999')
        )
        assert saved.id is not None
        uow.reclamos.set_active(saved.id, False)
        uow.commit()
        items = uow.list_home()
    assert len(items) == 2
    plain = next(i for i in items if i.reclamo_id == saved.id)
    assert plain.active is False
    assert plain.nro_gestion is None
    assert plain.has_pagos is False
    assert plain.has_credit_note is False


def test_sql_pagos_con_detalle(engine) -> None:
    _seed(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        items = uow.list_pagos_con_detalle()
    assert len(items) == 2
    for item in items:
        assert item.dominio == 'AB123CD'
        assert item.poliza == 'P-001'
        assert item.cliente == 'ACME'
        assert item.nro_gestion == 1001
    assert items[0].forma_pago == FormaPagoEnum.TRANSFERENCIA
    assert items[0].monto == 8000.0
    assert items[1].forma_pago == FormaPagoEnum.NOTA_DE_CREDITO
    assert items[1].monto == 5000.0


def test_sql_ciclos(engine) -> None:
    _seed(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        cards = uow.list_ciclos()
    assert len(cards) == 1
    card = cards[0]
    assert card.nombre_corto == '06/2026'
    assert card.anio_mes == 202606
    assert card.cant_documentos == 0
    assert card.suma_importe_facturas == 3000.5
    assert card.cant_notas_credito == 1
    assert card.suma_importe_notas_credito == 5000.0


def _seed_filtros(engine) -> None:
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        r_sos = uow.reclamos.save(
            Reclamo(
                tipo_reclamo=TipoReclamoEnum.SOS,
                cliente='ACME',
                poliza='P-001',
                dominio='AB123CD',
                importe_reclamado=15000.0,
                created_at=datetime(2026, 5, 10, 10, 0),
            )
        )
        assert r_sos.id is not None
        uow.reclamos_sos.save(ReclamoSos(reclamo_id=r_sos.id, nro_gestion=1001))
        for forma, monto in (
            (FormaPagoEnum.TRANSFERENCIA, 8000.0),
            (FormaPagoEnum.NOTA_DE_CREDITO, 4000.0),
        ):
            uow.pagos.save(
                Pago(
                    reclamo_id=r_sos.id,
                    forma_pago=forma,
                    pagador=AgenteEnum.ASEGURADO,
                    destinatario=AgenteEnum.PRESTADOR,
                    monto=monto,
                )
            )
        r_tresa = uow.reclamos.save(
            Reclamo(
                tipo_reclamo=TipoReclamoEnum.TRESA,
                cliente='OTRO',
                poliza='P-002',
                dominio='CD456EF',
                importe_reclamado=500.0,
                created_at=datetime(2026, 6, 15, 9, 30),
            )
        )
        assert r_tresa.id is not None
        grupo_norte = uow.grupos.save(Grupo(grupo='Grupo Norte'))
        assert grupo_norte.id is not None
        uow.tres_arr.save(
            TresArrReclamo(
                reclamo_id=r_tresa.id,
                grupo='Grupo Norte',
                grupo_id=grupo_norte.id,
            )
        )
        uow.pagos.save(
            Pago(
                reclamo_id=r_tresa.id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=500.0,
            )
        )
        r_tresa2 = uow.reclamos.save(
            Reclamo(
                tipo_reclamo=TipoReclamoEnum.TRESA,
                cliente='SUR',
                poliza='P-003',
                dominio='SR111TT',
                importe_reclamado=700.0,
                created_at=datetime(2026, 7, 1, 8, 0),
            )
        )
        assert r_tresa2.id is not None
        grupo_sur = uow.grupos.save(Grupo(grupo='Grupo Sur'))
        assert grupo_sur.id is not None
        uow.tres_arr.save(
            TresArrReclamo(
                reclamo_id=r_tresa2.id,
                grupo='Grupo Sur',
                grupo_id=grupo_sur.id,
            )
        )
        r_otros = uow.reclamos.save(
            Reclamo(
                tipo_reclamo=TipoReclamoEnum.OTROS,
                cliente='GEST',
                poliza='G-001',
                dominio='ZZ999',
                importe_reclamado=2000.0,
                created_at=datetime(2026, 7, 20, 15, 0),
            )
        )
        assert r_otros.id is not None
        uow.commit()


def test_sql_home_filtro_combinado(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        items = uow.list_home(
            ReclamoHomeFilter(
                tipo_reclamo=TipoReclamoEnum.TRESA, con_pagos=True, texto='cd45'
            )
        )
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'


def test_sql_home_filtro_tipo_y_con_pagos(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        sin_pagos = uow.list_home(
            ReclamoHomeFilter(tipo_reclamo=TipoReclamoEnum.SOS, con_pagos=False)
        )
        tresa_sin_pagos = uow.list_home(
            ReclamoHomeFilter(tipo_reclamo=TipoReclamoEnum.TRESA, con_pagos=False)
        )
    assert sin_pagos == []
    assert {item.dominio for item in tresa_sin_pagos} == {'SR111TT'}


def test_sql_home_filtro_importe(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        items = uow.list_home(
            ReclamoHomeFilter(importe_min=2000.0, importe_max=15000.0)
        )
    assert len(items) == 2
    assert {item.dominio for item in items} == {'AB123CD', 'ZZ999'}


def test_sql_home_filtro_fechas(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        items = uow.list_home(
            ReclamoHomeFilter(
                fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 30)
            )
        )
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'


def test_sql_home_filtro_con_nota_credito(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        con_nc = uow.list_home(ReclamoHomeFilter(con_nota_credito=True))
        sin_nc = uow.list_home(ReclamoHomeFilter(con_nota_credito=False))
    assert {item.dominio for item in con_nc} == {'AB123CD', 'CD456EF'}
    assert {item.dominio for item in sin_nc} == {'SR111TT', 'ZZ999'}


def test_sql_home_filtro_active(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        saved = uow.reclamos.save(
            Reclamo(cliente='INACTIVO', poliza='P-004', dominio='II222')
        )
        assert saved.id is not None
        uow.reclamos.set_active(saved.id, False)
        uow.commit()
        activos = uow.list_home(ReclamoHomeFilter(active=True))
        inactivos = uow.list_home(ReclamoHomeFilter(active=False))
    assert {item.dominio for item in activos} == {
        'AB123CD',
        'CD456EF',
        'SR111TT',
        'ZZ999',
    }
    assert [item.dominio for item in inactivos] == ['II222']


def test_sql_list_grupos_distinct(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        grupos = uow.list_grupos()
    assert grupos == ['GRUPO NORTE', 'GRUPO SUR']


def test_sql_home_filtro_grupo(engine) -> None:
    _seed_filtros(engine)
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        items = uow.list_home(ReclamoHomeFilter(grupo='GRUPO NORTE'))
        vacio = uow.list_home(ReclamoHomeFilter(grupo='No Existe'))
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'
    assert vacio == []


def test_sql_home_orden_fecha_desc(engine) -> None:
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        viejo = uow.reclamos.save(
            Reclamo(
                cliente='VIEJO',
                poliza='P-010',
                dominio='AA100',
                created_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        medio = uow.reclamos.save(
            Reclamo(
                cliente='MEDIO',
                poliza='P-011',
                dominio='BB200',
                created_at=datetime(2026, 4, 15, 12, 0),
            )
        )
        nuevo = uow.reclamos.save(
            Reclamo(
                cliente='NUEVO',
                poliza='P-012',
                dominio='CC300',
                created_at=datetime(2026, 7, 20, 15, 0),
            )
        )
        assert viejo.id is not None
        assert medio.id is not None
        assert nuevo.id is not None
        uow.commit()
        items = uow.list_home()
    assert [item.dominio for item in items] == ['CC300', 'BB200', 'AA100']
