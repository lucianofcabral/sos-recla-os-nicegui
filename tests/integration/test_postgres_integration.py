"""End-to-end integration tests against a real Postgres database via testcontainers."""

from __future__ import annotations

import shutil

import pytest
from sqlmodel import Session, SQLModel
from testcontainers.community.postgres import PostgresContainer

from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoReclamoEnum
from src.domain.models.entities import CreditNote, Pago, Periodo, Reclamo, ReclamoSos
from src.infrastructure.database import build_engine, create_schema
from src.infrastructure.unit_of_work import SqlModelUnitOfWork

pytestmark = pytest.mark.skipif(
    shutil.which('docker') is None, reason='Docker required'
)


@pytest.fixture(scope='module')
def engine():
    container = PostgresContainer('postgres:16-alpine')
    container.start()
    database_url = container.get_connection_url(driver='psycopg')
    eng = build_engine(database_url)
    create_schema(eng)
    yield eng
    container.stop()


@pytest.fixture(autouse=True)
def clean_schema(engine) -> None:
    SQLModel.metadata.drop_all(engine)
    create_schema(engine)
    yield


def test_end_to_end_reclamo_sos_pago_credit_note(engine) -> None:
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        periodo = uow.periodos.save(Periodo(anio=2026, mes=1, anio_mes=202601))
        reclamo = uow.reclamos.save(
            Reclamo(
                tipo_reclamo=TipoReclamoEnum.SOS,
                cliente='ACME',
                poliza='P-001',
                dominio='AB123CD',
                importe_reclamado=15000.0,
            )
        )
        assert reclamo.id is not None
        reclamo_id = reclamo.id
        uow.reclamos_sos.save(ReclamoSos(reclamo_id=reclamo_id, nro_gestion=1001))
        pago = uow.pagos.save(
            Pago(
                reclamo_id=reclamo_id,
                forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
                pagador=AgenteEnum.SOS,
                destinatario=AgenteEnum.SM,
                monto=10000.0,
            )
        )
        assert pago.id is not None
        assert periodo.id is not None
        periodo_id = periodo.id
        uow.credit_notes.save(CreditNote(pago_id=pago.id, periodo_id=periodo_id))
        uow.commit()

    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        reclamos = uow.reclamos.list()
        assert len(reclamos) == 1
        assert reclamos[0].tipo_reclamo == TipoReclamoEnum.SOS
        sos = uow.reclamos_sos.get_by_reclamo_id(reclamo_id)
        assert sos is not None
        assert sos.nro_gestion == 1001
        pagos = uow.pagos.list(reclamo_id=reclamo_id)
        assert len(pagos) == 1
        assert pagos[0].reclamo is not None
        assert pagos[0].reclamo.id == reclamo_id
        assert pagos[0].forma_pago == FormaPagoEnum.NOTA_DE_CREDITO
        ncs = uow.credit_notes.list_by_periodo(periodo_id)
        assert len(ncs) == 1
        assert ncs[0].pago is not None
        assert ncs[0].pago.id == pagos[0].id


def test_exit_without_commit_rolls_back(engine) -> None:
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        uow.reclamos.save(Reclamo(cliente='ACME', poliza='P-001', dominio='AB123CD'))
    with Session(engine) as sess, SqlModelUnitOfWork(sess) as uow:
        assert uow.reclamos.list() == []
