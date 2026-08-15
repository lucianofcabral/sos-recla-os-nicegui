# AGENTS.md — sos-reclamos-nicegui

## Status

Domain, application, persistence and UI layers are in place and green (108 tests), plus the historical import from the legacy DB.

- `src/domain` — frozen pydantic entities (`Periodo`, `Reclamo`, `ReclamoSos`, `TresArrReclamo`, `OtrosReclamo`, `Pago`, `CreditNote`, `Factura`, `User`, ...), StrEnums, exceptions (`DomainError`, `EntityNotFoundError`, `DuplicateEntityError`), repo ports (`src/domain/ports/repositories.py`, `typing.Protocol`) and `UnitOfWorkPort` (`src/domain/ports/unit_of_work.py`). In-memory fakes live in `tests/fakes/` with a contract test.
- `src/application/` — use cases (**reclamos**, **pagos + nota de crédito**, **auth**, `PeriodoNuevo`, `FacturaNueva`, `ReclamoAlternarEstado`), read-model queries (`queries.py`: `list_home`, `list_pagos_con_detalle`, `list_ciclos`), ARS formatting helpers (`format.py`), and the historical importer (`import_gestiones.py`: pure mapping helpers + idempotent pipeline from the legacy DB). Use case classes use Spanish names (e.g. `SosReclamoNuevo`), receive a `UnitOfWorkPort`, and the **commit is explicit inside each use case**.
- `src/adapters/sqlmodel/` — `models.py` (9 `XxxRow` tables + `to_entity`/`from_entity`), `repositories.py` (9 `SqlModel*` repos implementing the ports).
- `src/infrastructure/` — `database.py` (engine/session helpers) and `unit_of_work.py` (`SqlModelUnitOfWork`). Both UoWs (fake + SQLModel) implement `QueryPort` (`src/domain/ports/queries.py`) via `list_home`, `list_pagos_con_detalle`, `list_ciclos`; the UI consumes those, not raw repos.
- `src/ui/` — NiceGUI app: `deps.py` (per-request `uow_per_request()`, session helpers), `layout.py` (`page()` decorator + shell with dark/light toggle), `pages/login.py`, `pages/home.py`, `pages/pagos.py`, `pages/ciclos.py`, `main.py` entrypoint (`uv run python -m src.ui.main`).
- Tests: app-layer suites with fakes, repo suites against in-memory SQLite, UoW rollback/commit tests, and Postgres integration tests via testcontainers (`tests/integration/`, skipped if Docker is missing).

Still missing: `README.md`, Dockerfile, git repo/CI. The app **runs**: `uv run python scripts/bootstrap.py --username admin --password ...` creates the first user, then `uv run python -m src.ui.main` serves http://127.0.0.1:8080 (login required; `UI_HOST`/`UI_PORT`/`STORAGE_SECRET` env vars, default dev secret). Historical import: `uv run python scripts/import_old_db.py` (dry-run by default, `--apply` writes; target DB via `DATABASE_URL` or sqlite dev; legacy DB path `--old-db`, default `/home/fexa/sos-viejo/reclamos/gestiones.db`).

### Local PostgreSQL (docker compose)

`docker-compose.yml` runs `postgres:16-alpine` as `sos-postgres` (user/pass/db `sos`/`sos`/`sos_reclamos`, host port 5432, named volume `sos_pgdata`, healthcheck `pg_isready`). Start: `docker compose up -d`. The container currently holds the full historical import + bootstrap user `admin`.

- **Import directo a Postgres** (no via SQLite): `DATABASE_URL="postgresql+psycopg://sos:sos@localhost:5432/sos_reclamos" uv run python scripts/import_old_db.py --apply`
- **Bootstrap**: `DATABASE_URL="postgresql+psycopg://sos:sos@localhost:5432/sos_reclamos" uv run python scripts/bootstrap.py --username admin --password ...`
- **Run app against Postgres**: `DATABASE_URL="postgresql+psycopg://sos:sos@localhost:5432/sos_reclamos" uv run python -m src.ui.main`
- **Migrate a dev SQLite into Postgres**: `scripts/migrate_sqlite_to_postgres.py` (dry-run by default; `--apply` writes; `--force` truncates populated dest tables; preserves IDs and re-syncs sequences). Verified E2E: 1076 reclamos/613 SOS/324 tres_arr/139 otros/1068 pagos/265 NC/40 facturas/40 periodos, 0 orphaned FKs.
- Reset the DB: `docker compose down -v && docker compose up -d`, then re-import + bootstrap.

`PROMPT_INICIAL.md` is the authoritative product spec (Spanish). Read it before adding features; it defines the pages, fields, and business rules.

## Toolchain

- Python 3.13, dependencies managed with **uv** (`.venv` + `uv.lock`).
- Runtime deps: `pydantic`, `sqlmodel`, `psycopg`, `bcrypt`, `nicegui` (3.16).
- Dev deps: `pytest`, `ruff`, `testcontainers[postgres]`.

## Commands

```sh
uv run pytest                      # tests (testpaths=tests; 108 tests)
uv run ruff check .                # lint
uv run ruff format .               # format (single quotes, 88 cols — matches pyproject)
```

Ruff: select `E,W,F,I,N,UP,C4,SIM,RUF`, `E501` ignored, line-length = 88, quote-style single (see `pyproject.toml`).

## Architecture (hexagonal, enforced by spec)

- `src/domain` — entities (frozen pydantic `BaseModel`), `StrEnum`s, ports, exceptions, DTOs. Domain naming is **Spanish** (Póliza, dominio, anio_mes, nro_gestion) and DTOs use `*Create`/`*Edit` suffixes (`UserCreate`, `ReclamoSosEdit`, ...). Layer/file names are English. Follow both.
- `src/application` — use cases receive a `UnitOfWorkPort`, **never ORM models**. Commit is explicit inside each use case; leaving the context only rolls back. Reclamo use cases return the **typed child entity** with the base `Reclamo` embedded (`.reclamo`) after updates; `delete`/`borrar` for reclamos = soft delete (`set_active(False)`), hard delete exists only for pagos.
- `src/adapters/sqlmodel` — SQLModel row models (`XxxRow`) + repositories. Repos **flush but never commit**; enums are stored as `str` and mapped to StrEnums in `to_entity`.
- `src/infrastructure` — `SqlModelUnitOfWork` (explicit `commit()`; `__exit__` always rolls back and closes). Engine/session from `DATABASE_URL` (Postgres, e.g. `postgresql+psycopg://`) falling back to `sqlite:///sos.db` for dev. Schema via `create_all` — no Alembic yet.
- `src/ui` — NiceGUI pages (login, home, pagos, ciclos) + `deps.py`/`layout.py`/`main.py`. UI consumes `QueryPort` queries and use cases only.
- List queries must avoid N+1 (the `QueryPort` implementations use fixed join/`in_`/`GROUP BY` queries — keep it that way).

## Domain business rules (decided, keep them)

- `nro_gestion` is **required** when creating a SOS reclamo.
- `PagoNuevo` validates `monto > 0` and `pagador != destinatario`; for `forma_pago == NOTA_DE_CREDITO` the actors are **forced** to `pagador=SOS` / `destinatario=SM` and the `CreditNote` is **auto-created** (periodo `None`; asignado después con `AsignarNotaCreditoAPeriodo`). `PagoBorrar` rejects NC payments (`NotaCreditoBorrar` handles them). `CreditNoteCreate` DTO exists for future use; the UC path is `PagoNuevo`.
- `OtrosReclamo` was eliminated (user decision): OTROS/Gestión reclamos have NO child entity or table — they are plain `reclamos` rows with `tipo_reclamo == TipoReclamoEnum.OTROS` ('Otros'). `TresArrReclamo` keeps `grupo` (import groups by `fecha`). Keep it that way: do NOT re-introduce an OTROS child table.
- Auth: only `ADMIN` actors may create users; passwords are bcrypt-hashed; `AutenticarUsuario` returns a generic "usuario o contraseña inválidos" error and rejects inactive users.

## Gotchas

- Resolved: `src/domain/ports/repos/` was deleted; repo ports live in `src/domain/ports/repositories.py`. Still duplicated: `src/adapters/logging/` vs `src/infrastructure/logging/` — pick one per concern and delete the other rather than adding to both.
- **SQLModel 0.0.39**: do NOT use `from __future__ import annotations` in `models.py` — forward-ref relationships break `configure_mappers`/`selectinload`. Use classic forward refs (`Optional['X']`/`list['X']`).
- **testcontainers**: use `PostgresContainer` from `testcontainers.community.postgres` with `get_connection_url(driver='psycopg')` (the default psycopg2 driver breaks with psycopg 3).
- `FakePagoRepository.save` and `SqlModelPagoRepository.save` **upsert by id** (the ports' `update` exists for reclamos/sos/tres/credit_notes; pagos update via `save`).
- `pyproject.toml` references `README.md` but it does not exist. Create it when documenting setup/deploy (Docker) per the spec.
- No git repo, no CI, no Dockerfile yet. Docker compose exists only for the DB (`docker-compose.yml`), not for the app.
- Dev DB artifact `sos.db` is created by default when running against SQLite; add to `.gitignore` once git is initialized.
- **Legacy import**: do NOT read/write the old DB's `aux_*` tables — they are pre-filled by a previous migration of the old app and would swallow ~99% of records. The importer keeps its own `import_ledger` table in the destination DB (created by `src/infrastructure/import_ledger.py`) for idempotency. Import mapping rule: old `ngestion > 0` → SOS; `ngestion = 0` grouped by `fecha` → TresArr (`grupo=fecha`); `ngestion = 0` alone on a date → OTROS. Old `tipo` column is ignored.
- Integration tests target Postgres via testcontainers — **Docker required** (skipped if absent). App/repo tests use fakes or in-memory SQLite.
- Money format is Argentine: thousands `.`, decimals `,`, two decimals.
- UI: dark theme by default with per-user light/dark toggle (stored in `app.storage.user['theme']`, NOT in the DB). **NiceGUI 3.16** renamed `ui.dark(...)` → `ui.dark_mode` element (`.set_value`); tables use scoped slots (`add_slot('body-cell-X')` + `js_handler`) for row-action buttons. `ui.run` must stay under `if __name__ == '__main__':` so imports don't start the server.