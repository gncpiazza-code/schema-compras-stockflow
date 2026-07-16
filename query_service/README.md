# Query Service — StockFlow

Capa de datos entre la UI y PostgreSQL. **La UI no escribe SQL.**

## Uso

```python
from query_service.compras import solicitudes, proveedores, dashboard

print(dashboard.resumen())
print(solicitudes.siguiente_nro())
print(proveedores.listar(busqueda="acme"))
```

Configuración: variables del `.env` del instalador (`DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE` opcional).

También se puede apuntar el archivo con `STOCKFLOW_ENV=/ruta/.env`.

## Módulos `compras/`

| Módulo | Responsabilidad |
|--------|-----------------|
| `codificacion` | Catálogo oficial (código/nombre/descripcion) |
| `insumos` | Catálogo interno Compras (con o sin vínculo a codificación) |
| `proveedores` | ABM catálogo |
| `solicitudes` | SC + ítems, numeración, estados |
| `cotizaciones` | Cotización comparativa 3 proveedores |
| `ordenes` | OC + ítems |
| `recepciones` | Control pedida vs recibida |
| `panol` | `stock_maestro` + movimientos |
| `salidas` | Egresos de pañol (opcional descuento stock) |
| `dashboard` | Contadores y últimos documentos |

Dependencia: `psycopg` (misma que el instalador).
