---
name: sos-context
description: Contexto de negocio y gotchas del proyecto sos-reclamos-nicegui. Cargar al tocar reclamos, pagos, notas de crédito, periodos, import histórico o la capa UI/arquitectura.
---

# Contexto de negocio y arquitectura — sos-reclamos-nicegui

## Spec de producto

`PROMPT_INICIAL.md` es la especificación autoritativa (páginas, campos, reglas de negocio). Leer las secciones relevantes ANTES de agregar features.

## Reglas de negocio (decididas, mantenerlas)

- `nro_gestion` es **obligatorio** al crear un reclamo SOS.
- `PagoNuevo` valida `monto > 0` y `pagador != destinatario`; con `forma_pago == NOTA_DE_CREDITO` los actores se fuerzan a `pagador=SOS` / `destinatario=SM` y la `CreditNote` se **auto-crea** (periodo `None`; se asigna después con `AsignarNotaCreditoAPeriodo`). `PagoBorrar` rechaza pagos NC (`NotaCreditoBorrar` los maneja).
- `OtrosReclamo` fue eliminado por decisión de usuario: los reclamos OTROS/Gestión son filas planas `reclamos` con `tipo_reclamo == 'Otros'`. NO reintroducir tabla hija OTROS. `TresArrReclamo` conserva `grupo` (el import agrupa por `fecha`).
- Auth: solo `ADMIN` crea usuarios; passwords bcrypt; `AutenticarUsuario` da error genérico "usuario o contraseña inválidos" y rechaza inactivos.
- Dinero formato argentino: miles `.`, decimales `,`, dos decimales.

## Arquitectura (hexagonal)

- `src/domain` — entidades pydantic frozen, StrEnums, ports, excepciones, DTOs `*Create`/`*Edit`. Naming de dominio en español (Póliza, dominio, anio_mes, nro_gestion); nombres de capa/archivo en inglés.
- `src/application` — use cases reciben `UnitOfWorkPort`, nunca ORM. Commit explícito dentro de cada use case. Reclamos: `delete`/`borrar` = soft delete (`set_active(False)`); hard delete solo para pagos. Update de reclamos devuelve la entidad hija tipada con `.reclamo` embebido.
- `src/adapters/sqlmodel` — modelos `XxxRow` + repos. Repos **flush pero nunca commit**; enums como `str` mapeados a StrEnums en `to_entity`.
- `src/infrastructure` — `SqlModelUnitOfWork` (commit explícito; `__exit__` siempre rollback+close). Engine desde `DATABASE_URL` (Postgres) con fallback `sqlite:///sos.db`. Schema con `create_all` — sin Alembic.
- `src/ui` — NiceGUI; consume `QueryPort` y use cases, no repos crudos.
- Las queries de listado deben evitar N+1 (join/`in_`/`GROUP BY` fijos en `QueryPort`).

## Gotchas

- **SQLModel 0.0.39**: NO usar `from __future__ import annotations` en `models.py` — rompe forward-refs en `configure_mappers`/`selectinload`. Usar `Optional['X']`/`list['X']`.
- **testcontainers**: `PostgresContainer` de `testcontainers.community.postgres` con `get_connection_url(driver='psycopg')` (el driver psycopg2 default rompe con psycopg 3).
- `FakePagoRepository.save` y `SqlModelPagoRepository.save` hacen **upsert por id** (pagos no usan `update`).
- **Import legacy**: NO tocar las tablas `aux_*` de la DB vieja. El importer usa su tabla `import_ledger` en destino para idempotencia. Regla: `ngestion > 0` → SOS; `ngestion = 0` agrupado por `fecha` → TresArr (`grupo=fecha`); `ngestion = 0` solo en una fecha → OTROS. La columna `tipo` vieja se ignora.
- **NiceGUI 3.16**: `ui.dark(...)` se renombró a `ui.dark_mode` (`.set_value`); tablas usan slots (`add_slot('body-cell-X')` + `js_handler`) para botones por fila; `ui.run` debe quedar bajo `if __name__ == '__main__':`.
- UI: dark por defecto con toggle por usuario en `app.storage.user['theme']` (NO en DB).
- Duplicación pendiente: `src/adapters/logging/` vs `src/infrastructure/logging/` — elegir uno y borrar el otro.
- `pyproject.toml`: build-system hatchling con `packages = ["src"]`; dep psycopg es `psycopg[binary]` (requerido en Docker sin libpq del sistema).

## Ahorro de tokens (hábitos de sesión)

- Tests selectivos con `-q`: `uv run pytest -q tests/ui/` si tocás UI; no correr la suite completa en cada cambio.
- Pedir diffs acotados (`git diff <archivo>`) o `--stat`; evitar `git diff` completos cuando no hacen falta.
- Usar `mem_search`/`mem_get_observation` en Engram antes de re-explorar código ya trabajado.
- Cerrar sesión por feature con `mem_session_summary` (obligatorio antes de decir "done").
