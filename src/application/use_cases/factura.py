from src.domain.dto.create import FacturaCreate
from src.domain.models.entities import Factura
from src.domain.ports.unit_of_work import UnitOfWorkPort


class FacturaNueva:
    """Create an invoice with its importe."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: FacturaCreate) -> Factura:
        with self._uow:
            factura = self._uow.facturas.save(
                Factura(
                    periodo_id=data.periodo_id,
                    nro_factura=data.nro_factura,
                    importe=data.importe,
                    fecha_emision=data.fecha_emision,
                    fecha_vencimiento=data.fecha_vencimiento,
                )
            )
            self._uow.commit()
            return factura


class FacturaBorrar: ...
