# AGENTS.md — sos-reclamos-nicegui

## Status

App NiceGUI hexagonal completa y verde (235 tests). Capas: `src/domain` (entidades pydantic frozen, ports, excepciones), `src/application` (use cases con `UnitOfWorkPort`, commit explícito; queries de read-model), `src/adapters/sqlmodel` (9 `XxxRow` + repos que flush pero nunca commit), `src/infrastructure` (`SqlModelUnitOfWork`, `DATABASE_URL` Postgres con fallback SQLite), `src/ui` (login, home, pagos, periodos, migracion; consume `QueryPort` y use cases).

App: `uv run python -m src.ui.main` → http://127.0.0.1:8081 (`UI_HOST`/`UI_PORT`/`STORAGE_SECRET`; `scripts/bootstrap.py` crea el primer usuario). Import histórico: `scripts/import_old_db.py` (`--apply` escribe). Deploy: Dockerfile + `docker-compose.prod.yml` (Portainer) + README.md.

`PROMPT_INICIAL.md` es la spec de producto autoritativa (español).

## Commands

```sh
uv run pytest -q              # tests (235) — usar -q; tests/ui/ para cambios de UI
uv run ruff check .           # lint (E,W,F,I,N,UP,C4,SIM,RUF; E501 ignorado; 88 cols)
uv run ruff format .          # formato (single quotes)
```

## Token budget (obligatorio)

- Cargar la skill `.opencode/skills/sos-context/SKILL.md` (tool `skill`) cuando el trabajo toque dominio/negocio/UI/import. Contiene reglas de negocio, gotchas y arquitectura.
- Tests selectivos + `-q`; diffs acotados; `mem_search` en Engram antes de re-explorar; `mem_session_summary` al cerrar sesión.