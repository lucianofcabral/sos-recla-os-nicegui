"""Use case to create a Tres Arroyos lot (grupo + gestiones + pagos)."""

from datetime import date, datetime

from src.domain.domain_enums import (
    AgenteEnum,
    FormaPagoEnum,
    TipoEntidadEnum,
    TipoReclamoEnum,
)
from src.domain.dto.create import LoteTresArrCreate
from src.domain.dto.read import LoteTresArrResult
from src.domain.exceptions import DomainError
from src.domain.models.entities import (
    Documento,
    EntidadDocumento,
    Grupo,
    Pago,
    Reclamo,
    TresArrReclamo,
    normalizar_texto,
)
from src.domain.ports.unit_of_work import UnitOfWorkPort


class LoteTresArrNuevo:
    """Create a Tres Arroyos lot in a single transaction.

    The whole lot is saved under one ``with self._uow`` block and committed
    once at the end: on failure the context manager rolls back everything.
    Documents are linked to the ``Grupo`` (not to individual reclamos) and a
    single transfer payment SM -> Prestador is created per gestión whose
    ``importe_reclamado`` is greater than zero.
    """

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: LoteTresArrCreate) -> LoteTresArrResult:
        with self._uow:
            grupo_nombre = normalizar_texto(data.grupo or '')
            if not grupo_nombre:
                raise DomainError('El grupo es obligatorio')
            if self._uow.grupos.get_by_nombre(grupo_nombre) is not None:
                raise DomainError(f'el grupo {grupo_nombre!r} ya existe')
            if not data.gestiones:
                raise DomainError('El lote debe tener al menos una gestión')

            grupo = self._uow.grupos.save(
                Grupo(
                    grupo=grupo_nombre,
                    fecha_creacion=datetime.now(),
                    usuario_creacion=data.usuario_creacion,
                )
            )
            assert grupo.id is not None

            pagos_creados = 0
            gestiones_sin_pago = 0
            documentos_adjuntados = 0
            for item in data.gestiones:
                reclamo = Reclamo(
                    tipo_reclamo=TipoReclamoEnum.TRESA,
                    active=True,
                    cliente=item.reclamo.cliente,
                    poliza=item.reclamo.poliza,
                    dominio=item.reclamo.dominio,
                    importe_reclamado=item.reclamo.importe_reclamado,
                    comentario=item.reclamo.comentario,
                )
                reclamo = self._uow.reclamos.save(reclamo)
                assert reclamo.id is not None
                self._uow.tres_arr.save(
                    TresArrReclamo(
                        reclamo_id=reclamo.id,
                        reclamo=reclamo,
                        grupo=grupo_nombre,
                        grupo_id=grupo.id,
                    )
                )
                for documento in item.documentos:
                    contenido = documento.contenido or b''
                    self._uow.documentos.save(
                        Documento(
                            document_hash=documento.document_hash,
                            tipo=documento.tipo,
                            nombre=documento.nombre,
                            contenido=contenido,
                            tamanio=documento.tamanio,
                            mime=documento.mime,
                            descripcion=documento.descripcion,
                        )
                    )
                    self._uow.entidad_documentos.save(
                        EntidadDocumento(
                            document_hash=documento.document_hash,
                            tipo_entidad=TipoEntidadEnum.GRUPO,
                            entidad_id=grupo.id,
                        )
                    )
                    documentos_adjuntados += 1
                if data.generar_pagos and (item.reclamo.importe_reclamado or 0.0) > 0:
                    self._uow.pagos.save(
                        Pago(
                            reclamo_id=reclamo.id,
                            fecha_pago=date.today(),
                            forma_pago=FormaPagoEnum.TRANSFERENCIA,
                            pagador=AgenteEnum.SM,
                            destinatario=AgenteEnum.PRESTADOR,
                            monto=item.reclamo.importe_reclamado,
                        )
                    )
                    pagos_creados += 1
                else:
                    gestiones_sin_pago += 1

            self._uow.commit()
            return LoteTresArrResult(
                grupo_id=grupo.id,
                grupo=grupo_nombre,
                gestiones_creadas=len(data.gestiones),
                pagos_creados=pagos_creados,
                documentos_adjuntados=documentos_adjuntados,
                gestiones_sin_pago=gestiones_sin_pago,
            )
