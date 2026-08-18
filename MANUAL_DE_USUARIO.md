# Manual de usuario — SOS Reclamos

Aplicación web para administrar reclamos, pagos, notas de crédito y periodos del servicio terciarizado "SOS". La usa gente de la oficina desde el navegador; cada usuario ingresa con usuario y contraseña.

## 1. Ingreso y salida

- Abrí la aplicación en el navegador. Si no hay una sesión iniciada, la app redirige a la pantalla de **Login**.
- Ingresá tu **Usuario** y **Contraseña** y tocá **Ingresar**.
- Si los datos son incorrectos, aparece "usuario o contraseña inválidos".
- Para salir, tocá el botón de **cerrar sesión** en la barra superior.
- En el encabezado podés alternar el tema **claro/oscuro**; la preferencia se recuerda por usuario.

La barra superior tiene las secciones:

| Sección | Descripción | Acceso |
| --- | --- | --- |
| Inicio | Reclamos y su gestión | Todos |
| Pagos | Pagos de todos los reclamos | Todos |
| Periodos | Ciclos de facturación y notas de crédito | Todos |
| Migración | Importar base legada | Solo administradores |

## 2. Inicio: lista de reclamos

La página **Inicio** muestra todos los reclamos en una tabla con paginación (20 por página) y estas columnas:

- **Dominio**
- **Fecha Ingresado**
- **Póliza**
- **Cliente**
- **Nro. Gestión SOS**
- **Tipo de Reclamo** (SOS, 3 Arroyos o Gestión)
- **Importe Reclamado**
- **Con Pagos** (Sí/No)
- **Con Nota de Crédito** (Sí/No)
- **Editar** (botón por fila)
- **Activar/Inactivar** (botón por fila)

### 2.1 Filtrar reclamos

Arriba de la tabla hay controles de filtro:

- Casillas **Con Pagos / Sin Pagos**, **Con Nota de Crédito / Sin Nota de Crédito** y **Activos / Inactivos**.
- Rango de fechas **Desde / Hasta** (fecha de ingreso).
- **Importe min / Importe max**.
- **Tipo de Reclamo** (Todos, SOS, 3 Arroyos, Gestión).
- **Grupo** (filtra por grupo de 3 Arroyos).
- **Buscar** por dominio, póliza o nº de gestión (escribe y espera, filtra solo).

Tocá **Filtrar** para aplicar o **Limpiar** para volver a la lista completa.

### 2.2 Activar / Inactivar un reclamo

Tocá el botón de la fila:

- **Inactivar** (naranja): el reclamo queda inactivo; deja de usarse para cargar pagos nuevos.
- **Activar** (verde): lo vuelve activo.

### 2.3 Editar un reclamo

Tocá el ícono de lápiz en la fila. Se abre el diálogo **Editar reclamo** con los datos del reclamo y, en el mismo diálogo:

- **Pagos del reclamo**: tabla con los pagos registrados y botón **Nuevo pago**.
- **Documentos**: sección para adjuntar, descargar y eliminar archivos (ver sección 6).

Editá lo que necesites y guardá. En reclamos **SOS** el **Nro. de Gestión** no se puede editar; en **3 Arroyos** tampoco el **Grupo**.

## 3. Alta de reclamos

El botón **Nueva Gestión** abre el diálogo **Nuevo reclamo Gestión** con dos partes:

1. Datos del reclamo: Cliente, Póliza, Dominio, Importe Reclamado y Comentario.
2. **Pagos del reclamo**: cargás pagos y se van viendo en una tabla; podés quitar cualquiera tocando su botón.

Al guardar se crea la gestión y sus pagos **en un solo paso**: si algún pago es inválido no se guarda nada.

Cada pago pide: **Fecha de Pago** (por defecto hoy), **Forma de Pago**, **Importe**, **Pagador** y **Destinatario**. Reglas:

- El importe debe ser mayor a cero.
- El pagador no puede ser igual al destinatario.
- Si la forma es **Nota de Crédito**, SOS paga a SM automáticamente: se ocultan Pagador/Destinatario y la nota de crédito se crea sola.

> Los reclamos **SOS se importan** desde Excel (sección 5) y los **3 Arroyos** entran por lote (sección 4); "Nueva Gestión" crea reclamos tipo Gestión.

## 4. Nuevo lote 3 Arroyos

El botón **Nueva 3 Arroyos** abre el diálogo de **lote**: cargás varias gestiones de una sola vez (cliente, dominio, póliza, importe y documentos asociados), se van listando las pendientes y podés quitar alguna antes de confirmar. Opcionalmente se pueden generar pagos para el lote. Al confirmar se guarda todo el lote.

## 5. Importar Excel SOS

El botón **Importar Excel SOS** abre el diálogo para seleccionar el archivo **Gestión Reclamos Y Reintegros.xlsx**:

- Primero hace una **previsualización** ("X para crear, Y para actualizar") y muestra errores si los hay; no graba nada todavía.
- El **Importar** final aplica la carga. Los reclamos SOS se **actualizan por N° de Gestión**: si el número ya existe se actualizan sus datos y si no, se crea.
- El **estado** se guarda como texto y no inactiva el reclamo; el **importe** no se modifica al actualizar.
- Todo el texto se guarda en **mayúsculas**; dominio y póliza sin espacios internos.

## 6. Documentos (reclamos y periodos)

En el diálogo de **editar reclamo** y en el de **periodo** hay una sección para documentos:

- **Adjuntar documentos**: elegí uno o varios archivos (**PDF, PNG, JPG, JPEG, DOC, DOCX, XLSX**); se suben automáticamente.
- Cada documento listado tiene botones de **descargar** y **eliminar** (eliminar pide confirmación).

## 7. Pagos

La página **Pagos** muestra todos los pagos con: Fecha, Pagador, Destinatario, Forma de Pago, Dominio, Póliza, Grupo, Cliente, Nro. Gestión SOS e Importe.

### 7.1 Nuevo pago

Tocá **Nuevo Pago** y completá:

- **Reclamo**: seleccioná el reclamo (Dominio · Póliza · Cliente · Tipo). Si entrás desde un reclamo, ya viene fijado.
- **Fecha de Pago**, **Forma de Pago**, **Importe**, **Pagador**, **Destinatario**.

Las mismas reglas que en el alta de gestión: importe > 0, pagador ≠ destinatario, y **Nota de Crédito** fuerza SOS → SM y crea la nota sola. Solo se listan reclamos activos; si no hay ninguno, se avisa.

### 7.2 Editar un pago

Usá el ícono de lápiz en la fila. Solo se pueden editar los campos válidos según el tipo de pago; en una **nota de crédito** los actores quedan fijos.

### 7.3 Eliminar un pago

Botón rojo de eliminar en la fila. Los pagos tipo **Nota de Crédito** se eliminan junto con su nota de crédito. Una **nota de crédito asignada a un periodo cerrado** no se puede borrar (el periodo la protege mientras esté cerrado).

### 7.4 Filtrar pagos

Arriba de la tabla: filtros por **Pagador**, **Destinatario** y **Forma de Pago** (múltiples valores) y **Buscar** por dominio, cliente, grupo o póliza. Botones **Filtrar** y **Limpiar**.

## 8. Periodos (ciclos) y notas de crédito

La página **Periodos** tiene dos zonas:

### 8.1 Notas de crédito sin asignar

- Tabla con las notas de crédito pendientes de asignar a un periodo (fecha, dominio, cliente, póliza, nº gestión e importe).
- Seleccioná una o varias y usá **Asignar a Periodo** para elegir un **periodo abierto** y asignarlas.
- **Descargar Excel** exporta las notas seleccionadas.
- Si no hay periodos abiertos, el botón Asignar está deshabilitado.

### 8.2 Cards de periodos

Cada **ciclo** se muestra como una card con:

- **Nombre Corto** y estado (**Cerrado** si corresponde)
- **Cant. Documentos**
- **Suma Importe Facturas**
- **Cant. Notas de Crédito**
- **Suma Importe Notas de Crédito**

Tocá una card para **abrir el periodo**. Dentro del periodo podés:

- Editar **Fecha Inicio / Fecha Fin** y guardarlas.
- Ver sus **Notas de Crédito**, seleccionarlas y:
  - **Descargar Excel** con el detalle.
  - **Desasignar seleccionadas** (solo si el periodo está abierto).
- **Cerrar periodo** (queda en estado Cerrado; sus notas de crédito ya no se pueden borrar ni editar).
- **Reabrir periodo** (las notas vuelven a ser editables y desasignables).
- Ver y adjuntar **documentos** del periodo (sección 6).

### 8.3 Nuevo periodo

Tocá **Nuevo Periodo** y cargá **Año**, **Mes** y un **Nombre Corto** opcional. Se crea abierto para poder asignarle notas de crédito.

## 9. Migración (solo administradores)

La página **Migración** importa una base legada hacia la base actual. Para migrar
también los documentos adjuntos, prepará un ZIP con esta estructura:

```text
migracion.zip
├── gestiones.db
└── files/
    └── docs/
        └── ...archivos referenciados por la base...
```

La carpeta `files/docs` debe quedar al mismo nivel que `gestiones.db` dentro del
ZIP. También se puede subir sólo `gestiones.db`, pero en ese caso los documentos
que dependan de archivos externos no se podrán importar.

Desde la página:

1. Seleccioná el ZIP de migración (o el archivo `.db` si no hay adjuntos).
2. Sin marcar **Aplicar (escribir en la base)**, la importación es un **dry run**: solo cuenta y no escribe nada.
3. Con **Aplicar** marcado, pide confirmación y escribe los cambios.
4. Al final muestra el **reporte por tipo** (reclamos SOS, 3 Arroyos, Gestión, pagos, notas de crédito, facturas, periodos, documentos) y los errores si los hubo.

> Es una operación delicada: usala solo para la carga inicial o bajo indicación del administrador.

## 10. Formato de montos

Todos los importes se muestran con formato argentino: miles con `.` y decimales con `,` (por ejemplo `1.250,50`).
