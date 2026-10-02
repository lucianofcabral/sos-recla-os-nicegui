"""Unit of work backed by a real SQLModel session."""

from __future__ import annotations

from datetime import date
from typing import Self

from sqlalchemy import String, func, or_
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from src.adapters.sqlmodel.models import (
    CreditNoteRow,
    EntidadDocumentoRow,
    FacturaRow,
    GrupoRow,
    PagoRow,
    ReclamoRow,
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
from src.domain.domain_enums import FormaPagoEnum, TipoEntidadEnum
from src.domain.dto.read import (
    CicloCard,
    GrupoReclamoItem,
    NotaCreditoSinAsignarItem,
    PagoListFilter,
    PagoListItem,
    PagoListPage,
    ReclamoHomeFilter,
    ReclamoHomeItem,
    ReclamoHomePage,
)

_RECLAMO_SORT_COLUMNS: dict[str, object] = {
    'created_at': ReclamoRow.created_at,
    'dominio': ReclamoRow.dominio,
    'poliza': ReclamoRow.poliza,
    'cliente': ReclamoRow.cliente,
    'tipo_reclamo': ReclamoRow.tipo_reclamo,
}


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
        """Home listing (unpaginated): delegates to the paginated SQL query."""
        return self.list_home_pagina(filtro, offset=0, limit=None).items

    def list_home_pagina(
        self,
        filtro: ReclamoHomeFilter | None = None,
        *,
        offset: int = 0,
        limit: int | None = 20,
        sort_by: str | None = None,
        descending: bool = False,
    ) -> ReclamoHomePage:
        """Home listing: SQL filtering, ordering and LIMIT/OFFSET pagination."""
        conditions: list = self._reclamo_filter_conditions(filtro)
        total = int(
            self._session.exec(
                select(func.count(ReclamoRow.id)).where(*conditions)
            ).one()
        )
        sort_col = _RECLAMO_SORT_COLUMNS.get(sort_by or 'created_at')
        eff_desc = descending if sort_by is not None else True
        order = (
            sort_col.desc() if eff_desc else sort_col.asc(),
            ReclamoRow.id.desc() if eff_desc else ReclamoRow.id.asc(),
        )
        statement = select(ReclamoRow).where(*conditions).order_by(*order)
        if limit is not None:
            statement = statement.offset(offset).limit(limit)
        rows = self._session.exec(statement).all()
        return ReclamoHomePage(
            items=self._reclamo_rows_to_items(rows),
            total=total,
        )

    def _reclamo_filter_conditions(self, filtro: ReclamoHomeFilter | None) -> list:
        conditions: list = []
        if filtro is None:
            return conditions
        if filtro.fecha_desde is not None:
            conditions.append(func.date(ReclamoRow.created_at) >= filtro.fecha_desde)
        if filtro.fecha_hasta is not None:
            conditions.append(func.date(ReclamoRow.created_at) <= filtro.fecha_hasta)
        if filtro.importe_min is not None:
            conditions.append(ReclamoRow.importe_reclamado >= filtro.importe_min)
        if filtro.importe_max is not None:
            conditions.append(ReclamoRow.importe_reclamado <= filtro.importe_max)
        if filtro.con_pagos is not None:
            tiene_pagos = (
                select(PagoRow.id).where(PagoRow.reclamo_id == ReclamoRow.id).exists()
            )
            conditions.append(tiene_pagos if filtro.con_pagos else ~tiene_pagos)
        if filtro.con_nota_credito is not None:
            tiene_nc = (
                select(PagoRow.id)
                .where(
                    PagoRow.reclamo_id == ReclamoRow.id,
                    PagoRow.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO.value,
                )
                .exists()
            )
            conditions.append(tiene_nc if filtro.con_nota_credito else ~tiene_nc)
        if filtro.active is not None:
            conditions.append(ReclamoRow.active == filtro.active)
        if filtro.tipo_reclamo is not None:
            conditions.append(ReclamoRow.tipo_reclamo == filtro.tipo_reclamo.value)
        if filtro.grupo is not None:
            conditions.append(
                select(TresArrRow.id)
                .where(
                    TresArrRow.reclamo_id == ReclamoRow.id,
                    TresArrRow.grupo == filtro.grupo,
                )
                .exists()
            )
        if filtro.texto:
            conditions.append(self._reclamo_texto_condition(filtro.texto))
        return conditions

    def _reclamo_texto_condition(self, texto: str):
        needle = f'%{texto.lower()}%'
        return or_(
            func.lower(func.coalesce(ReclamoRow.dominio, '')).like(needle),
            func.lower(func.coalesce(ReclamoRow.cliente, '')).like(needle),
            func.lower(func.coalesce(ReclamoRow.poliza, '')).like(needle),
            func.lower(func.coalesce(ReclamoRow.tipo_reclamo, '')).like(needle),
            func.lower(func.cast(ReclamoRow.importe_reclamado, String)).like(needle),
            func.lower(func.cast(func.date(ReclamoRow.created_at), String)).like(
                needle
            ),
            select(ReclamoSosRow.id)
            .where(
                ReclamoSosRow.reclamo_id == ReclamoRow.id,
                func.lower(func.cast(ReclamoSosRow.nro_gestion, String)).like(needle),
            )
            .exists(),
            select(TresArrRow.id)
            .where(
                TresArrRow.reclamo_id == ReclamoRow.id,
                func.lower(func.coalesce(TresArrRow.grupo, '')).like(needle),
            )
            .exists(),
        )

    def _reclamo_rows_to_items(self, rows: list[ReclamoRow]) -> list[ReclamoHomeItem]:
        ids = [row.id for row in rows if row.id is not None]
        nro_por_reclamo: dict[int, int] = {}
        pagos_por_reclamo: dict[int, list[PagoRow]] = {}
        if ids:
            for sos in self._session.exec(
                select(ReclamoSosRow).where(ReclamoSosRow.reclamo_id.in_(ids))
            ).all():
                if sos.reclamo_id is not None:
                    nro_por_reclamo[sos.reclamo_id] = sos.nro_gestion
            for pago in self._session.exec(
                select(PagoRow).where(PagoRow.reclamo_id.in_(ids))
            ).all():
                if pago.reclamo_id is not None:
                    pagos_por_reclamo.setdefault(pago.reclamo_id, []).append(pago)
        items: list[ReclamoHomeItem] = []
        for row in rows:
            reclamo = row.to_entity()
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
        return items

    def list_grupos(self) -> list[str]:
        """Group names from the ``grupos`` table, sorted."""
        rows = self._session.exec(select(GrupoRow.grupo).order_by(GrupoRow.grupo)).all()
        return [grupo for grupo in rows if grupo is not None]

    def list_pagos_con_detalle(
        self, filtro: PagoListFilter | None = None
    ) -> list[PagoListItem]:
        """Pagos listing (unpaginated): delegates to the paginated SQL query."""
        return self.list_pagos_pagina(filtro, offset=0, limit=None).items

    def list_pagos_pagina(
        self,
        filtro: PagoListFilter | None = None,
        *,
        offset: int = 0,
        limit: int | None = 20,
    ) -> PagoListPage:
        """Pagos listing: SQL filtering and LIMIT/OFFSET pagination (id order)."""
        conditions: list = self._pago_filter_conditions(filtro)
        total = int(
            self._session.exec(select(func.count(PagoRow.id)).where(*conditions)).one()
        )
        statement = (
            select(PagoRow)
            .options(selectinload(PagoRow.reclamo))
            .where(*conditions)
            .order_by(
                PagoRow.fecha_pago.desc().nullslast(),
                PagoRow.id.desc(),
            )
        )
        if limit is not None:
            statement = statement.offset(offset).limit(limit)
        rows = self._session.exec(statement).all()
        return PagoListPage(
            items=self._pago_rows_to_items(rows),
            total=total,
        )

    def _pago_filter_conditions(self, filtro: PagoListFilter | None) -> list:
        conditions: list = []
        if filtro is None or filtro.is_empty():
            return conditions
        if filtro.pagadores:
            conditions.append(PagoRow.pagador.in_([a.value for a in filtro.pagadores]))
        if filtro.destinatarios:
            conditions.append(
                PagoRow.destinatario.in_([a.value for a in filtro.destinatarios])
            )
        if filtro.formas:
            conditions.append(PagoRow.forma_pago.in_([f.value for f in filtro.formas]))
        if filtro.texto:
            conditions.append(self._pago_texto_condition(filtro.texto))
        return conditions

    def _pago_texto_condition(self, texto: str):
        needle = f'%{texto.lower()}%'
        return or_(
            select(ReclamoRow.id)
            .where(
                ReclamoRow.id == PagoRow.reclamo_id,
                or_(
                    func.lower(func.coalesce(ReclamoRow.dominio, '')).like(needle),
                    func.lower(func.coalesce(ReclamoRow.cliente, '')).like(needle),
                    func.lower(func.coalesce(ReclamoRow.poliza, '')).like(needle),
                ),
            )
            .exists(),
            select(TresArrRow.id)
            .where(
                TresArrRow.reclamo_id == PagoRow.reclamo_id,
                func.lower(func.coalesce(TresArrRow.grupo, '')).like(needle),
            )
            .exists(),
        )

    def _pago_rows_to_items(self, rows: list[PagoRow]) -> list[PagoListItem]:
        reclamo_ids = {r.reclamo_id for r in rows if r.reclamo_id is not None}
        nro_por_reclamo: dict[int, int] = {}
        grupo_por_reclamo: dict[int, str] = {}
        if reclamo_ids:
            for sos in self._session.exec(
                select(ReclamoSosRow).where(ReclamoSosRow.reclamo_id.in_(reclamo_ids))
            ).all():
                if sos.reclamo_id is not None:
                    nro_por_reclamo[sos.reclamo_id] = sos.nro_gestion
            for tres in self._session.exec(
                select(TresArrRow).where(TresArrRow.reclamo_id.in_(reclamo_ids))
            ).all():
                if tres.reclamo_id is not None and tres.grupo is not None:
                    grupo_por_reclamo[tres.reclamo_id] = tres.grupo
        items: list[PagoListItem] = []
        for row in rows:
            pago = row.to_entity()
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
                    grupo=(
                        grupo_por_reclamo.get(pago.reclamo_id)
                        if pago.reclamo_id is not None
                        else None
                    ),
                )
            )
        return items

    def list_grupo_detalle(self, grupo_id: int) -> list[GrupoReclamoItem]:
        """Gestions of a Tres Arroyos group with pago detail (no N+1)."""
        tres_arr_rows = self._session.exec(
            select(TresArrRow)
            .where(
                TresArrRow.grupo_id == grupo_id,
                TresArrRow.reclamo.has(ReclamoRow.active.is_(True)),
            )
            .options(selectinload(TresArrRow.reclamo))
            .order_by(TresArrRow.id)
        ).all()
        reclamo_ids = [
            row.reclamo_id for row in tres_arr_rows if row.reclamo_id is not None
        ]
        pagos_por_reclamo: dict[int, list[PagoRow]] = {}
        if reclamo_ids:
            for pago in self._session.exec(
                select(PagoRow)
                .where(PagoRow.reclamo_id.in_(reclamo_ids))
                .order_by(PagoRow.id)
            ).all():
                if pago.reclamo_id is not None:
                    pagos_por_reclamo.setdefault(pago.reclamo_id, []).append(pago)
        items: list[GrupoReclamoItem] = []
        for row in tres_arr_rows:
            assert row.reclamo_id is not None
            reclamo = row.to_entity().reclamo
            pagos = pagos_por_reclamo.get(row.reclamo_id, [])
            items.append(
                GrupoReclamoItem(
                    reclamo_id=row.reclamo_id,
                    cliente=reclamo.cliente if reclamo is not None else None,
                    poliza=reclamo.poliza if reclamo is not None else None,
                    dominio=reclamo.dominio if reclamo is not None else None,
                    importe_reclamado=(
                        reclamo.importe_reclamado if reclamo is not None else None
                    ),
                    cant_pagos=len(pagos),
                    pagos=[
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
                            nro_gestion=None,
                        )
                        for pago in pagos
                        if pago.id is not None
                    ],
                )
            )
        return items

    def list_ciclos(self) -> list[CicloCard]:
        """Cycle cards with SUM/COUNT aggregates grouped by periodo."""
        facturas_por_periodo = self._factura_totales_por_periodo()
        credit_notes_por_periodo = self._credit_note_totales_por_periodo()
        documentos_por_periodo = self._documento_totales_por_periodo()
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
                    cant_documentos=documentos_por_periodo.get(periodo_id, 0),
                    suma_importe_facturas=suma_facturas,
                    cant_notas_credito=cant_ncs,
                    suma_importe_notas_credito=suma_ncs,
                    cerrado=periodo.cerrado,
                )
            )
        return cards

    def _documento_totales_por_periodo(self) -> dict[int, int]:
        rows = self._session.exec(
            select(
                EntidadDocumentoRow.entidad_id,
                func.count(EntidadDocumentoRow.id),
            )
            .where(EntidadDocumentoRow.tipo_entidad == TipoEntidadEnum.PERIODO.value)
            .group_by(EntidadDocumentoRow.entidad_id)
        ).all()
        result: dict[int, int] = {}
        for entidad_id, cant in rows:
            if entidad_id is not None:
                result[entidad_id] = int(cant)
        return result

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

    def list_notas_credito_por_periodo(
        self, periodo_id: int
    ) -> list[NotaCreditoSinAsignarItem]:
        """Credit notes assigned to a specific period, with pago + reclamo detail."""
        nc_rows = self._session.exec(
            select(CreditNoteRow).where(CreditNoteRow.periodo_id == periodo_id)
        ).all()
        if not nc_rows:
            return []
        pago_ids = [nc.pago_id for nc in nc_rows if nc.pago_id is not None]
        reclamo_ids: set[int] = set()
        pagos: dict[int, PagoRow] = {}
        if pago_ids:
            for pago in self._session.exec(
                select(PagoRow).where(PagoRow.id.in_(pago_ids))
            ).all():
                if pago.id is not None:
                    pagos[pago.id] = pago
                    if pago.reclamo_id is not None:
                        reclamo_ids.add(pago.reclamo_id)
        nro_por_reclamo: dict[int, int] = {}
        if reclamo_ids:
            for sos in self._session.exec(
                select(ReclamoSosRow).where(ReclamoSosRow.reclamo_id.in_(reclamo_ids))
            ).all():
                if sos.reclamo_id is not None:
                    nro_por_reclamo[sos.reclamo_id] = sos.nro_gestion
        reclamos: dict[int, ReclamoRow] = {}
        if reclamo_ids:
            for reclamo in self._session.exec(
                select(ReclamoRow).where(ReclamoRow.id.in_(reclamo_ids))
            ).all():
                if reclamo.id is not None:
                    reclamos[reclamo.id] = reclamo
        items: list[NotaCreditoSinAsignarItem] = []
        for nc in nc_rows:
            assert nc.id is not None
            pago = pagos.get(nc.pago_id) if nc.pago_id is not None else None
            reclamo = (
                reclamos.get(pago.reclamo_id)
                if pago is not None and pago.reclamo_id is not None
                else None
            )
            items.append(
                NotaCreditoSinAsignarItem(
                    credit_note_id=nc.id,
                    pago_id=nc.pago_id,
                    monto=pago.monto if pago is not None else None,
                    fecha_pago=pago.fecha_pago if pago is not None else None,
                    dominio=reclamo.dominio if reclamo is not None else None,
                    cliente=reclamo.cliente if reclamo is not None else None,
                    poliza=reclamo.poliza if reclamo is not None else None,
                    nro_gestion=(
                        nro_por_reclamo.get(pago.reclamo_id)
                        if pago is not None and pago.reclamo_id is not None
                        else None
                    ),
                )
            )
        items.sort(
            key=lambda item: item.fecha_pago or date.min,
            reverse=True,
        )
        return items

    def list_notas_credito_sin_asignar(self) -> list[NotaCreditoSinAsignarItem]:
        """Credit notes with no period, joined with pago and reclamo detail."""
        nc_rows = self._session.exec(
            select(CreditNoteRow).where(CreditNoteRow.periodo_id.is_(None))
        ).all()
        if not nc_rows:
            return []
        pago_ids = [nc.pago_id for nc in nc_rows if nc.pago_id is not None]
        reclamo_ids: set[int] = set()
        pagos: dict[int, PagoRow] = {}
        if pago_ids:
            for pago in self._session.exec(
                select(PagoRow).where(PagoRow.id.in_(pago_ids))
            ).all():
                if pago.id is not None:
                    pagos[pago.id] = pago
                    if pago.reclamo_id is not None:
                        reclamo_ids.add(pago.reclamo_id)
        nro_por_reclamo: dict[int, int] = {}
        if reclamo_ids:
            for sos in self._session.exec(
                select(ReclamoSosRow).where(ReclamoSosRow.reclamo_id.in_(reclamo_ids))
            ).all():
                if sos.reclamo_id is not None:
                    nro_por_reclamo[sos.reclamo_id] = sos.nro_gestion
        reclamos: dict[int, ReclamoRow] = {}
        if reclamo_ids:
            for reclamo in self._session.exec(
                select(ReclamoRow).where(ReclamoRow.id.in_(reclamo_ids))
            ).all():
                if reclamo.id is not None:
                    reclamos[reclamo.id] = reclamo
        items: list[NotaCreditoSinAsignarItem] = []
        for nc in nc_rows:
            assert nc.id is not None
            pago = pagos.get(nc.pago_id) if nc.pago_id is not None else None
            reclamo = (
                reclamos.get(pago.reclamo_id)
                if pago is not None and pago.reclamo_id is not None
                else None
            )
            items.append(
                NotaCreditoSinAsignarItem(
                    credit_note_id=nc.id,
                    pago_id=nc.pago_id,
                    monto=pago.monto if pago is not None else None,
                    fecha_pago=pago.fecha_pago if pago is not None else None,
                    dominio=reclamo.dominio if reclamo is not None else None,
                    cliente=reclamo.cliente if reclamo is not None else None,
                    poliza=reclamo.poliza if reclamo is not None else None,
                    nro_gestion=(
                        nro_por_reclamo.get(pago.reclamo_id)
                        if pago is not None and pago.reclamo_id is not None
                        else None
                    ),
                )
            )
        items.sort(
            key=lambda item: item.fecha_pago or date.min,
            reverse=True,
        )
        return items
