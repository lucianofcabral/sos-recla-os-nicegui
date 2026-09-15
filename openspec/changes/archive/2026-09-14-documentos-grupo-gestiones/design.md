# Design: Documentos a nivel de grupo y gestión en lotes 3 Arroyos

## Technical Approach

`LoteTresArrNuevo` currently saves raw `Documento`/`EntidadDocumento` rows keyed by hash and links every gestión doc to GRUPO — this raises `IntegrityError` on shared hashes and breaks the commit boundary. Fix: extract a pure, no-commit get-or-create helper shared by `DocumentoAdjuntar` and the lote use case; link group docs to GRUPO + each reclamo, per-gestión docs only to their reclamo. Enable GRUPO as a document entity. Add `documentos` to `LoteTresArrCreate`; extend the UI. No adapter/schema change.

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Atomicity vs. reuse | Extract module-level pure helper `adjuntar_documento(uow, tipo_entidad, entidad_id, data) -> Documento` (no `with`, no `commit`); `DocumentoAdjuntar` wraps it with `with self._uow` + `commit`; `LoteTresArrNuevo` calls it directly inside its own single `with self._uow` block | `DocumentoAdjuntar.__call__` owns a nested `with self._uow` + `commit()`; reusing it inside the lote transaction would commit mid-lote and break rollback. A pure helper honors the rule "use cases commit once, repos flush-only". |
| Group doc fan-out | Loop group docs once, linking to GRUPO and each reclamo id collected during the gestión loop | A group doc must be visible on GRUPO and every gestión (spec); one Documento row, N links. |
| Link dedupe | Reuse `EntidadDocumento` membership check against `list_by_entidad` (existing `DocumentoAdjuntar` logic) | Idempotent by hash + link; avoids `UniqueConstraint(document_hash, tipo_entidad, entidad_id)` violations. |
| GRUPO enablement | Add `TipoEntidadEnum.GRUPO` to `_ENTIDADES_CON_DOCUMENTOS` only | Repos already accept GRUPO as string; list/delete already type-agnostic. |

## Data Flow

```
LoteTresArrNuevo(uow)
  with uow:  ── one commit at end ──
    save Grupo ─→ grupo.id
    for gestión:
      save Reclamo ─→ reclamo.id   (collect ids)
      save TresArrReclamo
      per-gestión docs: adjuntar_documento(uow, RECLAMO, reclamo.id, d)
    group docs (data.documentos):
      adjuntar_documento(uow, GRUPO, grupo.id, d)
      for reclamo_id in ids:
        adjuntar_documento(uow, RECLAMO, reclamo_id, d)
    commit() ──→ atomic
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/application/use_cases/documento.py` | Modify | Add GRUPO to `_ENTIDADES_CON_DOCUMENTOS`; extract `adjuntar_documento`; refactor `DocumentoAdjuntar` to call it. |
| `src/application/use_cases/lote.py` | Modify | Replace raw `documentos.save`/`entidad_documentos.save` with `adjuntar_documento`; group docs → GRUPO + each reclamo; per-gestión docs → reclamo only. |
| `src/domain/dto/create.py` | Modify | Add `documentos: list[DocumentoCreate] = []` to `LoteTresArrCreate`. |
| `src/ui/dialogos.py` | Modify | Group dialog: `seccion_documentos(GRUPO, grupo_id)`. Lote dialog: separate group upload + per-gestión upload; editable pending gestión (row-click loads form; save updates row). |
| `tests/test_normalizacion_dominio.py` (or new `tests/test_documentos_grupo.py`) | Modify/Create | RED tests (below). |

## Interfaces / Contracts

```python
# src/application/use_cases/documento.py
def adjuntar_documento(
    uow: UnitOfWorkPort,
    tipo_entidad: TipoEntidadEnum,
    entidad_id: int,
    data: DocumentoCreate,
) -> Documento:
    """Get-or-create Documento by hash + idempotent EntidadDocumento link.
    No ``with``, no ``commit`` — caller owns the transaction boundary."""
```

```python
# src/domain/dto/create.py
class LoteTresArrCreate(BaseModel):
    grupo: str
    usuario_creacion: str | None = None
    gestiones: list[GestionLoteItem] = []
    documentos: list[DocumentoCreate] = []  # group-level
    generar_pagos: bool = True
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (FakeUnitOfWork) | Shared doc across gestiones commits once, one Documento row, links to GRUPO + each reclamo | RED first; assert `uow.committed`, `uow.documentos.list()` length, `list_by_entidad`. |
| Unit | Per-gestión doc links only to its reclamo; GRUPO/other gestión not visible | assert `list_by_entidad(RECLAMO, id)` membership. |
| Unit | Duplicate hash reuse creates no duplicate doc/link; GRUPO accepted by Adjuntar/Listar/Eliminar | reuse existing `DocumentoAdjuntar` tests extended to GRUPO. |
| UI (headless) | Group dialog renders `seccion_documentos(GRUPO)`; lote dialog shows two uploads + selectable/editable pending rows (no duplicate on save) | extend `tests/test_ui_widgets.py`. |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration required (schema/constraints unchanged; additive only). `git revert` restores prior behavior.

## Open Questions

- [ ] Should `documentos_adjuntados` count distinct documents or total links (group fan-out inflates link count)?
- [ ] Keep helper in `documento.py` (imported by `lote.py`) vs. a shared `_shared.py` module — prefer `documento.py` for cohesion.
