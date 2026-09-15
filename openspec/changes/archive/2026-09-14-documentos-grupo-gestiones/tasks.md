# Tasks: Documentos a nivel de grupo y gestión en lotes 3 Arroyos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~450–600 (4 src files + tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (helper+DTO) → PR 2 (lote rewire) → PR 3 (UI) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Pure `adjuntar_documento` helper + GRUPO enabled + DTO field | PR 1 | `uv run pytest -q tests/test_use_cases_documento.py` | `uv run pytest -q` / `uv run ruff check .` | `documento.py`, `create.py`, `test_use_cases_documento.py` |
| 2 | Lote rewire to helper with group/per-gestión semantics | PR 2 (base PR 1) | `uv run pytest -q tests/test_use_cases_lote.py` | `uv run pytest -q` | `lote.py`, `test_use_cases_lote.py` |
| 3 | Group doc section + lote dialog split uploads + editable pending | PR 3 (base PR 2) | `uv run pytest -q tests/test_ui_seccion_documentos.py tests/test_ui_dialogos.py` | `uv run pytest -q` / `uv run ruff check .` | `dialogos.py`, UI tests |

## Phase 1: Foundation — helper + GRUPO + DTO

- [x] 1.1 RED `tests/test_use_cases_documento.py`: add failing test that `adjuntar_documento` persists without committing, and GRUPO attach/list/remove lifecycle.
- [x] 1.2 GREEN `src/application/use_cases/documento.py`: add `TipoEntidadEnum.GRUPO` to `_ENTIDADES_CON_DOCUMENTOS`.
- [x] 1.3 GREEN `src/application/use_cases/documento.py`: extract no-commit `adjuntar_documento(uow, tipo_entidad, entidad_id, data)`; refactor `DocumentoAdjuntar` to call it + own `with`/`commit`.
- [x] 1.4 RED `tests/test_use_cases_lote.py`: failing test that `LoteTresArrCreate.documentos` is accepted and group doc links GRUPO + each reclamo.
- [x] 1.5 GREEN `src/domain/dto/create.py`: add `documentos: list[DocumentoCreate] = []` to `LoteTresArrCreate`.

## Phase 2: Core — lote rewire

- [x] 2.1 RED `tests/test_use_cases_lote.py`: shared-hash doc across two gestiones commits once, one `Documento` row, one link per entity; per-gestión doc isolated from GRUPO/other gestión.
- [x] 2.2 GREEN `src/application/use_cases/lote.py`: collect `reclamo.id`s; replace raw `documentos.save`/`entidad_documentos.save` with `adjuntar_documento`; per-gestión docs → RECLAMO only; group docs → GRUPO + each reclamo; keep single `commit()`.
- [x] 2.3 GREEN `src/application/use_cases/lote.py`: set `documentos_adjuntados` = distinct hashes (deduped), not link count; update docstring.
- [x] 2.4 REFACTOR: `uv run ruff check . && uv run ruff format .`; prune now-unused `Documento`/`EntidadDocumento` imports.

## Phase 3: Wiring — UI

- [x] 3.1 RED `tests/test_ui_seccion_documentos.py`: GRUPO section renders attach/list (headless `user_simulation`).
- [x] 3.2 GREEN `src/ui/dialogos.py`: render `seccion_documentos(TipoEntidadEnum.GRUPO, grupo_id)` in `open_grupo_tres_arr`; update docstring.
- [x] 3.3 RED `tests/test_ui_dialogos.py`: lote dialog exposes separate group upload + per-gestión upload; selecting a pending gestión loads fields and save updates in place (no duplicate).
- [x] 3.4 GREEN `src/ui/dialogos.py`: add group-level upload feeding `LoteTresArrCreate.documentos`; keep per-gestión upload; row-click loads pending gestión into form and `_agregar_gestion` updates the selected index.
- [x] 3.5 GREEN `src/ui/dialogos.py`: render distinct doc counts per row and group-doc count.

## Phase 4: Verification

- [x] 4.1 `uv run pytest -q` full suite green (278).
- [x] 4.2 `uv run ruff check .` clean; refresh AGENTS.md status line if test count changes.
