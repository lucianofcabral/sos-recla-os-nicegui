# Manual de despliegue — SOS Reclamos en Portainer

Este manual cubre el despliegue de la aplicación **SOS Reclamos** en un servidor con **Portainer**: la app y la base de datos Postgres corren en contenedores separados dentro de un mismo stack, con los datos persistidos en un volumen. También documenta qué pasa ante reinicios del servidor y cómo actualizar y respaldar.

## Quick path

1. Publicá la imagen en un registry: `docker build` + `docker push`.
2. Copiá `.env.example` a `.env` y ajustá `IMAGE` y `STORAGE_SECRET`.
3. En Portainer: **New stack** → pegá `docker-compose.prod.yml` + el contenido de `.env` en *Environment variables* (modo avanzado).
4. Deploy → esperá que `app` pase el healthcheck.
5. Creá el usuario admin con `bootstrap.py` desde la consola del contenedor.
6. Entrá a `http://<servidor>:<UI_PORT>` y validá.

## Prerrequisitos

- Docker (para build) y acceso a un registry Docker (Docker Hub, GHCR o uno privado).
- Servidor con Portainer (CE o EE) conectado al entorno Docker de producción.
- Repositorio del proyecto (para build local o para leer los archivos del stack).

## 1. Publicar la imagen

Portainer despliega por **imagen**, no por build context. La imagen se construye y se publica una vez, y el stack la baja en el server:

```sh
docker build -t <tu-registry>/sos-reclamos-nicegui:latest .
docker push <tu-registry>/sos-reclamos-nicegui:latest
```

Cada vez que quieras actualizar la versión, repetís estos dos pasos con un tag nuevo (p. ej. `:v1.1.0`).

## 2. Variables de entorno

Todas las variables salen de un archivo `.env` que el compose lee. El repo trae `.env.example` con valores random de referencia:

```sh
cp .env.example .env
```

| Variable | Ejemplo | Descripción | ¿Obligatoria? |
|----------|---------|-------------|---------------|
| `IMAGE` | `hub/sos-reclamos-nicegui:latest` | Imagen publicada que baja Portainer | Sí |
| `STORAGE_SECRET` | `14bfd7...0bf24` (hex 64) | Clave para firmar sesiones de NiceGUI | Sí — sin ella el stack no despliega (`:?`) |
| `POSTGRES_USER` | `sos` | Usuario de la base | No (default `sos`) |
| `POSTGRES_PASSWORD` | `ee56e1...9898db` (hex 32) | Password de Postgres | Sí, en producción no dejar el default |
| `POSTGRES_DB` | `sos_reclamos` | Nombre de la base | No (default `sos_reclamos`) |
| `UI_PORT` | `8081` | Puerto expuesto en el host (adentro el contenedor siempre escucha 8081) | No (default `8081`) |

Generá claves reales nuevas si las de ejemplo circularon en algún lado:

```sh
openssl rand -hex 32   # STORAGE_SECRET
openssl rand -hex 16   # POSTGRES_PASSWORD
```

> ⚠️ `.env` está en `.gitignore`: nunca se committea. `.env.example` sí se committea como plantilla.

## 3. Crear el stack en Portainer

1. En Portainer: **Stacks → Add stack** → nombre, p. ej. `sos-reclamos`.
2. **Build method**: *Web editor*.
3. Pegá el contenido de `docker-compose.prod.yml`.
4. Abrí **Environment variables** → **Advanced mode** y pegá el contenido de `.env` (o definí las variables una a una).
5. **Deploy the stack**.

El compose crea la red interna del stack (la app llega a la DB como `db:5432`), el volumen `sos_pgdata` para los datos y los healthchecks.

## 4. Primer arranque y verificación

El servicio `app` tiene `depends_on: condition: service_healthy`: espera a que Postgres responda antes de arrancar. Al iniciar, la app **crea el esquema sola** (idempotente) y escucha en `0.0.0.0:8081`.

Verificá en Portainer (Stacks → `sos-reclamos`):

- `db` → estado **healthy**.
- `app` → estado **healthy** (healthcheck HTTP a `127.0.0.1:8081`).
- Logs de `app` sin errores de conexión.

## 5. Crear el usuario admin

El stack no trae usuarios. Desde la consola del contenedor `app` (Containers → `sos-reclamos_app` → **Console**):

```sh
python scripts/bootstrap.py --username admin --password <tu-password>
```

> `bootstrap.py` vive dentro de la imagen (`scripts/` se copia en el build); no hace falta montar nada.

## Operación diaria

### Reinicio del servidor

Ambos servicios usan `restart: unless-stopped`:

- Al bootear, Docker levanta el stack solo, sin intervención.
- Los datos (reclamos, pagos, adjuntos) viven en el volumen `sos_pgdata` → **no se pierden**.
- La app reconecta a Postgres y regenera el esquema si faltara (idempotente).
- Único detalle: si el contenedor `app` se **recrea** (no solo reinicia), el directorio `.nicegui` (sesiones activas, tema) se pierde → los usuarios se desloguean. No se pierde ningún dato de negocio.

### Actualizar versión

1. `docker build` + `docker push` con el tag nuevo.
2. En Portainer: `sos-reclamos` → **Editor** → cambiá `IMAGE` al tag nuevo → **Update the stack**.
3. Esperá que ambos servicios queden *healthy*.

### Respaldo de la base

El stack solo persiste datos; no hace backups automáticos. Desde el host Docker:

```sh
docker exec sos-reclamos_db_1 pg_dump -U sos sos_reclamos > backup_$(date +%F).sql
```

Restore:

```sh
cat backup_2026-08-19.sql | docker exec -i sos-reclamos_db_1 psql -U sos sos_reclamos
```

> 📌 **Pendiente**: automatizar el backup (cron en el host o contenedor `pg_dump` con schedule) y rotación. Anotado para implementar más adelante.

## Importar la base legada (después del deploy)

La app trae una página de migración (**Migración**, solo ADMIN) para importar la base histórica desde la UI, sin entrar al contenedor. Incluye gestión, pagos, notas de crédito, facturas, periodos y adjuntos.

### Estructura fija del ZIP

```text
migracion.zip
├── gestiones.db          <- base SQLite legada (OBLIGATORIA, en la raíz)
└── files/
    └── docs/             <- adjuntos referenciados por la base (rutas `files\docs\...`)
```

Pasos:

1. Armá el ZIP con esa estructura (base en la raíz + carpeta `files/docs/`).
2. En la app: **Migración** → subí el ZIP o directamente una `.db`.
3. Desmarcado el checkbox, el botón **Importar** hace un *dry run* (solo cuenta). Marcado, pide confirmación y escribe.
4. El reporte muestra conteos por tipo y errores (p. ej. adjunto cuyo archivo no está en el ZIP).

Detalles:

- La importación es **idempotente**: re-correrla es un no-op para lo ya migrado (registro en `import_ledger`).
- El contenido de los adjuntos se guarda **en la base** (columna `contenido` de la tabla documentos), no en disco; la relación documento↔reclamo queda en la tabla de vínculos.
- Los adjuntos `files/docs/` pueden tener cualquier extensión (incluso `.db`); no se confunden con la base porque solo se busca la `.db` **en la raíz** del ZIP.
- Los documentos sin archivo presente en el ZIP se reportan como errores y se omiten; el resto de la importación continúa.

## Checklist de verificación

- [ ] La imagen está publicada en el registry y `IMAGE` apunta a ella.
- [ ] `.env` tiene `STORAGE_SECRET` y `POSTGRES_PASSWORD` reales (no los del ejemplo).
- [ ] El stack `sos-reclamos` existe con `app` y `db` en **healthy**.
- [ ] Entro a `http://<servidor>:8081` y veo la pantalla de login.
- [ ] El usuario admin creó y puede iniciar sesión.
- [ ] Reinicié el servidor una vez y el stack volvió solo, con los datos intactos.

## Referencias

- `docker-compose.prod.yml` — definición del stack (app + Postgres).
- `.env.example` — plantilla de variables.
- `Dockerfile` — build de la imagen.
- [`MANUAL_DE_USUARIO.md`](MANUAL_DE_USUARIO.md) — uso de la aplicación una vez desplegada.