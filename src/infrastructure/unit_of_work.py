"""Unit of work backed by a real SQLModel session."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from sqlalchemy import func
from sqlmodel import Session, select

from src.adapters.sqlmodel.models import (
    CreditNoteRow,
    FacturaRow,
    GrupoRow,
    PagoRow,
    ReclamoSosRow,
    TresArrRow,
)
from src.adapters.sqlmodel.repositories import (
    SqlModelCreditNoteRepository,
    SqlModelDocumentoRepository,
    SqlModelEntidadDocumentoRepository,
    SqlModelFacturaRepository,
    SqlModelGrupoRepository,
    SqlModelPagoRepository,
    SqlModelPeriodoRepository,
    SqlModelReclamoRepository,
    SqlModelReclamoSosRepository,
    SqlModelTresArrRepository,
    SqlModelUserRepository,
)
from src.domain.domain_enums import FormaPagoEnum
from src.domain.dto.read import (
    CicloCard,
    PagoListItem,
    ReclamoHomeFilter,
    ReclamoHomeItem,
)


class SqlModelUnitOfWork:
    """Real unit of work: explicit commit, rollback + close on exit."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.reclamos = SqlModelReclamoRepository(session)
        self.reclamos_sos = SqlModelReclamoSosRepository(session)
        self.tres_arr = SqlModelTresArrRepository(session)
        self.grupos = SqlModelGrupoRepository(session)
        self.pagos = SqlModelPagoRepository(session)
        self.periodos = SqlModelPeriodoRepository(session)
        self.facturas = SqlModelFacturaRepository(session)
        self.credit_notes = SqlModelCreditNoteRepository(session)
        self.users = SqlModelUserRepository(session)
        self.documentos = SqlModelDocumentoRepository(session)
        self.entidad_documentos = SqlModelEntidadDocumentoRepository(session)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._session.rollback()
        self._session.close()
        return False

    def commit(self) -> None:
        self._session.commit()

    def list_home(
        self, filtro: ReclamoHomeFilter | None = None
    ) -> list[ReclamoHomeItem]:
        """Home listing: reclamos + SOS nro_gestion + pago flags (no N+1)."""
        nro_por_reclamo: dict[int, int] = {}
        for sos in self._session.exec(select(ReclamoSosRow)).all():
            if sos.reclamo_id is not None:
                nro_por_reclamo[sos.reclamo_id] = sos.nro_gestion
        pagos_por_reclamo: dict[int, list[PagoRow]] = {}
        for pago in self._session.exec(select(PagoRow)).all():
            if pago.reclamo_id is not None:
                pagos_por_reclamo.setdefault(pago.reclamo_id, []).append(pago)
        grupo_por_reclamo: dict[int, str | None] = {}
        nombre_por_grupo_id: dict[int, str] = {
            grupo.id: grupo.grupo
            for grupo in self._session.exec(select(GrupoRow)).all()
            if grupo.id is not None
        }
        for tres_arr in self._session.exec(select(TresArrRow)).all():
            if tres_arr.reclamo_id is not None:
                nombre = (
                    nombre_por_grupo_id.get(tres_arr.grupo_id)
                    if tres_arr.grupo_id is not None
                    else None
                )
                grupo_por_reclamo[tres_arr.reclamo_id] = nombre or tres_arr.grupo
        items: list[ReclamoHomeItem] = []
        for reclamo in self.reclamos.list(active_only=False):
            reclamo_id = reclamo.id
            assert reclamo_id is not None
            pagos = pagos_por_reclamo.get(reclamo_id, [])
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
                    nro_gestion=nro_por_reclamo.get(reclamo_id),
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
        return [
            item
            for item in items
            if filtro.matches(item, grupo_por_reclamo.get(item.reclamo_id))
        ]

    def list_grupos(self) -> list[str]:
        """Group names from the ``grupos`` table, sorted."""
        rows = self._session.exec(select(GrupoRow.grupo).order_by(GrupoRow.grupo)).all()
        return [grupo for grupo in rows if grupo is not None]

    def list_pagos_con_detalle(self) -> list[PagoListItem]:
        """Pagos listing with reclamo detail and SOS nro_gestion (no N+1)."""
        pagos = self.pagos.list()
        reclamo_ids = {p.reclamo_id for p in pagos if p.reclamo_id is not None}
        nro_por_reclamo: dict[int, int] = {}
        if reclamo_ids:
            sos_rows = self._session.exec(
                select(ReclamoSosRow).where(ReclamoSosRow.reclamo_id.in_(reclamo_ids))
            ).all()
            for sos in sos_rows:
                if sos.reclamo_id is not None:
                    nro_por_reclamo[sos.reclamo_id] = sos.nro_gestion
        items: list[PagoListItem] = []
        for pago in pagos:
            assert pago.id is not None
            reclamo = pago.reclamo
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
                    nro_gestion=(
                        nro_por_reclamo.get(pago.reclamo_id)
                        if pago.reclamo_id is not None
                        else None
                    ),
                )
            )
        return items

    def list_ciclos(self) -> list[CicloCard]:
        """Cycle cards with SUM/COUNT aggregates grouped by periodo."""
        facturas_por_periodo = self._factura_totales_por_periodo()
        credit_notes_por_periodo = self._credit_note_totales_por_periodo()
        cards: list[CicloCard] = []
        for periodo in self.periodos.list():
            periodo_id = periodo.id
            assert periodo_id is not None
            _cant_facturas, suma_facturas = facturas_por_periodo.get(
                periodo_id, (0, 0.0)
            )
            cant_ncs, suma_ncs = credit_notes_por_periodo.get(periodo_id, (0, 0.0))
            cards.append(
                CicloCard(
                    periodo_id=periodo_id,
                    nombre_corto=periodo.nombre_corto,
                    anio_mes=periodo.anio_mes,
                    cant_documentos=0,
                    suma_importe_facturas=suma_facturas,
                    cant_notas_credito=cant_ncs,
                    suma_importe_notas_credito=suma_ncs,
                )
            )
        return cards

    def _factura_totales_por_periodo(self) -> dict[int, tuple[int, float]]:
        rows = self._session.exec(
            select(
                FacturaRow.periodo_id,
                func.count(FacturaRow.id),
                func.coalesce(func.sum(FacturaRow.importe), 0.0),
            ).group_by(FacturaRow.periodo_id)
        ).all()
        result: dict[int, tuple[int, float]] = {}
        for periodo_id, cant, suma in rows:
            if periodo_id is not None:
                result[periodo_id] = (int(cant), float(suma))
        return result

    def _credit_note_totales_por_periodo(self) -> dict[int, tuple[int, float]]:
        rows = self._session.exec(
            select(
                CreditNoteRow.periodo_id,
                func.count(CreditNoteRow.id),
                func.coalesce(func.sum(PagoRow.monto), 0.0),
            )
            .outerjoin(PagoRow, CreditNoteRow.pago_id == PagoRow.id)
            .where(CreditNoteRow.periodo_id.is_not(None))
            .group_by(CreditNoteRow.periodo_id)
        ).all()
        result: dict[int, tuple[int, float]] = {}
        for periodo_id, cant, suma in rows:
            if periodo_id is not None:
                result[periodo_id] = (int(cant), float(suma))
        return result
