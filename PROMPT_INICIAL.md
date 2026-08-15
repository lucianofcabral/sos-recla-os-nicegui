# Prompt inicial — Sistema de Reclamos de SOS

Necesito una aplicación web para administrar Reclamos relacionadas a un servicio
terciarizado llamado "SOS". Hoy existe una app muy desordenada.

La app la va a usar gente de la oficina desde el navegador, así que tiene que ser
simple de usar y segura: **nada de registros abiertos**; cada usuario entra con
usuario y contraseña.

## Contexto del negocio

Recibimos reclamos de servisio mal hechos, defectuosos o no prestados, que
reclaman reintegro de gastos.

Hay 3 tipos de reclamos:

- Reclamos que se deben reclamar a SOS.
- Reclamos que entran en lotes "3 Arroyos".
- Otros.

En un momento se debe decidir si se reintegra algo de lo gastado por
nuestros clientes y registrar solicitar pagos con su importe, pagador  
y pagado.

Hay un tipo mde pago especial "NOTA DE CRÉDITO" que es un pag que hace SOS a SM,
y se materializan una vez al mes y que van asociados a un periodo de facturación.

La app debe ser capaz de registrar la data necesaria para consultar y auditar lo
necesario.

## Lo que tiene que hacer la app

**Login:**

- Pantalla de inicio de sesión; sin sesión, cualquier ruta redirige al login.
- Primer usuario creado por script (bootstrap), contraseñas hasheadas con bcrypt.
- Botón para cerrar sesión.

**Pantalla de inicio (home):**

- Mostrar los **reclamos**, con datos importantes de la misma:
  - Dominio
  - Fecha Ingresado
  - Póliza
  - Cliente
  - Nro. Gestión SOS
  - Tipo de Reclamo
  - Importe Reclamado
  - Con Pagos
  - Con Nota de Crédito
  - Activar/Inactivar
- Botón para **importar Excel SOS**, **nueva 3 Arroyos** y **nueva Gestión** .
- Los reclamos **SOS se importan** (upsert) desde el Excel "Gestión Reclamos Y Reintegros.xlsx" por **N° Gestión**: si el número ya existe se actualizan sus datos, si no, se crea. Columnas usadas: Fecha (fecha de ingreso), Cliente, Dominio, Póliza, Motivo, Usuario Carga, Usuario Respuesta, Estado e ITR. El **Estado se guarda como texto** y no inactiva el reclamo; **Tipo y N° Caso se ignoran**; el importe no se modifica al actualizar (0 al crear).
- Todo texto de un reclamo se guarda en **MAYÚSCULAS**; **Dominio y Póliza** además **sin espacios internos** (MTB 828 → MTB828), y el resto del texto (cliente, comentarios, estado, etc.) en mayúsculas pero conservando los espacios entre palabras (juan perez → JUAN PEREZ) y sin espacios al inicio/fin ni dobles.
- Botón **nueva Gestión**: abre un diálogo que además de los campos del reclamo tiene una sección **Pagos del reclamo** — permite cargar pagos (fecha, forma, pagador, destinatario e importe) que se van viendo en una tabla dentro del mismo diálogo y se pueden quitar antes de guardar. Al confirmar se crea la gestión y sus pagos en **un solo commit**; si algún pago es inválido (importe ≤ 0, o pagador == destinatario salvo nota de crédito) no se guarda nada. Un pago **NOTA DE CRÉDITO** fuerza pagador SOS → destinatario SM y crea la nota de crédito automáticamente.

**Página de pagos:**

- Mostrar los **pagos**, con datos importantes:
  - Fecha Ingresado
  - Pagdaor
  - Destinatario
  - Forma de Pago
  - Dominio
  - Póliza
  - Cliente
  - Nro. Gestión SOS
  - Importe
  - Eliminar

**Página de Ciclos:**

- Mostrar los **ciclos** como cards, con datos importantes:
  - Nombre Corto
  - Cant. Documentos
  - Suma Importe Facturas
  - Cant. Notas de Crédito
  - Suma Importe Notas de Crédito
- Botón **Nuevo Ciclo**.

**Formato de montos:** estilo argentino — miles con `.`, decimales con `,`, dos decimales.

## Requisitos técnicos

- **Python 3.13**, interfaz con **NiceGUI** (sin framework JS separado), **Postgres y/o Sqlite** con **SQLModel 2**, dependencias manejadas con **uv**.
- **Arquitectura hexagonal**: dominio (entidades, ports, excepciones), aplicación (use cases), infraestructura (UoW), adapters (SQLModel) y UI (páginas NiceGUI). Los use cases reciben un `UnitOfWorkPort`, nunca modelos ORM.
- El commit de la base es **explícito en cada use case**; al salir del contexto solo se hace rollback.
- Las queries que retornan listas deben evitar el problema N+1.
- **Tests**: suite de aplicación con fakes + tests de integración contra PostgreSQL8Sqlite real efímero (testcontainers). Lint con ruff.
- Tema oscuro por defecto, con toggle para claro/oscuro que recuerde la preferencia por usuario.
- Estética profesional.

## Entregables

1. Código completo, funcionando, con tests verdes.
2. Script de bootstrap para crear el primer usuario.
3. Scripts de importación/migración para la carga inicial desde fuentes históricas.
4. Documentación: README con setup y despliegue (Docker), y un manual de usuario con el paso a paso.

---
