# Archive Report: documentos-grupo-gestiones

**Change**: documentos-grupo-gestiones
**Archived**: 2026-09-14
**Archived to**: `openspec/changes/archive/2026-09-14-documentos-grupo-gestiones/`
**Store mode**: openspec
**Cycle status**: COMPLETE

## Final State Summary

| Metric | Final value | Source |
|--------|-------------|--------|
| Implementation tasks | 16/16 complete (`[x]`) | `tasks.md` (persisted, Task Completion Gate) |
| Verification verdict | PASS WITH WARNINGS (0 CRITICAL, 0 blockers) | `verify-report.md` |
| Requirements | 9/9 covered | `verify-report.md` |
| Scenarios | 11/11 compliant | `verify-report.md` |
| Tests | 278 passed, 0 failed, 0 skipped | `uv run pytest -q` |
| Lint | `uv run ruff check .` clean | `uv run ruff check .` |
| New tests | 15 (12 unit + 3 UI integration) | `verify-report.md` |

## Task Completion Gate

Passed. `tasks.md` contains zero unchecked implementation tasks — all 16 tasks
(Phases 1–4) are marked `[x]`. No stale-checkbox reconciliation was required.

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| `documentos-grupo-gestiones` | Created | 9 requirements ADDED, 0 modified, 0 removed (11 scenarios) |

`openspec/specs/documentos-grupo-gestiones/spec.md` did not exist, so the delta
spec was a full spec. It was copied mechanically with the shell (`cp`) — never
via model Read/Write — and verified byte-identical.

**Source of truth updated**: `openspec/specs/documentos-grupo-gestiones/spec.md`
(sha256 `714f913f6cdbfd724ccc5bb15372bffbd714dc402cdb4e9e96f3ca04a05adcc8`).

### Resolved Design Open Question (delta-spec note)

Design open question #1 was resolved during implementation (task 2.3):
`documentos_adjuntados` is the count of **DISTINCT document hashes (deduped)**,
**not** the total link count. Group-document fan-out (one document linked to
GRUPO plus every gestión) therefore does not inflate the reported count.
`verify-report` SUGGESTION #2 asked that this semantics be captured at archive
time — it is recorded here.

## Archive Contents

- [x] `proposal.md`
- [x] `specs/documentos-grupo-gestiones/spec.md`
- [x] `design.md`
- [x] `tasks.md` (16/16 tasks complete)
- [x] `apply-progress.md`
- [x] `verify-report.md`
- [x] `archive-report.md` (this file, additive)

## Mechanical Copy Readback (verbatim)

Step 2 — delta spec → main spec (`diff -r` source vs staged copy, then installed):

```text
=== diff -r (delta spec vs staged copy) ===
=== end diff (exit 0) ===
```

Post-install byte-identity check:

```text
=== final diff -r (source delta spec vs installed main spec) ===
=== end diff (exit 0) ===
```

Step 3 — change folder → archive (`diff -r` pre-move snapshot vs archived tree):

```text
=== diff -r (pre-move snapshot vs unchanged source after git mv failure) ===
=== end diff (exit 0) ===
moved via plain mv
=== diff -r (pre-move snapshot vs archived tree) ===
=== end diff (exit 0) ===
```

All `diff -r` outputs are empty — the only passing evidence. The change folder
was untracked in git (`?? openspec/`), so `git mv` was unavailable and the
fallback plain `mv` was used after confirming the source was unchanged.

## Post-Archive Verification

- [x] Main spec updated correctly
- [x] Change folder moved to archive
- [x] Archive contains all artifacts (proposal, specs, design, tasks, apply-progress, verify-report)
- [x] Archived `tasks.md` has no unchecked implementation tasks
- [x] Active changes directory no longer contains this change
- [x] Verbatim `diff -r` readback included and empty

## Warnings Carried Forward (accurate final state)

1. **`opencode.json` deleted in the working tree — PRE-EXISTING / OUT OF SCOPE.**
   `git status --porcelain` reports ` D opencode.json`; the file was last
   committed at `dc14a9d` and the deletion was already present **before this SDD
   cycle began**. It is NOT a defect introduced by this change and is not part of
   its delivery. It remains an unexplained working-tree deletion that belongs to
   whoever deleted it; recorded here for audit only. (This corresponds to
   WARNING #1 in `verify-report.md`, which noted it was not listed in
   `apply-progress.md` Files Changed and was out of scope.)
2. **SUGGESTION (verify-report)**: `tests/test_use_cases_lote.py::test_lote_create_acepta_documentos_de_grupo`
   is a shallow DTO-presence assertion; real behavior is covered by
   `test_lote_mezcla_documento_de_grupo_y_por_gestion`. Non-blocking.

No CRITICAL issues. No blockers. No unresolved contradictions between sources.

## Files Changed By This Change

- `src/application/use_cases/documento.py` — GRUPO enablement + pure `adjuntar_documento` helper
- `src/application/use_cases/lote.py` — doc attach rewire; group/per-gestión semantics; distinct-hash count
- `src/domain/dto/create.py` — `LoteTresArrCreate.documentos`
- `src/ui/dialogos.py` — group doc section, split uploads, editable pending gestión
- `tests/test_use_cases_documento.py`, `tests/test_use_cases_lote.py`, `tests/test_ui_dialogos.py`, `tests/test_ui_seccion_documentos.py`
- `AGENTS.md` — test count refreshed to 278

## SDD Cycle Complete

The change was proposed, specified, designed, implemented, verified, and
archived. Source of truth for the new capability now lives in
`openspec/specs/documentos-grupo-gestiones/spec.md`. Ready for the next change.
