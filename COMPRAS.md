# Schema Compras — StockFlow

Documentación del sector **Compras**: estructura PostgreSQL, significado de cada tabla y funciones que debe cubrir la aplicación de escritorio (CustomTkinter).

| Recurso | Valor |
|---------|--------|
| Archivo SQL | [`schema_compras.sql`](schema_compras.sql) |
| Schema PostgreSQL | `compras` |
| Schemas relacionados | `public` (auth), `deposito` (almacén) |

---

## Mapa de la base de datos

```
empresa
├── public      → roles, usuarios, modulos
├── deposito    → áreas, sectores, productos, lotes, stock, movimientos
└── compras     → proveedores, SC, cotizaciones, OC, recepciones, pañol, salidas
        ├── proveedores
        ├── solicitudes + solicitud_items
        ├── cotizaciones + cotizacion_items
        ├── ordenes + orden_items
        ├── recepciones + recepcion_items
        ├── stock_maestro + stock_movimientos
        └── stock_salidas + salida_items
```

### Flujo de negocio

```
Solicitud (SC) → Cotización → Orden (OC) → Recepción → Pañol → Salida a área/máquina
```

1. Un área genera una **solicitud de compra** con ítems.
2. Compras arma una **cotización comparativa** (hasta 3 proveedores).
3. Se adjudica y emite una **orden de compra**.
4. Al llegar la mercadería se registra la **recepción** (pedida vs recibida).
5. El material ingresa al **pañol** (`stock_maestro`).
6. Las **salidas** descuentan stock hacia un área o máquina.

---

## Explicación de cada tabla

### Catálogo

| Tabla | Descripción |
|-------|-------------|
| **`proveedores`** | Maestro de proveedores. Guarda razón social, nombre de fantasía, CUIT, ciudad, mail, contacto, teléfono, rubro, observaciones y puntajes (entrega, calidad, respuesta, precio, escala 0–10). Campo `activo` para baja lógica. Opcionalmente vincula al usuario que lo cargó (`usuario_id` → `public.usuarios`). |

### Solicitud de compra (SC)

| Tabla | Descripción |
|-------|-------------|
| **`solicitudes`** | Cabecera de la solicitud. Identificador de negocio: `nro_solicitud` (único). Incluye fecha, área pedidora, solicitante, rubro, prioridad (`BAJA` / `MEDIA` / `ALTA` / `URGENTE`), tipo de cambio, estado (por defecto `Pendiente`), creador y `check_pedido` (marca de control interno). |
| **`solicitud_items`** | Líneas de la SC. Cada fila: cantidad, unidad, código interno, nro. de plano, descripción, proveedor sugerido, fecha de entrega deseada, precio unitario de referencia, observaciones y `estado_cot` (seguimiento respecto de la cotización). FK `solicitud_id` con borrado en cascada. |

### Cotización comparativa

| Tabla | Descripción |
|-------|-------------|
| **`cotizaciones`** | Cabecera de cotización, normalmente ligada a una SC (`solicitud_id` / `nro_solicitud`). Define moneda, tipo de cambio USD/EUR, IVA y estado. Soporta **hasta tres proveedores** en columnas denormalizadas: `prov1_*`, `prov2_*`, `prov3_*` (nombre, condición de entrega, forma de pago, flete). |
| **`cotizacion_items`** | Ítems cotizados. Por cada línea: descripción, unidad, cantidad e índice opcional hacia el ítem de la SC (`idx_sc`). Precios unitarios y descuentos por proveedor: `pu1/2/3`, `desc1/2/3`, `desctipo1/2/3` (`pct` u otro criterio). |

> El modelo de tres proveedores en columnas permite comparar ofertas lado a lado en una sola cotización.

### Orden de compra (OC)

| Tabla | Descripción |
|-------|-------------|
| **`ordenes`** | Cabecera de la orden. `nro_oc` único. Vincula a la SC (`solicitud_id` / `nro_solicitud`) y al proveedor adjudicado (`proveedor_id` y/o texto `proveedor_adjudicado`). Incluye IVA %, tipo de cambio y estado (por defecto `Emitida`). |
| **`orden_items`** | Líneas de la OC: cantidad, unidad, códigos, descripción, fecha de entrega, precio unitario, descuento (`descuento` + `desctipo`), importes calculados (`precio_neto`, `precio_iva`, `precio_final`) y estado por ítem (`estado_oc`). |

### Recepción / control de ingreso

| Tabla | Descripción |
|-------|-------------|
| **`recepciones`** | Cabecera del control de ingreso de mercadería. Relaciona OC y/o SC, fecha de recepción, nombre de proveedor, número de remito y usuario. |
| **`recepcion_items`** | Detalle de la recepción. Compara `cant_pedida` vs `cant_recibida`, guarda precio unitario, estado del ítem, observaciones y `estado_repuesto` (por defecto `A confirmar`). |

### Pañol (inventario de compras / insumos)

| Tabla | Descripción |
|-------|-------------|
| **`stock_maestro`** | Catálogo e inventario actual del pañol. Código único, código original (opcional), descripción, cantidad disponible, unidad, ubicación y observaciones. |
| **`stock_movimientos`** | Historial de movimientos del pañol (ingresos, egresos, ajustes). Registra tipo, vínculo opcional a `stock_maestro`, código, descripción, cantidad, unidad, referencia documental, responsable y usuario. |

> **Límite de dominio:** `compras.stock_maestro` (pañol / insumos de compras) y `deposito.productos` / `deposito.stock` (almacén) son schemas distintos. No deben mezclarse en la misma pantalla ni duplicarse sin un criterio de frontera acordado.

### Salidas de pañol

| Tabla | Descripción |
|-------|-------------|
| **`stock_salidas`** | Cabecera de egreso del pañol. `nro_salida` único. Incluye fecha, responsable, área destino, motivo, estado, firma (`firma_img`), máquina, tipo de reparación, grupo, horas y motivo de reparación. |
| **`salida_items`** | Ítems egresados: vínculo a `stock_maestro`, códigos, descripción, cantidad y unidad. Cascada al borrar la salida. |

---

## Funciones que debe cubrir el programa

Capacidades funcionales esperadas en la aplicación de escritorio.  
**Regla de arquitectura:** la UI no escribe SQL directamente; consume un Query Service o capa de datos equivalente.

### 1. Dashboard / inicio Compras

- Mostrar resumen de SC pendientes, OC emitidas y recepciones abiertas.
- Listar los últimos documentos creados.
- Exponer indicadores básicos (por ejemplo OTIF, si se implementa).

### 2. Proveedores

- Listar y buscar proveedores.
- Alta y edición de datos fiscales y de contacto (razón social, CUIT, rubro, observaciones, etc.).
- Carga y edición de puntajes (entrega, calidad, respuesta, precio).
- Baja lógica (`activo = false`) o eliminación controlada.

### 3. Solicitud de compra (SC)

- Crear SC con cabecera (área, solicitante, rubro, prioridad).
- Agregar, editar y quitar ítems.
- Generar o sugerir el próximo `nro_solicitud`.
- Cambiar estado (Pendiente → en proceso / cerrada / anulada).
- Registrar check de pedido (`check_pedido`).
- Listar historial y abrir detalle completo.
- Editar SC existente según reglas de estado.
- Eliminar SC (cascada de ítems; validar que no existan OC o cotización vinculadas).

### 4. Cotización

- Crear cotización a partir de una SC.
- Cargar hasta 3 proveedores con condiciones (entrega, pago, flete).
- Cargar precios y descuentos por ítem y por proveedor.
- Configurar moneda, tipo de cambio USD/EUR e IVA.
- Comparar ofertas y conservar trazabilidad para la adjudicación.
- Listar, editar y eliminar cotizaciones.
- Exportar PDF de cotización.

### 5. Orden de compra (OC)

- Generar OC desde una SC (típicamente tras cotizar).
- Asignar proveedor adjudicado.
- Editar ítems, precios, descuentos, IVA y tipo de cambio.
- Administrar estado de cabecera y de cada ítem.
- Listar, editar y eliminar OC.
- Exportar PDF de OC.

### 6. Recepción / control de stock

- Registrar recepción contra SC u OC (fecha, remito, proveedor).
- Cargar cantidad pedida vs recibida por ítem.
- Marcar estado del ítem y del repuesto.
- Listar, corregir y eliminar recepciones.
- Opcional: al confirmar recepción, impactar `stock_maestro` mediante un movimiento de ingreso.

### 7. Pañol (inventario)

- ABM de ítems en `stock_maestro` (código, descripción, cantidad, ubicación).
- Consultar movimientos del pañol.
- Resumen de existencias y, si se define regla de negocio, alertas de stock bajo.
- Exportar inventario a Excel.

### 8. Salidas de pañol

- Crear salida (área, responsable, máquina, motivo / reparación).
- Descontar ítems de `stock_maestro` y registrar el movimiento correspondiente.
- Generar el próximo `nro_salida`.
- Adjuntar firma o evidencia (`firma_img`) cuando aplique.
- Listar y eliminar salidas.
- Exportar PDF de salida y/o Excel.

### 9. Registros e historial

- Vista acumulativa de SC, OC, cotizaciones, recepciones y salidas.
- Filtros por fecha, estado, área y proveedor.
- Apertura de documento completo (cabecera + ítems).

### 10. Exportaciones

- Exportar solicitudes, órdenes, recepciones, inventario y salidas.
- Exportación completa (todos los módulos).

### 11. Autenticación y usuarios

- Login contra `public.usuarios` (no existe tabla de usuarios dentro de `compras`).
- Respetar roles definidos en `public.roles` (`admin`, `operador`, `auditor`).

---

## Cómo instalar el schema

### Con el instalador StockFlow

El instalador crea el schema `compras`, ejecuta `schema_compras.sql` y asigna permisos al usuario de aplicación, junto con `public` y `deposito`.

### Manual (psql)

```bash
psql -U postgres -d empresa -f schema_compras.sql
```

Permisos tipicos para el usuario de aplicación (`stockflow`):

```sql
GRANT USAGE ON SCHEMA compras TO stockflow;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA compras TO stockflow;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA compras TO stockflow;
```

**Precondición:** deben existir `public.usuarios` (varias FKs apuntan ahí).

---

## Trabajo pendiente (capa de datos)

1. **Query Service** (`compras/*.py`): operaciones SQL encapsuladas para que la UI no acceda a la base directamente.
2. Definir frontera formal entre pañol (`compras.stock_maestro`) y depósito (`deposito.*`).
3. Seed opcional (rubros / áreas de pedido) si el negocio lo requiere.
