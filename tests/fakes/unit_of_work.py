from __future__ import annotations

from datetime import datetime

from src.domain.domain_enums import FormaPagoEnum
from src.domain.dto.read import (
    CicloCard,
    PagoListItem,
    ReclamoHomeFilter,
    ReclamoHomeItem,
)
from src.domain.models.entities import CreditNote
from tests.fakes.repositories import (
    FakeCreditNoteRepository,
    FakeDocumentoRepository,
    FakeEntidadDocumentoRepository,
    FakeFacturaRepository,
    FakeGrupoRepository,
    FakePagoRepository,
    FakePeriodoRepository,
    FakeReclamoRepository,
    FakeReclamoSosRepository,
    FakeTresArrReclamoRepository,
    FakeUserRepository,
)


class FakeUnitOfWork:
    """In-memory unit of work backed by the fake repositories."""

    _REPO_ATTRS = (
        'reclamos',
        'reclamos_sos',
        'tres_arr',
        'grupos',
        'pagos',
        'periodos',
        'facturas',
        'credit_notes',
        'users',
        'documentos',
        'entidad_documentos',
    )

    def __init__(self) -> None:
        self.reclamos = FakeReclamoRepository()
        self.reclamos_sos = FakeReclamoSosRepository()
        self.tres_arr = FakeTresArrReclamoRepository()
        self.grupos = FakeGrupoRepository()
        self.pagos = FakePagoRepository()
        self.periodos = FakePeriodoRepository()
        self.facturas = FakeFacturaRepository()
        self.credit_notes = FakeCreditNoteRepository()
        self.users = FakeUserRepository()
        self.documentos = FakeDocumentoRepository()
        self.entidad_documentos = FakeEntidadDocumentoRepository()
        self.committed = False
        self._snapshot()

    def _snapshot(self) -> None:
        self._snap = {
            name: dict(getattr(self, name)._store) for name in self._REPO_ATTRS
        }

    def _restore(self) -> None:
        for name, store in self._snap.items():
            getattr(self, name)._store = store

    def __enter__(self) -> FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self._restore()
        return False

    def commit(self) -> None:
        self.committed = True
        self._snapshot()

    def list_home(
        self, filtro: ReclamoHomeFilter | None = None
    ) -> list[ReclamoHomeItem]:
        items: list[ReclamoHomeItem] = []
        for reclamo in self.reclamos.list(active_only=False):
            reclamo_id = reclamo.id
            assert reclamo_id is not None
            sos = self.reclamos_sos.get_by_reclamo_id(reclamo_id)
            pagos = self.pagos.list(reclamo_id=reclamo_id)
            items.append(
                ReclamoHomeItem(
                    reclamo_id=reclamo_id,
                    tipo_reclamo=reclamo.tipo_reclamo,
                    cliente=reclamo.cliente,
                    poliza=reclamo.poliza or '',
                    dominio=reclamo.dominio or '',
                    importe_reclamado=reclamo.importe_reclamado or 0.0,
                    active=reclamo.active,
                    created_at=reclamo.created_at,
                    nro_gestion=sos.nro_gestion if sos is not None else None,
                    has_pagos=bool(pagos),
                    has_credit_note=any(
                        pago.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO
                        for pago in pagos
                    ),
                )
            )
        items.sort(
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        if filtro is None:
            return items
        grupo_por_reclamo: dict[int, str | None] = {}
        nombre_por_grupo_id = {
            grupo.id: grupo.grupo
            for grupo in self.grupos.list()
            if grupo.id is not None
        }
        for tres_arr in self.tres_arr._store.values():
            if tres_arr.reclamo_id is None:
                continue
            nombre = (
                nombre_por_grupo_id.get(tres_arr.grupo_id)
                if tres_arr.grupo_id is not None
                else None
            )
            grupo_por_reclamo[tres_arr.reclamo_id] = nombre or tres_arr.grupo
        return [
            item
            for item in items
            if filtro.matches(item, grupo_por_reclamo.get(item.reclamo_id))
        ]

    def list_grupos(self) -> list[str]:
        """Group names from the fake ``grupos`` repository, sorted."""
        return [grupo.grupo for grupo in self.grupos.list()]

    def list_pagos_con_detalle(self) -> list[PagoListItem]:
        items: list[PagoListItem] = []
        for pago in self.pagos.list():
            assert pago.id is not None
            reclamo = pago.reclamo
            if reclamo is None and pago.reclamo_id is not None:
                reclamo = self.reclamos.get(pago.reclamo_id)
            sos = (
                self.reclamos_sos.get_by_reclamo_id(pago.reclamo_id)
                if pago.reclamo_id is not None
                else None
            )
            items.append(
                PagoListItem(
                    pago_id=pago.id,
                    fecha_pago=pago.fecha_pago,
                    forma_pago=pago.forma_pago,
                    pagador=pago.pagador,
                    destinatario=pago.destinatario,
                    monto=pago.monto,
                    dominio=reclamo.dominio if reclamo is not None else None,
                    poliza=reclamo.poliza if reclamo is not None else None,
                    cliente=reclamo.cliente if reclamo is not None else None,
                    nro_gestion=sos.nro_gestion if sos is not None else None,
                )
            )
        return items

    def list_ciclos(self) -> list[CicloCard]:
        cards: list[CicloCard] = []
        for periodo in self.periodos.list():
            periodo_id = periodo.id
            assert periodo_id is not None
            facturas = self.facturas.list_by_periodo(periodo_id)
            credit_notes = self.credit_notes.list_by_periodo(periodo_id)
            cards.append(
                CicloCard(
                    periodo_id=periodo_id,
                    nombre_corto=periodo.nombre_corto,
                    anio_mes=periodo.anio_mes,
                    cant_documentos=0,
                    suma_importe_facturas=sum(f.importe for f in facturas),
                    cant_notas_credito=len(credit_notes),
                    suma_importe_notas_credito=sum(
                        self._credit_note_monto(cn) for cn in credit_notes
                    ),
                )
            )
        return cards

    def _credit_note_monto(self, credit_note: CreditNote) -> float:
        if credit_note.pago is not None and credit_note.pago.monto is not None:
            return credit_note.pago.monto
        if credit_note.pago_id is not None:
            return self.pagos.get(credit_note.pago_id).monto or 0.0
        return 0.0
