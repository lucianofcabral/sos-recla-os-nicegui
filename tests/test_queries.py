"""Query (read-model) tests against the fake unit of work."""

from __future__ import annotations

from datetime import date, datetime

from src.application.queries import (
    list_ciclos,
    list_grupos,
    list_home,
    list_notas_credito_sin_asignar,
    list_pagos_con_detalle,
)
from src.application.use_cases.factura import FacturaNueva
from src.application.use_cases.nota_credito import AsignarNotaCreditoAPeriodo
from src.application.use_cases.pago import PagoNuevo
from src.application.use_cases.periodo import PeriodoCerrar, PeriodoNuevo
from src.application.use_cases.reclamo import (
    OtrosReclamoNuevo,
    SosReclamoNuevo,
    TresArrReclamoNuevo,
)
from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)
from src.domain.dto.create import (
    FacturaCreate,
    OtrosReclamoCreate,
    PagoCreate,
    PeriodoCreate,
    ReclamoCreate,
    ReclamoSosCreate,
    TresArrReclamoCreate,
)
from src.domain.dto.read import PagoListFilter, ReclamoHomeFilter
from src.domain.models.entities import Documento, EntidadDocumento
from tests.fakes.unit_of_work import FakeUnitOfWork


def _dataset() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    with uow:
        sos = SosReclamoNuevo(uow)(
            ReclamoSosCreate(
                reclamo=ReclamoCreate(
                    cliente='ACME',
                    poliza='P-001',
                    dominio='AB123CD',
                    importe_reclamado=15000.0,
                ),
                nro_gestion=1001,
            )
        )
        assert sos.reclamo_id is not None
        sos_id = sos.reclamo_id
        TresArrReclamoNuevo(uow)(
            TresArrReclamoCreate(
                reclamo=ReclamoCreate(
                    cliente='OTRO',
                    poliza='P-002',
                    dominio='XX999',
                    importe_reclamado=500.0,
                )
            )
        )
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=sos_id,
                forma_pago=FormaPagoEnum.TRANSFERENCIA,
                pagador=AgenteEnum.ASEGURADO,
                destinatario=AgenteEnum.PRESTADOR,
                monto=8000.0,
            )
        )
        pago_nc = PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=sos_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=5000.0,
            )
        )
        assert pago_nc.id is not None
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=6))
        assert periodo.id is not None
        ncs = uow.credit_notes.list_by_periodo(None)
        assert len(ncs) == 1
        assert ncs[0].id is not None
        AsignarNotaCreditoAPeriodo(uow)(ncs[0].id, periodo.id)
        FacturaNueva(uow)(
            FacturaCreate(periodo_id=periodo.id, nro_factura='A-0001', importe=3000.5)
        )
        uow.commit()
    return uow


def test_list_home_fields() -> None:
    uow = _dataset()
    items = list_home(uow)
    assert len(items) == 2
    sos_item, tresa_item = items
    assert sos_item.reclamo_id == 1
    assert sos_item.tipo_reclamo == TipoReclamoEnum.SOS
    assert sos_item.cliente == 'ACME'
    assert sos_item.poliza == 'P-001'
    assert sos_item.dominio == 'AB123CD'
    assert sos_item.importe_reclamado == 15000.0
    assert sos_item.active is True
    assert sos_item.nro_gestion == 1001
    assert sos_item.has_pagos is True
    assert sos_item.has_credit_note is True
    assert tresa_item.tipo_reclamo == TipoReclamoEnum.TRESA
    assert tresa_item.nro_gestion is None
    assert tresa_item.has_pagos is False
    assert tresa_item.has_credit_note is False


def test_list_pagos_con_detalle() -> None:
    uow = _dataset()
    items = list_pagos_con_detalle(uow)
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


def test_list_ciclos() -> None:
    uow = _dataset()
    cards = list_ciclos(uow)
    assert len(cards) == 1
    card = cards[0]
    periodo = uow.periodos.list()[0]
    assert card.periodo_id == periodo.id
    assert card.nombre_corto == '06/2026'
    assert card.anio_mes == 202606
    assert card.cant_documentos == 0
    assert card.suma_importe_facturas == 3000.5
    assert card.cant_notas_credito == 1
    assert card.suma_importe_notas_credito == 5000.0
    assert card.cerrado is False


def test_list_ciclos_cuenta_documentos() -> None:
    uow = _dataset()
    periodo = uow.periodos.list()[0]
    assert periodo.id is not None
    doc1 = uow.documentos.save(
        Documento(
            document_hash='a' * 64,
            tipo='adjunto',
            nombre='uno.pdf',
            contenido=b'one',
            tamanio=3,
            mime='application/pdf',
        )
    )
    doc2 = uow.documentos.save(
        Documento(
            document_hash='b' * 64,
            tipo='adjunto',
            nombre='dos.pdf',
            contenido=b'two',
            tamanio=3,
            mime='application/pdf',
        )
    )
    uow.entidad_documentos.save(
        EntidadDocumento(
            document_hash=doc1.document_hash,
            tipo_entidad=TipoEntidadEnum.PERIODO,
            entidad_id=periodo.id,
        )
    )
    uow.entidad_documentos.save(
        EntidadDocumento(
            document_hash=doc2.document_hash,
            tipo_entidad=TipoEntidadEnum.PERIODO,
            entidad_id=periodo.id,
        )
    )
    cards = list_ciclos(uow)
    assert len(cards) == 1
    assert cards[0].cant_documentos == 2
    assert cards[0].suma_importe_facturas == 3000.5


def test_list_ciclos_propaga_cerrado() -> None:
    uow = _dataset()
    with uow:
        periodo = uow.periodos.list()[0]
        assert periodo.id is not None
        PeriodoCerrar(uow)(periodo.id)
    cards = list_ciclos(uow)
    assert len(cards) == 1
    assert cards[0].cerrado is True


def _set_created(uow: FakeUnitOfWork, reclamo_id: int, when: datetime) -> None:
    reclamo = uow.reclamos.get(reclamo_id)
    uow.reclamos.update(reclamo.model_copy(update={'created_at': when}))


def _dataset_filtros() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    with uow:
        sos = SosReclamoNuevo(uow)(
            ReclamoSosCreate(
                reclamo=ReclamoCreate(
                    cliente='ACME',
                    poliza='P-001',
                    dominio='AB123CD',
                    importe_reclamado=15000.0,
                ),
                nro_gestion=1001,
            )
        )
        tresa = TresArrReclamoNuevo(uow)(
            TresArrReclamoCreate(
                reclamo=ReclamoCreate(
                    cliente='OTRO',
                    poliza='P-002',
                    dominio='CD456EF',
                    importe_reclamado=500.0,
                ),
                grupo='Grupo Norte',
            )
        )
        TresArrReclamoNuevo(uow)(
            TresArrReclamoCreate(
                reclamo=ReclamoCreate(
                    cliente='SUR',
                    poliza='P-003',
                    dominio='SR111TT',
                    importe_reclamado=700.0,
                ),
                grupo='Grupo Sur',
            )
        )
        otros = OtrosReclamoNuevo(uow)(
            OtrosReclamoCreate(
                reclamo=ReclamoCreate(
                    cliente='GEST',
                    poliza='G-001',
                    dominio='ZZ999',
                    importe_reclamado=2000.0,
                )
            )
        )
        assert sos.reclamo_id is not None
        assert tresa.reclamo_id is not None
        assert otros.id is not None
        _set_created(uow, sos.reclamo_id, datetime(2026, 5, 10, 10, 0))
        _set_created(uow, tresa.reclamo_id, datetime(2026, 6, 15, 9, 30))
        _set_created(uow, otros.id, datetime(2026, 7, 20, 15, 0))
        for reclamo_id, forma in (
            (sos.reclamo_id, FormaPagoEnum.TRANSFERENCIA),
            (sos.reclamo_id, FormaPagoEnum.NOTA_DE_CREDITO),
            (tresa.reclamo_id, FormaPagoEnum.NOTA_DE_CREDITO),
        ):
            PagoNuevo(uow)(
                PagoCreate(
                    reclamo_id=reclamo_id,
                    forma_pago=forma,
                    pagador=AgenteEnum.SOS
                    if forma == FormaPagoEnum.NOTA_DE_CREDITO
                    else AgenteEnum.ASEGURADO,
                    destinatario=AgenteEnum.SM
                    if forma == FormaPagoEnum.NOTA_DE_CREDITO
                    else AgenteEnum.PRESTADOR,
                    monto=8000.0 if forma == FormaPagoEnum.TRANSFERENCIA else 4000.0,
                )
            )
        uow.commit()
    return uow


def test_list_home_filtro_tipo_reclamo() -> None:
    uow = _dataset_filtros()
    items = list_home(uow, ReclamoHomeFilter(tipo_reclamo=TipoReclamoEnum.TRESA))
    assert len(items) == 2
    assert {item.dominio for item in items} == {'CD456EF', 'SR111TT'}
    assert (
        list_home(uow, ReclamoHomeFilter(tipo_reclamo=TipoReclamoEnum.SOS))[0].dominio
        == 'AB123CD'
    )
    assert (
        len(list_home(uow, ReclamoHomeFilter(tipo_reclamo=TipoReclamoEnum.OTROS))) == 1
    )


def test_list_home_filtro_texto_parcial() -> None:
    uow = _dataset_filtros()
    assert len(list_home(uow, ReclamoHomeFilter(texto='ab12'))) == 1
    assert len(list_home(uow, ReclamoHomeFilter(texto='p-00'))) == 3
    assert len(list_home(uow, ReclamoHomeFilter(texto='1001'))) == 1
    assert len(list_home(uow, ReclamoHomeFilter(texto='ZZ99'))) == 1
    assert list_home(uow, ReclamoHomeFilter(texto='noexiste')) == []


def test_list_home_filtro_importe() -> None:
    uow = _dataset_filtros()
    items = list_home(uow, ReclamoHomeFilter(importe_min=2000.0, importe_max=15000.0))
    assert len(items) == 2
    assert {item.dominio for item in items} == {'AB123CD', 'ZZ999'}
    assert (
        len(list_home(uow, ReclamoHomeFilter(importe_min=500.0, importe_max=500.0)))
        == 1
    )
    assert len(list_home(uow, ReclamoHomeFilter(importe_max=600.0))) == 1


def test_list_home_filtro_fechas() -> None:
    uow = _dataset_filtros()
    items = list_home(
        uow,
        ReclamoHomeFilter(fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 30)),
    )
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'
    assert len(list_home(uow, ReclamoHomeFilter(fecha_desde=date(2026, 7, 15)))) == 1
    assert len(list_home(uow, ReclamoHomeFilter(fecha_hasta=date(2026, 5, 31)))) == 1
    assert len(list_home(uow, ReclamoHomeFilter(fecha_desde=date(2020, 1, 1)))) == 3


def test_list_home_filtro_con_pagos() -> None:
    uow = _dataset_filtros()
    assert len(list_home(uow, ReclamoHomeFilter(con_pagos=True))) == 2
    assert len(list_home(uow, ReclamoHomeFilter(con_pagos=False))) == 2
    assert len(list_home(uow, ReclamoHomeFilter(con_nota_credito=True))) == 2
    assert len(list_home(uow, ReclamoHomeFilter(con_nota_credito=False))) == 2


def test_list_home_filtro_active_true() -> None:
    uow = _dataset_filtros()
    with uow:
        target = next(
            r for r in uow.reclamos.list(active_only=False) if r.dominio == 'SR111TT'
        )
        assert target.id is not None
        uow.reclamos.set_active(target.id, False)
        uow.commit()
    activos = list_home(uow, ReclamoHomeFilter(active=True))
    assert {item.dominio for item in activos} == {'AB123CD', 'CD456EF', 'ZZ999'}


def test_list_home_filtro_active_false() -> None:
    uow = _dataset_filtros()
    with uow:
        target = next(
            r for r in uow.reclamos.list(active_only=False) if r.dominio == 'ZZ999'
        )
        assert target.id is not None
        uow.reclamos.set_active(target.id, False)
        uow.commit()
    inactivos = list_home(uow, ReclamoHomeFilter(active=False))
    assert {item.dominio for item in inactivos} == {'ZZ999'}
    assert len(list_home(uow)) == 4


def test_list_home_filtro_grupo() -> None:
    uow = _dataset_filtros()
    items = list_home(uow, ReclamoHomeFilter(grupo='GRUPO NORTE'))
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'
    assert list_home(uow, ReclamoHomeFilter(grupo='No Existe')) == []


def test_list_home_filtro_combinado() -> None:
    uow = _dataset_filtros()
    items = list_home(
        uow,
        ReclamoHomeFilter(
            tipo_reclamo=TipoReclamoEnum.TRESA, con_pagos=True, texto='cd45'
        ),
    )
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'


def test_list_home_sin_filtro_retorna_todo() -> None:
    uow = _dataset_filtros()
    assert len(list_home(uow)) == 4
    assert len(list_home(uow, None)) == 4


def test_list_grupos() -> None:
    uow = _dataset_filtros()
    assert list_grupos(uow) == ['GRUPO NORTE', 'GRUPO SUR']


def test_list_home_orden_fecha_desc() -> None:
    uow = FakeUnitOfWork()
    with uow:
        sos = SosReclamoNuevo(uow)(
            ReclamoSosCreate(
                reclamo=ReclamoCreate(cliente='ACME', poliza='P-010', dominio='AA100'),
                nro_gestion=2001,
            )
        )
        tresa = TresArrReclamoNuevo(uow)(
            TresArrReclamoCreate(
                reclamo=ReclamoCreate(cliente='MEDIO', poliza='P-011', dominio='BB200')
            )
        )
        otros = OtrosReclamoNuevo(uow)(
            OtrosReclamoCreate(
                reclamo=ReclamoCreate(
                    cliente='SIN FECHA', poliza='P-012', dominio='CC300'
                )
            )
        )
        assert sos.reclamo_id is not None
        assert tresa.reclamo_id is not None
        assert otros.id is not None
        _set_created(uow, sos.reclamo_id, datetime(2026, 7, 1, 12, 0))
        _set_created(uow, tresa.reclamo_id, datetime(2026, 1, 1, 9, 0))
        uow.commit()
    items = list_home(uow)
    assert [item.dominio for item in items] == ['AA100', 'BB200', 'CC300']
    assert items[-1].created_at is None


def test_list_pagos_con_detalle_grupo() -> None:
    uow = _dataset_filtros()
    items = list_pagos_con_detalle(uow)
    assert len(items) == 3
    tresa = next(it for it in items if it.dominio == 'CD456EF')
    assert tresa.grupo == 'GRUPO NORTE'
    assert tresa.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO
    sos_items = [it for it in items if it.dominio == 'AB123CD']
    assert len(sos_items) == 2
    assert all(it.grupo is None for it in sos_items)


def test_list_pagos_filtro_pagador() -> None:
    uow = _dataset_filtros()
    items = list_pagos_con_detalle(uow, PagoListFilter(pagadores={AgenteEnum.SOS}))
    assert len(items) == 2
    assert {it.dominio for it in items} == {'AB123CD', 'CD456EF'}
    assert all(it.pagador == AgenteEnum.SOS for it in items)
    solo_asegurado = list_pagos_con_detalle(
        uow, PagoListFilter(pagadores={AgenteEnum.ASEGURADO})
    )
    assert len(solo_asegurado) == 1
    assert solo_asegurado[0].dominio == 'AB123CD'


def test_list_pagos_filtro_destinatario() -> None:
    uow = _dataset_filtros()
    items = list_pagos_con_detalle(uow, PagoListFilter(destinatarios={AgenteEnum.SM}))
    assert len(items) == 2
    assert {it.dominio for it in items} == {'AB123CD', 'CD456EF'}
    assert all(it.destinatario == AgenteEnum.SM for it in items)


def test_list_pagos_filtro_forma() -> None:
    uow = _dataset_filtros()
    transferencias = list_pagos_con_detalle(
        uow, PagoListFilter(formas={FormaPagoEnum.TRANSFERENCIA})
    )
    assert len(transferencias) == 1
    assert transferencias[0].dominio == 'AB123CD'
    ncs = list_pagos_con_detalle(
        uow, PagoListFilter(formas={FormaPagoEnum.NOTA_DE_CREDITO})
    )
    assert len(ncs) == 2
    assert {it.dominio for it in ncs} == {'AB123CD', 'CD456EF'}


def test_list_pagos_filtro_texto() -> None:
    uow = _dataset_filtros()
    assert len(list_pagos_con_detalle(uow, PagoListFilter(texto='acme'))) == 2
    assert len(list_pagos_con_detalle(uow, PagoListFilter(texto='P-00'))) == 3
    assert len(list_pagos_con_detalle(uow, PagoListFilter(texto='grupo norte'))) == 1
    assert len(list_pagos_con_detalle(uow, PagoListFilter(texto='cd45'))) == 1
    assert list_pagos_con_detalle(uow, PagoListFilter(texto='noexiste')) == []


def test_list_pagos_filtro_combinado() -> None:
    uow = _dataset_filtros()
    items = list_pagos_con_detalle(
        uow,
        PagoListFilter(
            pagadores={AgenteEnum.SOS},
            formas={FormaPagoEnum.NOTA_DE_CREDITO},
            texto='cd45',
        ),
    )
    assert len(items) == 1
    assert items[0].dominio == 'CD456EF'


def test_pago_list_filter_is_empty() -> None:
    assert PagoListFilter().is_empty() is True
    assert PagoListFilter(pagadores={AgenteEnum.SOS}).is_empty() is False
    assert PagoListFilter(destinatarios={AgenteEnum.SM}).is_empty() is False
    assert PagoListFilter(formas={FormaPagoEnum.EFECTIVO}).is_empty() is False
    assert PagoListFilter(texto='x').is_empty() is False


def test_list_pagos_filtro_sets_vacios_no_filtran() -> None:
    uow = _dataset_filtros()
    items = list_pagos_con_detalle(
        uow,
        PagoListFilter(pagadores=set(), destinatarios=set(), formas=set()),
    )
    assert len(items) == 3


def test_list_notas_credito_sin_asignar_retorna_nc_sin_periodo() -> None:
    uow = FakeUnitOfWork()
    with uow:
        sos = SosReclamoNuevo(uow)(
            ReclamoSosCreate(
                reclamo=ReclamoCreate(
                    cliente='ACME',
                    poliza='P-001',
                    dominio='AB123CD',
                    importe_reclamado=15000.0,
                ),
                nro_gestion=1001,
            )
        )
        assert sos.reclamo_id is not None
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=sos.reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=5000.0,
                fecha_pago=date(2026, 1, 15),
            )
        )
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=1))
        assert periodo.id is not None
        uow.commit()
    ncs = list_notas_credito_sin_asignar(uow)
    assert len(ncs) == 1
    nc = ncs[0]
    assert nc.monto == 5000.0
    assert nc.fecha_pago == date(2026, 1, 15)
    assert nc.dominio == 'AB123CD'
    assert nc.cliente == 'ACME'
    assert nc.poliza == 'P-001'
    assert nc.nro_gestion == 1001


def test_list_notas_credito_sin_asignar_vacia_despues_de_asignar() -> None:
    uow = FakeUnitOfWork()
    with uow:
        sos = SosReclamoNuevo(uow)(
            ReclamoSosCreate(
                reclamo=ReclamoCreate(
                    cliente='ACME',
                    poliza='P-001',
                    dominio='AB123CD',
                    importe_reclamado=15000.0,
                ),
                nro_gestion=1001,
            )
        )
        assert sos.reclamo_id is not None
        PagoNuevo(uow)(
            PagoCreate(
                reclamo_id=sos.reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=5000.0,
            )
        )
        periodo = PeriodoNuevo(uow)(PeriodoCreate(anio=2026, mes=1))
        assert periodo.id is not None
        nc = uow.credit_notes.get_by_pago_id(1)
        assert nc is not None and nc.id is not None
        AsignarNotaCreditoAPeriodo(uow)(nc.id, periodo.id)
        uow.commit()
    assert list_notas_credito_sin_asignar(uow) == []


def test_list_notas_credito_sin_asignar_vacia_sin_ncs() -> None:
    uow = FakeUnitOfWork()
    assert list_notas_credito_sin_asignar(uow) == []
