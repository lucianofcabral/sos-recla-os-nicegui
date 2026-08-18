# SOS Reclamos — NiceGUI

Aplicación web para la gestión de reclamos, pagos, notas de crédito, periodos y documentos adjuntos de SOS, construida con Python 3.13, NiceGUI y una arquitectura hexagonal (domain / application / adapters / infrastructure / ui).

El **manual de usuario** con el paso a paso de cada caso de uso está en [`MANUAL_DE_USUARIO.md`](MANUAL_DE_USUARIO.md).

## Requisitos

- Python 3.13
- [uv](https://docs.astral.sh/uv/) para gestión de dependencias
- Docker (opcional, para Postgres y despliegue)

## Setup y ejecución local

```sh
uv sync
uv run python scripts/bootstrap.py --username admin --password <tu-password>
uv run python -m src.ui.main
```

La app queda en http://127.0.0.1:8081 (configurable con `UI_HOST` / `UI_PORT`; `STORAGE_SECRET` firma las sesiones).

Por defecto usa SQLite (`sos.db`). Para usar Postgres local:

```sh
docker compose up -d                   # levanta solo la DB (postgres:16-alpine)
export DATABASE_URL="postgresql+psycopg://sos:sos@localhost:5432/sos_reclamos"
uv run python scripts/import_old_db.py --apply   # import histórico (opcional)
uv run python -m src.ui.main
```

## Tests y lint

```sh
uv run pytest       # 252 tests (app, repos, UoW; integración Postgres vía testcontainers si hay Docker)
uv run ruff check .
uv run ruff format .
```

## Docker

### Build e imagen

```sh
docker build -t sos-reclamos-nicegui:latest .
# y para publicar en un registry:
docker push <hub>/sos-reclamos-nicegui:latest
```

La imagen expone el puerto 8081 y arranca con `python -m src.ui.main`. Requiere la variable `STORAGE_SECRET`; la DB se configura vía `DATABASE_URL`.

### Deploy en Portainer

`docker-compose.prod.yml` define el stack completo (app + Postgres). En Portainer: **New stack** → pegar el contenido (o apuntar al archivo) → definir al menos `STORAGE_SECRET` y `IMAGE` (el nombre de tu imagen publicada):

```yaml
IMAGE=hub/sos-reclamos-nicegui:latest
STORAGE_SECRET=una-clave-secreta-larga
```

Primer arranque: la app crea el esquema sola; creá el usuario admin con:

```sh
docker compose -f docker-compose.prod.yml exec app python scripts/bootstrap.py --username admin --password <tu-password>
```

## Especificación

`PROMPT_INICIAL.md` es la especificación de producto autoritativa (páginas, campos y reglas de negocio). `MANUAL_DE_USUARIO.md` es el [manual de usuario](MANUAL_DE_USUARIO.md) con los casos de uso paso a paso.
