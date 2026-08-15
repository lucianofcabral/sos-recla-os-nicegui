import pytest

from src.domain.exceptions import DuplicateEntityError, EntityNotFoundError
from src.domain.models.entities import Grupo, Reclamo, ReclamoSos, User
from src.domain.ports.queries import QueryPort
from src.domain.ports.repositories import (
    CreditNoteRepositoryPort,
    DocumentoRepositoryPort,
    EntidadDocumentoRepositoryPort,
    FacturaRepositoryPort,
    GrupoRepositoryPort,
    PagoRepositoryPort,
    PeriodoRepositoryPort,
    ReclamoRepositoryPort,
    ReclamoSosRepositoryPort,
    TresArrReclamoRepositoryPort,
    UserRepositoryPort,
)
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
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_fakes_conform_to_repository_ports() -> None:
    assert isinstance(FakeReclamoRepository(), ReclamoRepositoryPort)
    assert isinstance(FakeReclamoSosRepository(), ReclamoSosRepositoryPort)
    assert isinstance(FakeTresArrReclamoRepository(), TresArrReclamoRepositoryPort)
    assert isinstance(FakeGrupoRepository(), GrupoRepositoryPort)
    assert isinstance(FakePagoRepository(), PagoRepositoryPort)
    assert isinstance(FakePeriodoRepository(), PeriodoRepositoryPort)
    assert isinstance(FakeFacturaRepository(), FacturaRepositoryPort)
    assert isinstance(FakeCreditNoteRepository(), CreditNoteRepositoryPort)
    assert isinstance(FakeUserRepository(), UserRepositoryPort)
    assert isinstance(FakeDocumentoRepository(), DocumentoRepositoryPort)
    assert isinstance(FakeEntidadDocumentoRepository(), EntidadDocumentoRepositoryPort)


def test_reclamo_save_get_roundtrip() -> None:
    repo = FakeReclamoRepository()
    saved = repo.save(Reclamo(cliente='ACME', dominio='AB123CD'))
    assert saved.id is not None
    assert repo.get(saved.id) == saved


def test_reclamo_set_active_mutates_stored_copy() -> None:
    repo = FakeReclamoRepository()
    saved = repo.save(Reclamo())
    reclamo_id = saved.id
    assert reclamo_id is not None
    repo.set_active(reclamo_id, False)
    assert repo.get(reclamo_id).active is False
    assert repo.list(active_only=True) == []


def test_reclamo_sos_get_by_nro_gestion_roundtrip() -> None:
    reclamos = FakeReclamoRepository()
    sos = FakeReclamoSosRepository()
    saved_reclamo = reclamos.save(Reclamo())
    assert saved_reclamo.id is not None
    saved = sos.save(ReclamoSos(reclamo_id=saved_reclamo.id, nro_gestion=4004))
    assert saved.id is not None
    found = sos.get_by_nro_gestion(4004)
    assert found is not None
    assert found.id == saved.id
    assert sos.get_by_nro_gestion(999) is None


def test_user_save_get_roundtrip() -> None:
    repo = FakeUserRepository()
    saved = repo.save(User(username='admin', password_hash='hashed'))
    assert saved.id is not None
    assert repo.get(saved.id) == saved
    assert repo.get_by_username('admin') == saved


def test_grupo_save_get_by_nombre_y_duplicado() -> None:
    repo = FakeGrupoRepository()
    saved = repo.save(Grupo(grupo='Grupo Norte'))
    assert saved.id is not None
    assert repo.get_by_nombre('GRUPO NORTE') == saved
    assert repo.get_by_nombre('No Existe') is None
    with pytest.raises(DuplicateEntityError):
        repo.save(Grupo(grupo='Grupo Norte'))


def test_get_missing_entity_raises_entity_not_found() -> None:
    with pytest.raises(EntityNotFoundError):
        FakeReclamoRepository().get(999)
    with pytest.raises(EntityNotFoundError):
        FakeUserRepository().get(999)


def test_duplicate_username_raises_duplicate_entity_error() -> None:
    repo = FakeUserRepository()
    repo.save(User(username='admin', password_hash='a'))
    with pytest.raises(DuplicateEntityError):
        repo.save(User(username='admin', password_hash='b'))


def test_fake_unit_of_work_exposes_repos_and_commits() -> None:
    uow = FakeUnitOfWork()
    assert isinstance(uow.reclamos, ReclamoRepositoryPort)
    assert isinstance(uow.users, UserRepositoryPort)
    assert isinstance(uow.grupos, GrupoRepositoryPort)
    with uow:
        uow.commit()
    assert uow.committed is True


def test_fake_unit_of_work_implements_query_port() -> None:
    assert isinstance(FakeUnitOfWork(), QueryPort)
