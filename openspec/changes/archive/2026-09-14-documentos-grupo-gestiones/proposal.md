# Proposal: Documentos a nivel de grupo y gestión en lotes 3 Arroyos

## Intent

In the "Nueva 3 Arroyos" lote flow, uploading documents fails. `LoteTresArrNuevo` links every gestión's documents to the GRUPO without hash dedupe. Because `documentos.document_hash` is UNIQUE and `entidad_documento` has `UniqueConstraint(document_hash, tipo_entidad, entidad_id)`, a document shared by two gestiones in the same lote raises `IntegrityError` and rolls back the whole lote. GRUPO is also missing from `_ENTIDADES_CON_DOCUMENTOS`, so there is no group-level document UI, no per-gestión attachment, and no way to select a pending gestión to edit its fields. Product behavior extends the 3 Arroyos lote upload already described in PROMPT_INICIAL.md.

## Scope

### In Scope
- Group-level documents link to GRUPO and to each RECLAMO created in the lote.
- Per-gestión documents link only to that RECLAMO.
- Hash + link dedupe on attach.
- Enable `TipoEntidadEnum.GRUPO` in `_ENTIDADES_CON_DOCUMENTOS`.
- `documentos: list[DocumentoCreate]` on `LoteTresArrCreate`.
- Group-doc upload + per-gestión upload + editable pending gestiones in the lote dialog.
- `seccion_documentos(GRUPO, grupo_id)` in the group dialog.

### Out of Scope
- Historical import (`import_gestiones.py`).
- Re-uploading a pending gestión's documents (fields only).

## Capabilities

### New Capabilities
- `documentos-grupo-gestiones`: document linking semantics (group + per-gestión), hash/link dedupe, and GRUPO entity document support.

### Modified Capabilities
None (`openspec/specs/` is empty).

## Approach

Reuse `DocumentoAdjuntar` (already does `get_by_hash` + link dedupe) inside `LoteTresArrNuevo` instead of raw `documentos.save`/`entidad_documentos.save`. Add GRUPO to `_ENTIDADES_CON_DOCUMENTOS`. Add group-level `documentos` to `LoteTresArrCreate`. In the UI, separate group-doc upload from per-gestión upload, and make pending rows selectable to load fields into the form for edit (fields only). Layers: application, domain (DTO), ui; no adapter schema change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/application/use_cases/lote.py` | Modified | Attach docs via `DocumentoAdjuntar`; group docs to GRUPO + each reclamo |
| `src/application/use_cases/documento.py` | Modified | Add GRUPO to `_ENTIDADES_CON_DOCUMENTOS` |
| `src/domain/dto/create.py` | Modified | Add `documentos` to `LoteTresArrCreate` |
| `src/ui/dialogos.py` | Modified | Group-doc upload, per-gestión upload, editable pending gestiones, group `seccion_documentos` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Duplicate link still raised before dedupe lands | Med | Unit tests on shared-doc lote |
| Group docs bloated when many gestiones | Low | Dedupe by hash; links only |
| Editing UI breaks existing lote save path | Med | UI tests for create and edit modes |

## Rollback Plan

Revert the change-folder commits; `DocumentoAdjuntar` changes are additive. No schema migration (constraints unchanged), so `git revert` restores prior behavior; no data to migrate.

## Dependencies

None.

## Success Criteria

- [ ] Shared document across gestiones in one lote creates no `IntegrityError`; lot commits once.
- [ ] Group docs visible at GRUPO and on each gestión; per-gestión docs only on that gestión.
- [ ] `uv run pytest -q` green; `uv run ruff check .` clean.
