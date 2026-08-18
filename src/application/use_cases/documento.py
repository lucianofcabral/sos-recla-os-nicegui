"""Use cases to attach, list and remove documents on entities (reclamos, periodos)."""

from __future__ import annotations

from src.domain.domain_enums import TipoEntidadEnum
from src.domain.dto.create import DocumentoCreate
from src.domain.exceptions import DomainError
from src.domain.models.entities import Documento, EntidadDocumento
from src.domain.ports.unit_of_work import UnitOfWorkPort

_ENTIDADES_CON_DOCUMENTOS = {TipoEntidadEnum.RECLAMO, TipoEntidadEnum.PERIODO}


class DocumentoAdjuntar:
    """Attach a document to an entity.

    Idempotent by content hash: re-attaching the same bytes to the same
    entity creates nothing new; the same document attached to a different
    entity only creates the link.
    """

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(
        self, tipo_entidad: TipoEntidadEnum, entidad_id: int, data: DocumentoCreate
    ) -> Documento:
        with self._uow:
            if tipo_entidad not in _ENTIDADES_CON_DOCUMENTOS:
                raise DomainError(
                    f'tipo de entidad {tipo_entidad!r} no admite documentos'
                )
            contenido = data.contenido or b''
            existente = self._uow.documentos.get_by_hash(data.document_hash)
            if existente is not None:
                resultado: Documento = existente
            else:
                resultado = self._uow.documentos.save(
                    Documento(
                        document_hash=data.document_hash,
                        tipo=data.tipo,
                        nombre=data.nombre,
                        contenido=contenido,
                        tamanio=data.tamanio,
                        mime=data.mime,
                        descripcion=data.descripcion,
                    )
                )
            assert resultado is not None
            vinculo = EntidadDocumento(
                document_hash=data.document_hash,
                tipo_entidad=tipo_entidad,
                entidad_id=entidad_id,
            )
            vinculos = self._uow.entidad_documentos.list_by_entidad(
                tipo_entidad, entidad_id
            )
            if vinculo not in vinculos:
                self._uow.entidad_documentos.save(vinculo)
            self._uow.commit()
            return resultado


class DocumentoEliminar:
    """Remove a document from an entity.

    Deletes the link and, when the document has no remaining links anywhere,
    also deletes the document itself. Idempotent: missing links are no-ops.
    """

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(
        self, tipo_entidad: TipoEntidadEnum, entidad_id: int, document_hash: str
    ) -> None:
        with self._uow:
            if tipo_entidad not in _ENTIDADES_CON_DOCUMENTOS:
                raise DomainError(
                    f'tipo de entidad {tipo_entidad!r} no admite documentos'
                )
            self._uow.entidad_documentos.delete_by_entidad(
                tipo_entidad, entidad_id, document_hash
            )
            if self._uow.entidad_documentos.count_by_hash(document_hash) == 0:
                self._uow.documentos.delete_by_hash(document_hash)
            self._uow.commit()


class DocumentoListarPorEntidad:
    """List documents attached to an entity, newest first."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(
        self, tipo_entidad: TipoEntidadEnum, entidad_id: int
    ) -> list[Documento]:
        if tipo_entidad not in _ENTIDADES_CON_DOCUMENTOS:
            raise DomainError(f'tipo de entidad {tipo_entidad!r} no admite documentos')
        return self._uow.documentos.list_by_entidad(tipo_entidad, entidad_id)
