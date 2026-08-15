"""Unit of work tests against an in-memory SQLite database."""

from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from src.domain.models.entities import Reclamo
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


def _reclamo() -> Reclamo:
    return Reclamo(cliente='ACME', poliza='P-001', dominio='AB123CD')


def test_commit_persists_across_sessions(engine) -> None:
    sess_a = Session(engine)
    with SqlModelUnitOfWork(sess_a) as uow:
        uow.reclamos.save(_reclamo())
        uow.commit()
    sess_b = Session(engine)
    with SqlModelUnitOfWork(sess_b) as uow_b:
        items = uow_b.reclamos.list()
        assert len(items) == 1
        assert items[0].poliza == 'P-001'


def test_exit_without_commit_rolls_back(engine) -> None:
    sess_a = Session(engine)
    with SqlModelUnitOfWork(sess_a) as uow:
        uow.reclamos.save(_reclamo())
    sess_b = Session(engine)
    with SqlModelUnitOfWork(sess_b) as uow_b:
        assert uow_b.reclamos.list() == []
