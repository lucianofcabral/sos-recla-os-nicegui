"""Repository tests against an in-memory SQLite database."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

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
from src.domain.domain_enums import AgenteEnum, FormaPagoEnum, TipoEntidadEnum
from src.domain.exceptions import DuplicateEntityError, EntityNotFoundError
from src.domain.models.entities import (
    CreditNote,
    Documento,
    EntidadDocumento,
    Factura,
    Grupo,
    Pago,
    Periodo,
    Reclamo,
    ReclamoSos,
    TresArrReclamo,
    User,
)
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
from src.infrastructure.database import create_schema


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    create_schema(engine)
    with Session(engine) as sess:
        yield sess


def _nuevo_reclamo() -> Reclamo:
    return Reclamo(cliente='ACME', poliza='P-001', dominio='AB123CD')


def _reclamo_id(
    session: Session, repo: SqlModelReclamoRepository, reclamo: Reclamo | None = None
) -> int:
    saved = repo.save(reclamo or _nuevo_reclamo())
    assert saved.id is not None
    return saved.id


def test_repos_conform_to_ports(session: Session) -> None:
    assert isinstance(SqlModelReclamoRepository(session), ReclamoRepositoryPort)
    assert isinstance(SqlModelReclamoSosRepository(session), ReclamoSosRepositoryPort)
    assert isinstance(SqlModelTresArrRepository(session), TresArrReclamoRepositoryPort)
    assert isinstance(SqlModelGrupoRepository(session), GrupoRepositoryPort)
    assert isinstance(SqlModelPagoRepository(session), PagoRepositoryPort)
    assert isinstance(SqlModelPeriodoRepository(session), PeriodoRepositoryPort)
    assert isinstance(SqlModelFacturaRepository(session), FacturaRepositoryPort)
    assert isinstance(SqlModelCreditNoteRepository(session), CreditNoteRepositoryPort)
    assert isinstance(SqlModelUserRepository(session), UserRepositoryPort)
    assert isinstance(SqlModelDocumentoRepository(session), DocumentoRepositoryPort)
    assert isinstance(
        SqlModelEntidadDocumentoRepository(session), EntidadDocumentoRepositoryPort
    )


def test_reclamo_save_assigns_id(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    saved = repo.save(_nuevo_reclamo())
    assert saved.id is not None


def test_reclamo_get_returns_saved(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    saved = repo.save(_nuevo_reclamo())
    assert repo.get(saved.id) == saved


def test_reclamo_get_missing_raises_entity_not_found(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    with pytest.raises(EntityNotFoundError):
        repo.get(999)


def test_reclamo_list_active_filters(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    _reclamo_id(session, repo)
    inactive_id = _reclamo_id(
        session, repo, _nuevo_reclamo().model_copy(update={'active': False})
    )
    active = repo.list(active_only=True)
    assert len(active) == 1
    assert all(r.active for r in active)
    assert inactive_id not in [r.id for r in active]
    assert len(repo.list(active_only=False)) == 2


def test_reclamo_update_modifies_fields(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    saved = repo.save(_nuevo_reclamo())
    updated = repo.update(saved.model_copy(update={'comentario': 'nuevo comentario'}))
    assert updated.comentario == 'NUEVO COMENTARIO'
    assert repo.get(saved.id).comentario == 'NUEVO COMENTARIO'


def test_reclamo_update_missing_raises_entity_not_found(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    with pytest.raises(EntityNotFoundError):
        repo.update(_nuevo_reclamo().model_copy(update={'id': 999}))


def test_reclamo_set_active_excludes_from_active_list(session: Session) -> None:
    repo = SqlModelReclamoRepository(session)
    saved = repo.save(_nuevo_reclamo())
    repo.set_active(saved.id, False)
    assert repo.list(active_only=True) == []
    assert repo.get(saved.id).active is False


def test_reclamo_sos_save_and_get_by_reclamo_id(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    sos_repo = SqlModelReclamoSosRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    saved = sos_repo.save(ReclamoSos(reclamo_id=reclamo_id, nro_gestion=1001))
    assert saved.id is not None
    found = sos_repo.get_by_reclamo_id(reclamo_id)
    assert found is not None
    assert found.nro_gestion == 1001


def test_reclamo_sos_update_modifies_fields(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    sos_repo = SqlModelReclamoSosRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    saved = sos_repo.save(ReclamoSos(reclamo_id=reclamo_id, nro_gestion=1001))
    updated = sos_repo.update(saved.model_copy(update={'nro_gestion': 2002}))
    assert updated.nro_gestion == 2002
    found = sos_repo.get_by_reclamo_id(reclamo_id)
    assert found is not None
    assert found.nro_gestion == 2002


def test_reclamo_sos_get_by_missing_reclamo_returns_none(session: Session) -> None:
    sos_repo = SqlModelReclamoSosRepository(session)
    assert sos_repo.get_by_reclamo_id(999) is None


def test_reclamo_sos_get_by_nro_gestion_roundtrip(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    sos_repo = SqlModelReclamoSosRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    saved = sos_repo.save(
        ReclamoSos(reclamo_id=reclamo_id, nro_gestion=1001, motivo='choque')
    )
    assert saved.id is not None
    found = sos_repo.get_by_nro_gestion(1001)
    assert found is not None
    assert found.id == saved.id
    assert found.motivo == 'CHOQUE'
    assert sos_repo.get_by_nro_gestion(999) is None


def test_tres_arr_save_and_get_by_reclamo_id(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    repo = SqlModelTresArrRepository(session)
    grupos = SqlModelGrupoRepository(session)
    grupo = grupos.save(Grupo(grupo='Grupo A'))
    assert grupo.id is not None
    reclamo_id = _reclamo_id(session, reclamos)
    saved = repo.save(
        TresArrReclamo(reclamo_id=reclamo_id, grupo='Grupo A', grupo_id=grupo.id)
    )
    assert saved.id is not None
    found = repo.get_by_reclamo_id(reclamo_id)
    assert found is not None
    assert found.grupo == 'GRUPO A'
    assert found.grupo_id == grupo.id
    updated = repo.update(saved.model_copy(update={'grupo': 'Grupo B'}))
    assert updated.grupo == 'GRUPO B'
    assert repo.get_by_reclamo_id(999) is None


def test_grupo_save_get_by_nombre_and_list(session: Session) -> None:
    repo = SqlModelGrupoRepository(session)
    norte = repo.save(Grupo(grupo='Grupo Norte'))
    sur = repo.save(Grupo(grupo='Grupo Sur'))
    assert norte.id is not None
    assert sur.id is not None
    found = repo.get_by_nombre('GRUPO NORTE')
    assert found is not None
    assert found.id == norte.id
    assert repo.get_by_nombre('No Existe') is None
    assert repo.list() == [norte, sur]


def test_grupo_save_duplicate_nombre_raises(session: Session) -> None:
    repo = SqlModelGrupoRepository(session)
    repo.save(Grupo(grupo='Grupo A'))
    with pytest.raises(DuplicateEntityError):
        repo.save(Grupo(grupo='Grupo A'))


def _pago_nc() -> Pago:
    return Pago(
        forma_pago=FormaPagoEnum.NOTA_DE_CREDITO,
        pagador=AgenteEnum.SOS,
        destinatario=AgenteEnum.SM,
        monto=1000.0,
    )


def test_pago_save_nuevo_and_upsert(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pago = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
    assert pago.id is not None
    updated = pagos.save(pago.model_copy(update={'monto': 2500.0}))
    assert updated.id == pago.id
    assert pagos.get(pago.id).monto == 2500.0


def test_pago_list_filters_by_reclamo(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    reclamo_a = _reclamo_id(session, reclamos)
    reclamo_b = _reclamo_id(
        session, reclamos, _nuevo_reclamo().model_copy(update={'cliente': 'OTRO'})
    )
    pago_a = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_a}))
    pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_b}))
    lista = pagos.list(reclamo_id=reclamo_a)
    assert len(lista) == 1
    assert lista[0].id == pago_a.id


def test_pago_list_embeds_reclamo(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
    lista = pagos.list()
    assert len(lista) == 1
    assert lista[0].reclamo is not None
    assert lista[0].reclamo.id == reclamo_id


def test_pago_delete_removes_and_missing_raises(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pago = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
    pagos.delete(pago.id)
    assert pagos.list(reclamo_id=reclamo_id) == []
    with pytest.raises(EntityNotFoundError):
        pagos.delete(999)


def _periodo(session: Session, anio: int, mes: int) -> Periodo:
    saved = SqlModelPeriodoRepository(session).save(Periodo(anio=anio, mes=mes))
    assert saved.id is not None
    return saved


def test_periodo_save_get_list(session: Session) -> None:
    repo = SqlModelPeriodoRepository(session)
    saved = repo.save(Periodo(anio=2026, mes=1))
    assert saved.id is not None
    assert repo.get(saved.id) == saved
    assert repo.list() == [saved]
    with pytest.raises(EntityNotFoundError):
        repo.get(999)


def test_factura_save_and_list_by_periodo(session: Session) -> None:
    facturas = SqlModelFacturaRepository(session)
    periodo = _periodo(session, 2026, 1)
    assert periodo.id is not None
    saved = facturas.save(Factura(periodo_id=periodo.id, nro_factura='A-0001'))
    assert saved.id is not None
    lista = facturas.list_by_periodo(periodo.id)
    assert len(lista) == 1
    assert lista[0].id == saved.id
    assert lista[0].periodo is not None
    assert lista[0].periodo.id == periodo.id


def test_credit_note_save_get_list_by_periodo(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    credit_notes = SqlModelCreditNoteRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pago_ids: list[int] = []
    for _ in range(3):
        pago = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
        assert pago.id is not None
        pago_ids.append(pago.id)
    p1 = _periodo(session, 2026, 1)
    p2 = _periodo(session, 2026, 2)
    nc1 = credit_notes.save(CreditNote(pago_id=pago_ids[0], periodo_id=p1.id))
    nc2 = credit_notes.save(CreditNote(pago_id=pago_ids[1], periodo_id=p2.id))
    credit_notes.save(CreditNote(pago_id=pago_ids[2], periodo_id=None))
    assert nc1.id is not None
    assert nc2.id is not None
    assert [nc.id for nc in credit_notes.list_by_periodo(p1.id)] == [nc1.id]
    assert [nc.id for nc in credit_notes.list_by_periodo(p2.id)] == [nc2.id]
    assert credit_notes.list_by_periodo(999) == []


def test_credit_note_get_embeds_pago_and_periodo(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    credit_notes = SqlModelCreditNoteRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pago = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
    assert pago.id is not None
    p1 = _periodo(session, 2026, 1)
    nc = credit_notes.save(CreditNote(pago_id=pago.id, periodo_id=p1.id))
    assert nc.id is not None
    found = credit_notes.get(nc.id)
    assert found.pago is not None
    assert found.pago.id == pago.id
    assert found.periodo is not None
    assert found.periodo.id == p1.id
    with pytest.raises(EntityNotFoundError):
        credit_notes.get(999)


def test_credit_note_update_changes_periodo(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    credit_notes = SqlModelCreditNoteRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pago = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
    assert pago.id is not None
    p1 = _periodo(session, 2026, 1)
    p2 = _periodo(session, 2026, 2)
    nc = credit_notes.save(CreditNote(pago_id=pago.id, periodo_id=p1.id))
    assert nc.id is not None
    updated = credit_notes.update(nc.model_copy(update={'periodo_id': p2.id}))
    assert updated.periodo_id == p2.id
    got = credit_notes.get(nc.id)
    assert got.periodo_id == p2.id


def test_credit_note_delete_and_missing_raises(session: Session) -> None:
    reclamos = SqlModelReclamoRepository(session)
    pagos = SqlModelPagoRepository(session)
    credit_notes = SqlModelCreditNoteRepository(session)
    reclamo_id = _reclamo_id(session, reclamos)
    pago = pagos.save(_pago_nc().model_copy(update={'reclamo_id': reclamo_id}))
    assert pago.id is not None
    nc = credit_notes.save(CreditNote(pago_id=pago.id))
    assert nc.id is not None
    credit_notes.delete(nc.id)
    with pytest.raises(EntityNotFoundError):
        credit_notes.get(nc.id)
    with pytest.raises(EntityNotFoundError):
        credit_notes.delete(999)


def test_user_save_get_and_get_by_username(session: Session) -> None:
    repo = SqlModelUserRepository(session)
    saved = repo.save(User(username='admin', password_hash='hashed'))
    assert saved.id is not None
    assert repo.get(saved.id).username == 'admin'
    found = repo.get_by_username('admin')
    assert found is not None
    assert found.id == saved.id
    assert repo.get_by_username('nobody') is None
    with pytest.raises(EntityNotFoundError):
        repo.get(999)


def test_user_duplicate_username_raises(session: Session) -> None:
    repo = SqlModelUserRepository(session)
    repo.save(User(username='admin', password_hash='a'))
    with pytest.raises(DuplicateEntityError):
        repo.save(User(username='admin', password_hash='b'))


def test_documento_save_get_by_hash_roundtrip(session: Session) -> None:
    repo = SqlModelDocumentoRepository(session)
    doc = Documento(
        document_hash='a' * 64,
        tipo='Factura',
        nombre='factura.pdf',
        contenido=b'pdf-bytes',
        tamanio=9,
        mime='application/pdf',
    )
    saved = repo.save(doc)
    assert saved == doc
    found = repo.get_by_hash('a' * 64)
    assert found is not None
    assert found.nombre == 'factura.pdf'
    assert found.contenido == b'pdf-bytes'
    assert repo.get_by_hash('f' * 64) is None
    assert repo.list() == [saved]


def test_entidad_documento_save_list_y_unique(session: Session) -> None:
    repo = SqlModelEntidadDocumentoRepository(session)
    vinculo = EntidadDocumento(
        document_hash='a' * 64,
        tipo_entidad=TipoEntidadEnum.RECLAMO,
        entidad_id=1,
    )
    saved = repo.save(vinculo)
    assert saved == vinculo
    assert repo.list() == [saved]
    repo.save(
        EntidadDocumento(
            document_hash='a' * 64,
            tipo_entidad=TipoEntidadEnum.RECLAMO,
            entidad_id=2,
        )
    )
    assert len(repo.list()) == 2
    with pytest.raises(IntegrityError):
        repo.save(
            EntidadDocumento(
                document_hash='a' * 64,
                tipo_entidad=TipoEntidadEnum.RECLAMO,
                entidad_id=1,
            )
        )
