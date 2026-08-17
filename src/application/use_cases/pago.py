from typing import Any

from src.domain.domain_enums import AgenteEnum, FormaPagoEnum
from src.domain.dto.create import PagoCreate
from src.domain.dto.edit import PagoEdit
from src.domain.exceptions import DomainError
from src.domain.models.entities import CreditNote, Pago
from src.domain.ports.unit_of_work import UnitOfWorkPort


def _crear_pago(data: PagoCreate) -> Pago:
    return Pago(
        reclamo_id=data.reclamo_id,
        fecha_pago=data.fecha_pago,
        forma_pago=data.forma_pago,
        pagador=data.pagador,
        destinatario=data.destinatario,
        monto=data.monto,
    )


def registrar_pago(uow: UnitOfWorkPort, data: PagoCreate) -> Pago:
    """Validate and save one pago (no commit). NC pays force SOS->SM and auto-create CreditNote."""
    uow.reclamos.get(data.reclamo_id)
    if data.monto <= 0:
        raise DomainError('monto debe ser mayor a cero')
    if data.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO:
        data.pagador = AgenteEnum.SOS
        data.destinatario = AgenteEnum.SM
        pago = uow.pagos.save(_crear_pago(data))
        assert pago.id is not None
        uow.credit_notes.save(CreditNote(pago_id=pago.id, periodo_id=None))
    else:
        if data.pagador == data.destinatario:
            raise DomainError('el pagador no puede ser igual al destinatario')
        pago = uow.pagos.save(_crear_pago(data))
    return pago


class PagoNuevo:
    """Create a pago; nota de crédito pays auto-create their CreditNote."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: PagoCreate) -> Pago:
        with self._uow:
            pago = registrar_pago(self._uow, data)
            self._uow.commit()
            return pago


class PagoActualizar:
    """Update a pago; nota de crédito pays keep their actors fixed."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: PagoEdit) -> Pago:
        with self._uow:
            pago = self._uow.pagos.get(data.id)
            changes: dict[str, Any] = data.model_dump(exclude_unset=True)
            if pago.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO:
                for field in ('forma_pago', 'pagador', 'destinatario'):
                    if field in changes:
                        raise DomainError(
                            'una nota de crédito no permite cambiar '
                            'forma de pago ni actores'
                        )
                nc = self._uow.credit_notes.get_by_pago_id(data.id)
                if nc is not None and nc.periodo_id is not None:
                    periodo = (
                        nc.periodo
                        if nc.periodo is not None
                        else self._uow.periodos.get(nc.periodo_id)
                    )
                    if periodo.cerrado:
                        raise DomainError(
                            'no se puede editar una nota de crédito '
                            'de un periodo cerrado'
                        )
                editable = ('monto', 'fecha_pago')
            else:
                editable = (
                    'monto',
                    'fecha_pago',
                    'forma_pago',
                    'pagador',
                    'destinatario',
                )
            pago = pago.model_copy(
                update={k: v for k, v in changes.items() if k in editable}
            )
            pago = self._uow.pagos.save(pago)
            self._uow.commit()
            return pago


class PagoBorrar:
    """Delete a pago; nota de crédito pays must go through NotaCreditoBorrar."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, pago_id: int) -> None:
        with self._uow:
            pago = self._uow.pagos.get(pago_id)
            if pago.forma_pago == FormaPagoEnum.NOTA_DE_CREDITO:
                raise DomainError('esta nota de crédito se borra con NotaCreditoBorrar')
            self._uow.pagos.delete(pago_id)
            self._uow.commit()
