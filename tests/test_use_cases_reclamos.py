import pytest
from pydantic import ValidationError

from src.application.use_cases.reclamo import (
    OtrosReclamoActualizar,
    OtrosReclamoBorrar,
    OtrosReclamoNuevo,
    SosReclamoActualizar,
    SosReclamoBorrar,
    SosReclamoNuevo,
    TresArrReclamoActualizar,
    TresArrReclamoBorrar,
    TresArrReclamoNuevo,
)
from src.domain.domain_enums import TipoReclamoEnum
from src.domain.dto.create import (
    OtrosReclamoCreate,
    ReclamoCreate,
    ReclamoSosCreate,
    TresArrReclamoCreate,
)
from src.domain.dto.edit import (
    OtrosReclamoEdit,
    ReclamoSosEdit,
    TresArrReclamoEdit,
)
from src.domain.exceptions import EntityNotFoundError
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


def test_sos_nueva_creates_reclamo_and_sos() -> None:
    with FakeUnitOfWork() as uow:
        use_case = SosReclamoNuevo(uow)
        data = ReclamoSosCreate(
            reclamo=_reclamo_data(),
            nro_gestion=1001,
            categoria='Colision',
            motivo='choque',
            usuario_carga='carga1',
            status='pendiente',
            itr=5,
        )
        sos = use_case(data)
        assert sos.id is not None
        assert sos.reclamo is not None
        assert sos.reclamo.tipo_reclamo == TipoReclamoEnum.SOS
        assert sos.reclamo.active is True
        assert sos.nro_gestion == 1001
        assert sos.categoria == 'COLISION'
        assert sos.itr == 5
        assert uow.committed is True


def test_sos_nueva_without_nro_gestion_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        ReclamoSosCreate(reclamo=_reclamo_data())


def test_sos_actualizar_updates_nro_gestion_and_base_field() -> None:
    with FakeUnitOfWork() as uow:
        creado = SosReclamoNuevo(uow)(
            ReclamoSosCreate(reclamo=_reclamo_data(), nro_gestion=1001)
        )
        assert creado.id is not None
        actualizado = SosReclamoActualizar(uow)(
            ReclamoSosEdit(id=creado.id, nro_gestion=2002, cliente='NUEVA')
        )
        assert actualizado.reclamo is not None
        assert actualizado.reclamo.cliente == 'NUEVA'
        sos = uow.reclamos_sos.get_by_reclamo_id(creado.id)
        assert sos is not None
        assert sos.nro_gestion == 2002


def test_sos_borrar_soft_deletes_and_can_be_revived() -> None:
    with FakeUnitOfWork() as uow:
        creado = SosReclamoNuevo(uow)(
            ReclamoSosCreate(reclamo=_reclamo_data(), nro_gestion=1001)
        )
        assert creado.reclamo is not None
        assert creado.reclamo.id is not None
        SosReclamoBorrar(uow)(creado.reclamo.id)
        assert uow.reclamos.list(active_only=True) == []
        uow.reclamos.set_active(creado.reclamo.id, True)
        assert [r.id for r in uow.reclamos.list(active_only=True)] == [
            creado.reclamo.id
        ]


def test_tres_arr_nueva_creates_reclamo_and_grupo() -> None:
    with FakeUnitOfWork() as uow:
        data = TresArrReclamoCreate(reclamo=_reclamo_data(), grupo='Grupo A')
        tres = TresArrReclamoNuevo(uow)(data)
        assert tres.id is not None
        assert tres.reclamo is not None
        assert tres.reclamo.tipo_reclamo == TipoReclamoEnum.TRESA
        assert tres.grupo == 'GRUPO A'
        assert uow.committed is True


def test_tres_arr_nueva_crea_grupo_y_asigna_grupo_id() -> None:
    with FakeUnitOfWork() as uow:
        data = TresArrReclamoCreate(reclamo=_reclamo_data(), grupo='Grupo A')
        tres = TresArrReclamoNuevo(uow)(data)
        assert tres.grupo_id is not None
        grupo = uow.grupos.get_by_nombre('GRUPO A')
        assert grupo is not None
        assert grupo.id == tres.grupo_id


def test_tres_arr_mismo_grupo_reutiliza_grupo_existente() -> None:
    with FakeUnitOfWork() as uow:
        primero = TresArrReclamoNuevo(uow)(
            TresArrReclamoCreate(reclamo=_reclamo_data(), grupo='Grupo A')
        )
        segundo = TresArrReclamoNuevo(uow)(
            TresArrReclamoCreate(
                reclamo=_reclamo_data(dominio='ZZ999'), grupo='Grupo A'
            )
        )
        assert primero.grupo_id is not None
        assert segundo.grupo_id == primero.grupo_id
        assert len(uow.grupos.list()) == 1


def test_tres_arr_sin_grupo_no_crea_grupo() -> None:
    with FakeUnitOfWork() as uow:
        tres = TresArrReclamoNuevo(uow)(TresArrReclamoCreate(reclamo=_reclamo_data()))
        assert tres.grupo is None
        assert tres.grupo_id is None
        assert uow.grupos.list() == []


def test_tres_arr_actualizar_resuelve_grupo_nuevo() -> None:
    with FakeUnitOfWork() as uow:
        data = TresArrReclamoCreate(reclamo=_reclamo_data(), grupo='Grupo A')
        creado = TresArrReclamoNuevo(uow)(data)
        assert creado.reclamo is not None
        assert creado.reclamo.id is not None
        actualizado = TresArrReclamoActualizar(uow)(
            TresArrReclamoEdit(id=creado.reclamo.id, grupo='Grupo B')
        )
        assert actualizado.grupo == 'GRUPO B'
        assert actualizado.grupo_id is not None
        grupo_b = uow.grupos.get_by_nombre('GRUPO B')
        assert grupo_b is not None
        assert actualizado.grupo_id == grupo_b.id
        tres_arr = uow.tres_arr.get_by_reclamo_id(creado.reclamo.id)
        assert tres_arr is not None
        assert tres_arr.grupo == 'GRUPO B'


def test_tres_arr_actualizar_updates_grupo() -> None:
    with FakeUnitOfWork() as uow:
        data = TresArrReclamoCreate(reclamo=_reclamo_data(), grupo='Grupo A')
        creado = TresArrReclamoNuevo(uow)(data)
        assert creado.reclamo is not None
        assert creado.reclamo.id is not None
        actualizado = TresArrReclamoActualizar(uow)(
            TresArrReclamoEdit(id=creado.reclamo.id, grupo='Grupo B', cliente='NUEVA')
        )
        assert actualizado.reclamo is not None
        assert actualizado.reclamo.cliente == 'NUEVA'
        tres_arr = uow.tres_arr.get_by_reclamo_id(creado.reclamo.id)
        assert tres_arr is not None
        assert tres_arr.grupo == 'GRUPO B'


def test_tres_arr_borrar_soft_deletes() -> None:
    with FakeUnitOfWork() as uow:
        data = TresArrReclamoCreate(reclamo=_reclamo_data(), grupo='Grupo A')
        creado = TresArrReclamoNuevo(uow)(data)
        assert creado.reclamo is not None
        TresArrReclamoBorrar(uow)(creado.reclamo.id)
        assert uow.reclamos.list(active_only=True) == []


def test_otros_nuevo_forces_tipo_otros() -> None:
    with FakeUnitOfWork() as uow:
        data = OtrosReclamoCreate(
            reclamo=_reclamo_data(tipo_reclamo=TipoReclamoEnum.SOS),
        )
        otros = OtrosReclamoNuevo(uow)(data)
        assert otros.id is not None
        assert otros.tipo_reclamo == TipoReclamoEnum.OTROS
        assert otros.active is True
        guardado = uow.reclamos.get(otros.id)
        assert guardado.tipo_reclamo == TipoReclamoEnum.OTROS
        assert uow.committed is True


def test_otros_actualizar_updates_base_field() -> None:
    with FakeUnitOfWork() as uow:
        creado = OtrosReclamoNuevo(uow)(OtrosReclamoCreate(reclamo=_reclamo_data()))
        assert creado.id is not None
        actualizado = OtrosReclamoActualizar(uow)(
            OtrosReclamoEdit(id=creado.id, cliente='NUEVA')
        )
        assert actualizado.cliente == 'NUEVA'
        assert actualizado.tipo_reclamo == TipoReclamoEnum.OTROS
        guardado = uow.reclamos.get(creado.id)
        assert guardado.cliente == 'NUEVA'
        assert guardado.tipo_reclamo == TipoReclamoEnum.OTROS


def test_otros_borrar_soft_deletes() -> None:
    with FakeUnitOfWork() as uow:
        creado = OtrosReclamoNuevo(uow)(OtrosReclamoCreate(reclamo=_reclamo_data()))
        assert creado.id is not None
        OtrosReclamoBorrar(uow)(creado.id)
        assert uow.reclamos.list(active_only=True) == []


def test_actualizar_missing_reclamo_raises_entity_not_found() -> None:
    with FakeUnitOfWork() as uow:
        with pytest.raises(EntityNotFoundError):
            SosReclamoActualizar(uow)(ReclamoSosEdit(id=999, nro_gestion=1))
        with pytest.raises(EntityNotFoundError):
            OtrosReclamoActualizar(uow)(OtrosReclamoEdit(id=999))


def test_borrar_missing_reclamo_raises_entity_not_found() -> None:
    with FakeUnitOfWork() as uow:
        with pytest.raises(EntityNotFoundError):
            SosReclamoBorrar(uow)(999)
        with pytest.raises(EntityNotFoundError):
            TresArrReclamoBorrar(uow)(999)
        with pytest.raises(EntityNotFoundError):
            OtrosReclamoBorrar(uow)(999)
