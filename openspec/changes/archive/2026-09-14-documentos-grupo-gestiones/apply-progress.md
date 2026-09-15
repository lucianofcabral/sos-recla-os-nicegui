# Apply Progress: documentos-grupo-gestiones

## Status

- **Status**: `ok` (all 16 tasks complete; verify/archive are orchestrator-owned)
- **Mode**: Strict TDD (RED → GREEN → TRIANGULATE → REFACTOR)
- **Artifact store**: openspec
- **Test runner**: `uv run pytest -q`
- **Baseline (safety net)**: 263 passed / `uv run ruff check .` clean
- **Final**: 278 passed / `uv run ruff check .` clean / `uv run ruff format --check .` clean
- **First apply batch** — no previous apply-progress existed.

## Completed Tasks

All 16 tasks in `tasks.md` marked `[x]`: 1.1–1.5, 2.1–2.4, 3.1–3.5, 4.1–4.2.

## Files Changed

| File | Action | Insertions | Deletions |
|------|--------|-----------:|----------:|
| `src/application/use_cases/documento.py` | Modify — extract `adjuntar_documento`, add GRUPO | 49 | 33 |
| `src/domain/dto/create.py` | Modify — `LoteTresArrCreate.documentos` | 1 | 0 |
| `src/application/use_cases/lote.py` | Modify — rewire to helper, group/per-gestión semantics | 22 | 26 |
| `src/ui/dialogos.py` | Modify — GRUPO section, split uploads, editable pending | 123 | 16 |
| `tests/test_use_cases_documento.py` | Modify — +3 tests | 38 | 0 |
| `tests/test_use_cases_lote.py` | Modify — +5 tests, update old GRUPO-link assertion | 143 | 2 |
| `tests/test_ui_seccion_documentos.py` | Modify — +2 headless render tests | 61 | 1 |
| `tests/test_ui_dialogos.py` | Modify — +5 tests (helpers + render) | 53 | 0 |
| `AGENTS.md` | Modify — test count 235 → 278 | 2 | 2 |
| **Total (tracked)** | | **492** | **80** |

`openspec/changes/documentos-grupo-gestiones/tasks.md` checkboxes updated (untracked `openspec/` tree).

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_use_cases_documento.py` | Unit | ✅ 9/9 | ✅ Written — 3 failed (helper AttributeError + GRUPO DomainError) | ✅ after 1.3 → 12 passed | ✅ 3 cases (helper no-commit, hash reuse, GRUPO lifecycle) | ✅ module-alias import → direct import |
| 1.2 | `tests/test_use_cases_documento.py` | Unit | ✅ 9/9 | ➖ GREEN task | ✅ `-k grupo` 1 passed | ✅ GRUPO attach/list/remove | ✅ |
| 1.3 | `tests/test_use_cases_documento.py` | Unit | ✅ 9/9 | ✅ (1.1 helper tests) | ✅ 12 passed | ✅ 2 helper cases | ✅ |
| 1.4 | `tests/test_use_cases_lote.py` | Unit | ✅ 6/6 | ✅ Written — 2 failed (DTO `documentos`, group link) | ✅ DTO 7 passed; group-link deferred to 2.2 | ✅ 2 cases | ➖ |
| 1.5 | `tests/test_use_cases_lote.py` | Unit | ✅ 6/6 | ✅ (1.4) | ✅ 7 passed / 1 deferred | ✅ | ✅ |
| 2.1 | `tests/test_use_cases_lote.py` | Unit | ✅ 7/7 | ✅ Written — 5 failed | ✅ after 2.2 → 11 passed | ✅ 4 cases (shared, isolation, mixed, old-test update) | ➖ |
| 2.2 | `tests/test_use_cases_lote.py` | Unit | ✅ 7/7 | ✅ (2.1) | ✅ 11 passed | ✅ shared hash / per-gestión isolation / mixed kinds | ✅ |
| 2.3 | `tests/test_use_cases_lote.py` | Unit | ✅ 7/7 | ✅ (2.1) | ✅ distinct-hash assertions pass (`==1`, `==2`) | ✅ 2 cases | ✅ docstring |
| 2.4 | — | Refactor/Lint | ✅ 11/11 | ➖ | ✅ `ruff check .` clean | ➖ | ✅ pruned `Documento`/`EntidadDocumento` imports |
| 3.1 | `tests/test_ui_seccion_documentos.py` | Integration (headless NiceGUI) | ✅ 1/1 | ✅ Written — group dialog test failed | ✅ after 3.2 → 3 passed | ✅ 3 render cases (RECLAMO, GRUPO, dialog) | ➖ |
| 3.2 | `tests/test_ui_seccion_documentos.py` | Integration | ✅ 1/1 | ✅ (3.1) | ✅ 3 passed | ✅ | ✅ docstring |
| 3.3 | `tests/test_ui_dialogos.py` | Unit + Integration | ✅ 3/3 | ✅ Written — 5 failed | ✅ after 3.4 → 8 passed | ✅ 5 cases (upsert append, upsert update, dedupe 2, dedupe 0, render) | ➖ |
| 3.4 | `tests/test_ui_dialogos.py` | Unit + Integration | ✅ 3/3 | ✅ (3.3) | ✅ 8 passed | ✅ append/update + two uploads rendered | ✅ |
| 3.5 | `tests/test_ui_dialogos.py` | Unit | ✅ 3/3 | ✅ (3.3) | ✅ 8 passed | ✅ distinct count 2 and 0 | ✅ |
| 4.1 | full suite | Integration | ✅ 263 | ➖ | ✅ 278 passed | ➖ | ➖ |
| 4.2 | — | Lint/Docs | ✅ 263 | ➖ | ✅ `ruff check .` clean | ➖ | ✅ AGENTS.md count refreshed |

### Test Summary

- **Total tests written**: 15 (12 unit, 3 headless integration)
- **Total tests passing**: 278 (baseline 263)
- **Layers used**: Unit 12, Integration (headless NiceGUI `user_simulation`) 3, E2E 0
- **Approval tests** (refactoring): 1 — `test_lote_crea_grupo_gestiones_pagos_y_documentos` updated to the NEW per-gestión semantics (old single-GRUPO-link assertion changed per spec)
- **Pure functions created**: 3 — `adjuntar_documento` (no `with`/`commit`), `_upsert_gestion`, `_contar_documentos_distintos`

## Work Unit Evidence

| Unit (PR) | Focused test command | Exact result | Runtime harness | Exact result | Rollback boundary |
|-----------|----------------------|--------------|-----------------|--------------|-------------------|
| 1 (PR1) helper + GRUPO + DTO | `uv run pytest -q tests/test_use_cases_documento.py` | ✅ `12 passed in 0.09s` | `uv run pytest -q` + `uv run ruff check .` | ✅ `278 passed` / `All checks passed!` | `src/application/use_cases/documento.py`, `src/domain/dto/create.py`, `tests/test_use_cases_documento.py` |
| 2 (PR2) lote rewire | `uv run pytest -q tests/test_use_cases_lote.py` | ✅ `11 passed in 0.08s` | `uv run pytest -q` | ✅ `278 passed` | `src/application/use_cases/lote.py`, `tests/test_use_cases_lote.py` |
| 3 (PR3) UI + verification | `uv run pytest -q tests/test_ui_seccion_documentos.py tests/test_ui_dialogos.py` | ✅ `11 passed in 1.27s` | `uv run pytest -q` + `uv run ruff check .` | ✅ `278 passed` / `All checks passed!` | `src/ui/dialogos.py`, `tests/test_ui_seccion_documentos.py`, `tests/test_ui_dialogos.py`, `AGENTS.md` |

## Deviations From Design

1. **Task 3.1 RED targets the dialog wiring, not a bare GRUPO section render.** GRUPO enablement landed in Phase 1, so a bare `seccion_documentos(GRUPO)` render test was already green. The genuine RED was `test_dialogo_grupo_muestra_seccion_documentos` (group dialog did not render the section until 3.2). A direct `seccion_documentos(GRUPO)` render test was kept as triangulation.
2. **Task 1.4's group-link assertion goes GREEN in 2.2, not 1.5.** 1.5 only adds the DTO field; the lote use case processes `data.documentos` in 2.2. The 1.5 GREEN is verified by `test_lote_create_acepta_documentos_de_grupo`.
3. **Two extra pure UI helpers extracted** (`_upsert_gestion`, `_contar_documentos_distintos`) so "edit pending in place, no duplicate" and "distinct doc counts" are unit-testable without mocks, per the strict-TDD Extract-Before-Mock rule. This is additive to the design's UI wiring, not a behavior change.
4. **Unrelated ruff-format churn reverted.** Running `uv run ruff format .` reformatted three files outside scope (`src/ui/layout.py`, `src/ui/theme.py`, `tests/test_queries_sqlite.py`); they were restored with `git checkout` so the change stays scoped.
5. **`AGENTS.md` test count was already stale** (said 235; real baseline 263). Updated to 278 (post-change), satisfying task 4.2.

## Issues Found

- `tasks.md`/`AGENTS.md` forecast "235 + new"; actual pre-change baseline was 263. Corrected in AGENTS.md.
- No schema/migration impact: `TipoEntidadEnum.GRUPO` already existed and repos accept it; only `_ENTIDADES_CON_DOCUMENTOS` gating changed.
- No circular import: `lote.py` → `documento.py` → domain only.

## Remaining Tasks

None. All 16 tasks complete. `verify` and `archive` phases are owned by the orchestrator (native status still marks them `blocked` pending verify).

## Workload / PR Boundary

- **Total changed lines (my files)**: 572 (492 insertions + 80 deletions) — over the 400-line budget.
- **Per unit**: Unit 1 = 121, Unit 2 = 193, Unit 3 = 258 — each under 400.
- **Recommendation**: `size:exception` — the delivery decision already resolved Chained PRs `stacked-to-main`; commit the three cohesive work units separately as planned (helper/DTO → lote → UI+verification). No branches or commits were created.

## Final Summary

Extracted a pure, no-commit `adjuntar_documento` helper shared by `DocumentoAdjuntar` and `LoteTresArrNuevo`; enabled `TipoEntidadEnum.GRUPO`; added group-level `documentos` to `LoteTresArrCreate`. The lote use case now links per-gestión docs only to their reclamo and group docs to the GRUPO plus every reclamo, dedupes by hash, and counts `documentos_adjuntados` as distinct hashes — all inside one atomic commit. The UI exposes a GRUPO document section in the group dialog, separate group/per-gestión uploads in the lote dialog, and selectable pending gestiones that update in place. Strict TDD followed throughout; full suite 278 passed, ruff clean.
