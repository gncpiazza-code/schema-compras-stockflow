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
└── compras
        ├── codificacion          ← catálogo oficial (código + nombre + descripción)
        ├── insumos               ← catálogo interno de Compras (puede o no cruzar con codificación)
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

### Relación codificación ↔ insumos ↔ pedidos

```
codificacion (maestro oficial del sistema)
      │
      │  opcional: Compras “toma” un artículo oficial
      ▼
insumos (catálogo interno de Compras)
      │  • con codificacion_id  → usa nombre oficial
      │  • sin codificacion_id  → producto solo de Compras
      ▼
solicitud_items / OC / recepción  (documentos de compra)
```

---

## Explicación de cada tabla

### `codificacion` — catálogo oficial

Maestro de artículos del sistema. Lo que figura acá se nombra **siempre** igual en toda la app: no se inventan alias ni se reescriben descripciones en pantallas.

| Campo | Uso |
|-------|-----|
| `codigo` | Código genérico único (ej. `40000001`) |
| `nombre` | Nombre oficial del artículo |
| `descripcion` | Descripción oficial (misma forma canónica que el nombre en el seed actual) |
| `unidad` | Unidad de medida (`UN`, `KG`, `BO`, `MI`, `RO`, …) |
| `categoria` | Agrupación de negocio |
| `activo` | Baja lógica sin borrar el código |

**Categorías cargadas en el seed:**

| Categoría | Ejemplos de códigos |
|-----------|---------------------|
| PRODUCTO TERMINADO | `00000001` … |
| INSUMOS | `40000000` … |
| VARIOS | `10000001` … |
| PRODUCTOS REVENTA | `20000001`, `30000001` … |

**Seed:** [`datos_codificacion.sql`](datos_codificacion.sql) — 84 artículos desde el Excel de codificación del sistema.  
**Migración** (bases ya instaladas): [`migration_codificacion.sql`](migration_codificacion.sql) + volver a correr el seed.

**Regla de UI:** al mostrar o elegir un artículo codificado, usar exactamente `codigo` + `nombre` + `descripcion` (+ `unidad`).

### `insumos` — catálogo interno de Compras

Tabla propia del sector Compras. Se **alimenta** de `codificacion` cuando corresponde, pero también permite cargar productos que **no existen** en la codificación oficial.

| Campo | Uso |
|-------|-----|
| `codigo` | Código interno de Compras (opcional; único si se informa) |
| `nombre` | Nombre del insumo en Compras |
| `descripcion` | Descripción (en vinculados, copia del oficial) |
| `unidad` | Unidad de medida |
| `codificacion_id` | FK a `codificacion`. `NULL` = insumo 100% interno |
| `activo` | Baja lógica |

**Dos modos:**

| Modo | `codificacion_id` | Significado |
|------|-------------------|-------------|
| Vinculado al oficial | seteado | Compras compra un artículo de la codificación. Nombre/descripcion/unidad deben respetar el maestro. |
| Interno puro | `NULL` | Producto a comprar que **no cruza** con la codificación original (repuestos sueltos, servicios, ítems nuevos, etc.). Compras lo alta y gestiona libremente. |

Los ítems de solicitud (`solicitud_items`) pueden apuntar a `codificacion_id` y/o `insumo_id` para dejar trazabilidad del origen del artículo.

### Proveedores

| Tabla | Descripción |
|-------|-------------|
| **`proveedores`** | Maestro de proveedores. Guarda razón social, nombre de fantasía, CUIT, ciudad, mail, contacto, teléfono, rubro, observaciones y puntajes (entrega, calidad, respuesta, precio, escala 0–10). Campo `activo` para baja lógica. Opcionalmente vincula al usuario que lo cargó (`usuario_id` → `public.usuarios`). |

### Solicitud de compra (SC)

| Tabla | Descripción |
|-------|-------------|
| **`solicitudes`** | Cabecera de la solicitud. Identificador de negocio: `nro_solicitud` (único). Incluye fecha, área pedidora, solicitante, rubro, prioridad (`BAJA` / `MEDIA` / `ALTA` / `URGENTE`), tipo de cambio, estado (por defecto `Pendiente`), creador y `check_pedido` (marca de control interno). |
| **`solicitud_items`** | Líneas de la SC. Cada fila: cantidad, unidad, código interno, nro. de plano, descripción, proveedor sugerido, fecha de entrega deseada, precio unitario de referencia, observaciones y `estado_cot`. Opcionalmente referencia `codificacion_id` y/o `insumo_id` (origen del artículo). FK `solicitud_id` con borrado en cascada. |

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

### 2. Codificación oficial

- Consultar / buscar por código, nombre o categoría.
- Al elegir un artículo codificado, la UI debe mostrar **exactamente** `codigo` + `nombre` + `descripcion` (+ unidad).
- No editar a mano la denominación oficial desde Compras (el maestro se mantiene vía seed/migración).

### 3. Insumos internos de Compras

- Listar insumos (todos / solo internos / solo vinculados a codificación).
- Alta de insumo **interno** (sin `codificacion_id`): productos a comprar fuera del maestro oficial.
- Alta de insumo **desde codificación**: copia nombre/descripcion/unidad oficiales.
- Editar insumos internos; en vinculados, no alterar nombre/descripcion/unidad.
- Baja lógica / eliminación controlada.

### 4. Proveedores

- Listar y buscar proveedores.
- Alta y edición de datos fiscales y de contacto (razón social, CUIT, rubro, observaciones, etc.).
- Carga y edición de puntajes (entrega, calidad, respuesta, precio).
- Baja lógica (`activo = false`) o eliminación controlada.

### 5. Solicitud de compra (SC)

- Crear SC con cabecera (área, solicitante, rubro, prioridad).
- Agregar, editar y quitar ítems (eligiendo desde codificación, desde insumos, o libre).
- Generar o sugerir el próximo `nro_solicitud`.
- Cambiar estado (Pendiente → en proceso / cerrada / anulada).
- Registrar check de pedido (`check_pedido`).
- Listar historial y abrir detalle completo.
- Editar SC existente según reglas de estado.
- Eliminar SC (cascada de ítems; validar que no existan OC o cotización vinculadas).

### 6. Cotización

- Crear cotización a partir de una SC.
- Cargar hasta 3 proveedores con condiciones (entrega, pago, flete).
- Cargar precios y descuentos por ítem y por proveedor.
- Configurar moneda, tipo de cambio USD/EUR e IVA.
- Comparar ofertas y conservar trazabilidad para la adjudicación.
- Listar, editar y eliminar cotizaciones.
- Exportar PDF de cotización.

### 7. Orden de compra (OC)

- Generar OC desde una SC (típicamente tras cotizar).
- Asignar proveedor adjudicado.
- Editar ítems, precios, descuentos, IVA y tipo de cambio.
- Administrar estado de cabecera y de cada ítem.
- Listar, editar y eliminar OC.
- Exportar PDF de OC.

### 8. Recepción / control de stock

- Registrar recepción contra SC u OC (fecha, remito, proveedor).
- Cargar cantidad pedida vs recibida por ítem.
- Marcar estado del ítem y del repuesto.
- Listar, corregir y eliminar recepciones.
- Opcional: al confirmar recepción, impactar `stock_maestro` mediante un movimiento de ingreso.

### 9. Pañol (inventario)

- ABM de ítems en `stock_maestro` (código, descripción, cantidad, ubicación).
- Consultar movimientos del pañol.
- Resumen de existencias y, si se define regla de negocio, alertas de stock bajo.
- Exportar inventario a Excel.

### 10. Salidas de pañol

- Crear salida (área, responsable, máquina, motivo / reparación).
- Descontar ítems de `stock_maestro` y registrar el movimiento correspondiente.
- Generar el próximo `nro_salida`.
- Adjuntar firma o evidencia (`firma_img`) cuando aplique.
- Listar y eliminar salidas.
- Exportar PDF de salida y/o Excel.

### 11. Registros e historial

- Vista acumulativa de SC, OC, cotizaciones, recepciones y salidas.
- Filtros por fecha, estado, área y proveedor.
- Apertura de documento completo (cabecera + ítems).

### 12. Exportaciones

- Exportar solicitudes, órdenes, recepciones, inventario y salidas.
- Exportación completa (todos los módulos).

### 13. Autenticación y usuarios

- Login contra `public.usuarios` (no existe tabla de usuarios dentro de `compras`).
- Respetar roles definidos en `public.roles` (`admin`, `operador`, `auditor`).

---

## Cómo instalar el schema

### Con el instalador StockFlow

El instalador crea el schema `compras`, ejecuta `schema_compras.sql`, carga `datos_iniciales.sql` + `datos_codificacion.sql`, y asigna permisos al usuario de aplicación (`public`, `deposito`, `compras`).

### Manual (psql)

```bash
psql -U postgres -d empresa -f schema_compras.sql
psql -U postgres -d empresa -f datos_codificacion.sql
```

Bases ya existentes (solo parche de catálogos):

```bash
psql -U postgres -d empresa -f migration_codificacion.sql
psql -U postgres -d empresa -f datos_codificacion.sql
```

Permisos tipicos para el usuario de aplicación (`stockflow`):

```sql
GRANT USAGE ON SCHEMA compras TO stockflow;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA compras TO stockflow;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA compras TO stockflow;
```

**Precondición:** deben existir `public.usuarios` (varias FKs apuntan ahí).

---

## Query Service

Capa Python entre la UI y PostgreSQL. La interfaz **no escribe SQL**: llama funciones de este paquete.

```
query_service/
├── db.py                 # conexión (.env) y helpers
└── compras/
    ├── codificacion.py   # catálogo oficial (solo lectura / consulta)
    ├── insumos.py        # catálogo interno de Compras
    ├── proveedores.py
    ├── solicitudes.py
    ├── cotizaciones.py
    ├── ordenes.py
    ├── recepciones.py
    ├── panol.py          # stock_maestro + movimientos
    ├── salidas.py
    └── dashboard.py
```

Ejemplo de uso desde la UI:

```python
from query_service.compras import solicitudes, proveedores, codificacion, insumos

lista = solicitudes.listar(estado="Pendiente")
oficiales = codificacion.listar(categoria="INSUMOS", busqueda="papel")
insumos.crear_interno({"nombre": "Guantes nitrilo M", "unidad": "UN"})
insumos.crear_desde_codificacion(oficiales[0]["id"])
proveedores.crear({"razon_social": "Acme SA", "cuit": "30-12345678-9"})
```

Ver docstrings en cada módulo para la firma completa de operaciones.
