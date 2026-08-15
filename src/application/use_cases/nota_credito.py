from src.domain.models.entities import CreditNote
from src.domain.ports.unit_of_work import UnitOfWorkPort


class NotaCreditoBorrar:
    """Delete a credit note together with its associated pago."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, credit_note_id: int) -> None:
        with self._uow:
            nc = self._uow.credit_notes.get(credit_note_id)
            assert nc.pago_id is not None
            self._uow.pagos.delete(nc.pago_id)
            self._uow.credit_notes.delete(credit_note_id)
            self._uow.commit()


class AsignarNotaCreditoAPeriodo:
    """Assign an existing period to a credit note."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, credit_note_id: int, periodo_id: int) -> CreditNote:
        with self._uow:
            self._uow.periodos.get(periodo_id)
            nc = self._uow.credit_notes.get(credit_note_id)
            nc = nc.model_copy(update={'periodo_id': periodo_id})
            nc = self._uow.credit_notes.update(nc)
            self._uow.commit()
            return nc


class DesasignarNotaCreditoAPeriodo:
    """Remove the period assignment from a credit note."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, credit_note_id: int) -> CreditNote:
        with self._uow:
            nc = self._uow.credit_notes.get(credit_note_id)
            nc = nc.model_copy(update={'periodo_id': None})
            nc = self._uow.credit_notes.update(nc)
            self._uow.commit()
            return nc
