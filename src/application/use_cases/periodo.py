from src.domain.dto.create import PeriodoCreate
from src.domain.exceptions import DomainError
from src.domain.models.entities import Periodo
from src.domain.ports.unit_of_work import UnitOfWorkPort


class PeriodoNuevo:
    """Create a billing period from PeriodoCreate data."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: PeriodoCreate) -> Periodo:
        with self._uow:
            if any(not periodo.cerrado for periodo in self._uow.periodos.list()):
                raise DomainError(
                    'no se puede crear un periodo nuevo si no están todos cerrados'
                )
            nombre_corto = data.nombre_corto or f'{data.mes:02d}/{data.anio}'
            periodo = self._uow.periodos.save(
                Periodo(
                    anio=data.anio,
                    mes=data.mes,
                    anio_mes=data.anio * 100 + data.mes,
                    nombre_corto=nombre_corto,
                    nombre_largo=data.nombre_largo,
                    fecha_inicio=data.fecha_inicio,
                    fecha_fin=data.fecha_fin,
                )
            )
            self._uow.commit()
            return periodo


class PeriodoCerrar:
    """Close a billing period (reversible)."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, periodo_id: int) -> Periodo:
        with self._uow:
            periodo = self._uow.periodos.get(periodo_id)
            periodo = periodo.model_copy(update={'cerrado': True})
            periodo = self._uow.periodos.update(periodo)
            self._uow.commit()
            return periodo


class PeriodoReabrir:
    """Reopen a closed billing period."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, periodo_id: int) -> Periodo:
        with self._uow:
            periodo = self._uow.periodos.get(periodo_id)
            periodo = periodo.model_copy(update={'cerrado': False})
            periodo = self._uow.periodos.update(periodo)
            self._uow.commit()
            return periodo


class PeriodoBorrar: ...
