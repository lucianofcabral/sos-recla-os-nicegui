from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.application.use_cases.pago import registrar_pago
from src.domain.domain_enums import TipoReclamoEnum
from src.domain.dto.create import (
    OtrosReclamoCreate,
    PagoCreate,
    PagoReclamoCreate,
    ReclamoSosCreate,
    TresArrReclamoCreate,
)
from src.domain.dto.edit import (
    OtrosReclamoEdit,
    ReclamoSosEdit,
    TresArrReclamoEdit,
)
from src.domain.exceptions import (
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from src.domain.models.entities import (
    Grupo,
    Reclamo,
    ReclamoSos,
    TresArrReclamo,
    normalizar_texto,
)
from src.domain.ports.unit_of_work import UnitOfWorkPort

RECLAMO_BASE_FIELDS: tuple[str, ...] = (
    'cliente',
    'poliza',
    'dominio',
    'importe_reclamado',
    'comentario',
)


def _changes(data: BaseModel, fields: tuple[str, ...]) -> dict[str, Any]:
    return {f: getattr(data, f) for f in fields if getattr(data, f) is not None}


def _resolver_grupo_id(uow: UnitOfWorkPort, nombre: str | None) -> int | None:
    """Resolve a group by name, creating it when missing; returns its id."""
    if not nombre:
        return None
    nombre = normalizar_texto(nombre)
    assert nombre is not None
    grupo = uow.grupos.get_by_nombre(nombre)
    if grupo is None:
        grupo = uow.grupos.save(Grupo(grupo=nombre, fecha_creacion=datetime.now()))
    assert grupo.id is not None
    return grupo.id


class SosReclamoNuevo:
    """Create a SOS reclamo and its associated SOS record."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: ReclamoSosCreate) -> ReclamoSos:
        with self._uow:
            reclamo = Reclamo(
                tipo_reclamo=TipoReclamoEnum.SOS,
                active=True,
                cliente=data.reclamo.cliente,
                poliza=data.reclamo.poliza,
                dominio=data.reclamo.dominio,
                importe_reclamado=data.reclamo.importe_reclamado,
                comentario=data.reclamo.comentario,
            )
            reclamo = self._uow.reclamos.save(reclamo)
            assert reclamo.id is not None
            sos = self._uow.reclamos_sos.save(
                ReclamoSos(
                    reclamo_id=reclamo.id,
                    reclamo=reclamo,
                    nro_gestion=data.nro_gestion,
                    categoria=data.categoria,
                    motivo=data.motivo,
                    usuario_carga=data.usuario_carga,
                    usuario_respuesta=data.usuario_respuesta,
                    status=data.status,
                    itr=data.itr,
                )
            )
            self._uow.commit()
            return sos


class SosReclamoActualizar:
    """Update a SOS reclamo base fields and its SOS record."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: ReclamoSosEdit) -> ReclamoSos:
        with self._uow:
            reclamo = self._uow.reclamos.get(data.id)
            sos = self._uow.reclamos_sos.get_by_reclamo_id(data.id)
            if sos is None:
                raise EntityNotFoundError(f'reclamo sos {data.id} not found')
            reclamo = Reclamo.model_validate(
                {**reclamo.model_dump(), **_changes(data, RECLAMO_BASE_FIELDS)}
            )
            sos = ReclamoSos.model_validate(
                {
                    **sos.model_dump(),
                    **_changes(
                        data,
                        (
                            'nro_gestion',
                            'categoria',
                            'motivo',
                            'usuario_carga',
                            'usuario_respuesta',
                            'status',
                            'itr',
                        ),
                    ),
                }
            )
            reclamo = self._uow.reclamos.update(reclamo)
            sos = sos.model_copy(update={'reclamo': reclamo})
            self._uow.reclamos_sos.update(sos)
            self._uow.commit()
            return sos


class SosReclamoBorrar:
    """Soft-delete a SOS reclamo by setting it inactive."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, reclamo_id: int) -> None:
        with self._uow:
            self._uow.reclamos.set_active(reclamo_id, False)
            self._uow.commit()


class TresArrReclamoNuevo:
    """Create a Tres Arroyos reclamo and its associated record."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: TresArrReclamoCreate) -> TresArrReclamo:
        with self._uow:
            reclamo = Reclamo(
                tipo_reclamo=TipoReclamoEnum.TRESA,
                active=True,
                cliente=data.reclamo.cliente,
                poliza=data.reclamo.poliza,
                dominio=data.reclamo.dominio,
                importe_reclamado=data.reclamo.importe_reclamado,
                comentario=data.reclamo.comentario,
            )
            reclamo = self._uow.reclamos.save(reclamo)
            assert reclamo.id is not None
            tresa = self._uow.tres_arr.save(
                TresArrReclamo(
                    reclamo_id=reclamo.id,
                    reclamo=reclamo,
                    grupo=data.grupo,
                    grupo_id=_resolver_grupo_id(self._uow, data.grupo),
                )
            )
            self._uow.commit()
            return tresa


class TresArrReclamoActualizar:
    """Update a Tres Arroyos reclamo base fields and its record."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: TresArrReclamoEdit) -> TresArrReclamo:
        with self._uow:
            reclamo = self._uow.reclamos.get(data.id)
            tres_arr = self._uow.tres_arr.get_by_reclamo_id(data.id)
            if tres_arr is None:
                raise EntityNotFoundError(f'tres arr {data.id} not found')
            reclamo = Reclamo.model_validate(
                {**reclamo.model_dump(), **_changes(data, RECLAMO_BASE_FIELDS)}
            )
            cambios = _changes(data, ('grupo',))
            if 'grupo' in cambios:
                cambios['grupo_id'] = _resolver_grupo_id(self._uow, cambios['grupo'])
            tres_arr = TresArrReclamo.model_validate(
                {**tres_arr.model_dump(), **cambios}
            )
            reclamo = self._uow.reclamos.update(reclamo)
            tres_arr = tres_arr.model_copy(update={'reclamo': reclamo})
            self._uow.tres_arr.update(tres_arr)
            self._uow.commit()
            return tres_arr


class TresArrReclamoBorrar:
    """Soft-delete a Tres Arroyos reclamo by setting it inactive."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, reclamo_id: int) -> None:
        with self._uow:
            self._uow.reclamos.set_active(reclamo_id, False)
            self._uow.commit()


def _construir_otros(data: OtrosReclamoCreate) -> Reclamo:
    return Reclamo(
        tipo_reclamo=TipoReclamoEnum.OTROS,
        active=True,
        cliente=data.reclamo.cliente,
        poliza=data.reclamo.poliza,
        dominio=data.reclamo.dominio,
        importe_reclamado=data.reclamo.importe_reclamado,
        comentario=data.reclamo.comentario,
    )


class OtrosReclamoNuevo:
    """Create an OTROS reclamo; only the base reclamo is persisted."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: OtrosReclamoCreate) -> Reclamo:
        with self._uow:
            reclamo = self._uow.reclamos.save(_construir_otros(data))
            self._uow.commit()
            return reclamo


class OtrosReclamoConPagosNuevo:
    """Create an OTROS reclamo and its pagos in one transaction."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(
        self, data: OtrosReclamoCreate, pagos: Sequence[PagoReclamoCreate] = ()
    ) -> Reclamo:
        with self._uow:
            reclamo = self._uow.reclamos.save(_construir_otros(data))
            assert reclamo.id is not None
            for pago in pagos:
                registrar_pago(
                    self._uow, PagoCreate(**pago.model_dump(), reclamo_id=reclamo.id)
                )
            self._uow.commit()
            return reclamo


class OtrosReclamoActualizar:
    """Update an OTROS reclamo base fields; only the base reclamo is touched."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: OtrosReclamoEdit) -> Reclamo:
        with self._uow:
            reclamo = self._uow.reclamos.get(data.id)
            reclamo = Reclamo.model_validate(
                {**reclamo.model_dump(), **_changes(data, RECLAMO_BASE_FIELDS)}
            )
            reclamo = self._uow.reclamos.update(reclamo)
            self._uow.commit()
            return reclamo


class OtrosReclamoBorrar:
    """Soft-delete a generic reclamo by setting it inactive."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, reclamo_id: int) -> None:
        with self._uow:
            self._uow.reclamos.set_active(reclamo_id, False)
            self._uow.commit()


class ReclamoAlternarEstado:
    """Toggle the active flag of a reclamo (activate/inactivate)."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, reclamo_id: int) -> Reclamo:
        with self._uow:
            reclamo = self._uow.reclamos.get(reclamo_id)
            self._uow.reclamos.set_active(reclamo_id, not reclamo.active)
            self._uow.commit()
            return self._uow.reclamos.get(reclamo_id)


class ActualizarGrupo:
    """Rename a 3 Arroyos group: updates the Grupo record and every member."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, grupo_id: int, nuevo_nombre: str | None) -> Grupo:
        with self._uow:
            nombre = normalizar_texto(nuevo_nombre or '')
            assert nombre is not None
            if not nombre:
                raise DomainError('el nombre del grupo no puede estar vacío')
            grupo = self._uow.grupos.get(grupo_id)
            if nombre == grupo.grupo:
                return grupo
            existente = self._uow.grupos.get_by_nombre(nombre)
            if existente is not None and existente.id != grupo_id:
                raise DuplicateEntityError(f'ya existe un grupo llamado {nombre}')
            updated = Grupo.model_validate({**grupo.model_dump(), 'grupo': nombre})
            self._uow.grupos.update(updated)
            for tres in self._uow.tres_arr.list_by_grupo_id(grupo_id):
                nuevo_tres = TresArrReclamo.model_validate(
                    {**tres.model_dump(), 'grupo': nombre}
                )
                self._uow.tres_arr.update(nuevo_tres)
            self._uow.commit()
            return updated
