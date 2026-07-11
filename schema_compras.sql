-- ============================================================
-- SCHEMA COMPRAS  (PostgreSQL)
-- Base: empresa  |  Schema: compras
-- Origen funcional: standrISO (SQLite) — portado a PG nativo
-- Flujo: SC → Cotización → OC → Recepción → Pañol → Salidas
-- ============================================================

CREATE SCHEMA IF NOT EXISTS compras;

-- ------------------------------------------------------------
-- 1. Proveedores (catálogo maestro)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.proveedores (
    id               SERIAL PRIMARY KEY,
    razon_social     VARCHAR(150) NOT NULL,
    nombre_fantasia  VARCHAR(150),
    ciudad           VARCHAR(100),
    cuit             VARCHAR(20),
    mail             VARCHAR(120),
    contacto         VARCHAR(120),
    telefono         VARCHAR(50),
    rubro            VARCHAR(80),
    observaciones    TEXT,
    punt_entrega     SMALLINT NOT NULL DEFAULT 0
        CHECK (punt_entrega BETWEEN 0 AND 10),
    punt_calidad     SMALLINT NOT NULL DEFAULT 0
        CHECK (punt_calidad BETWEEN 0 AND 10),
    punt_respuesta   SMALLINT NOT NULL DEFAULT 0
        CHECK (punt_respuesta BETWEEN 0 AND 10),
    punt_precio      SMALLINT NOT NULL DEFAULT 0
        CHECK (punt_precio BETWEEN 0 AND 10),
    activo           BOOLEAN NOT NULL DEFAULT TRUE,
    usuario_id       INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- 2. Solicitud de compra (SC) + ítems
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.solicitudes (
    id             SERIAL PRIMARY KEY,
    nro_solicitud  VARCHAR(30) NOT NULL UNIQUE,
    fecha          DATE NOT NULL,
    area           VARCHAR(80) NOT NULL,
    solicitante    VARCHAR(100) NOT NULL,
    rubro          VARCHAR(80),
    prioridad      VARCHAR(20) NOT NULL DEFAULT 'MEDIA'
        CHECK (prioridad IN ('BAJA', 'MEDIA', 'ALTA', 'URGENTE')),
    tipo_cambio    NUMERIC(14, 4) DEFAULT 1,
    estado         VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    creador        VARCHAR(100),
    check_pedido   VARCHAR(50) DEFAULT '',
    usuario_id     INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.solicitud_items (
    id                 SERIAL PRIMARY KEY,
    solicitud_id       INT NOT NULL
        REFERENCES compras.solicitudes(id) ON DELETE CASCADE,
    cantidad           NUMERIC(12, 2) NOT NULL CHECK (cantidad > 0),
    unidad             VARCHAR(30) NOT NULL,
    codigo_interno     VARCHAR(50),
    nro_plano          VARCHAR(50),
    descripcion        VARCHAR(255) NOT NULL,
    proveedor_sugerido VARCHAR(150),
    fecha_entrega      DATE,
    precio_unitario    NUMERIC(14, 4) DEFAULT 0,
    observaciones      TEXT,
    estado_cot         VARCHAR(40) DEFAULT ''
);

-- ------------------------------------------------------------
-- 3. Cotización comparativa (hasta 3 proveedores) + ítems
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.cotizaciones (
    id             SERIAL PRIMARY KEY,
    nro_cot        VARCHAR(30) NOT NULL UNIQUE,
    solicitud_id   INT REFERENCES compras.solicitudes(id) ON DELETE SET NULL,
    nro_solicitud  VARCHAR(30),
    fecha          DATE NOT NULL,
    moneda         VARCHAR(10) NOT NULL DEFAULT 'ARS',
    tc_usd         NUMERIC(14, 4) NOT NULL DEFAULT 1,
    tc_eur         NUMERIC(14, 4) NOT NULL DEFAULT 1,
    iva_pct        NUMERIC(5, 2) NOT NULL DEFAULT 21,
    estado         VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    -- Proveedor 1
    prov1_nombre   VARCHAR(150),
    prov1_entrega  VARCHAR(100),
    prov1_pago     VARCHAR(100),
    prov1_flete    VARCHAR(100),
    -- Proveedor 2
    prov2_nombre   VARCHAR(150),
    prov2_entrega  VARCHAR(100),
    prov2_pago     VARCHAR(100),
    prov2_flete    VARCHAR(100),
    -- Proveedor 3
    prov3_nombre   VARCHAR(150),
    prov3_entrega  VARCHAR(100),
    prov3_pago     VARCHAR(100),
    prov3_flete    VARCHAR(100),
    usuario_id     INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.cotizacion_items (
    id             SERIAL PRIMARY KEY,
    cotizacion_id  INT NOT NULL
        REFERENCES compras.cotizaciones(id) ON DELETE CASCADE,
    idx_sc         INT,
    descripcion    VARCHAR(255),
    unidad         VARCHAR(30),
    cantidad       NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    pu1            NUMERIC(14, 4) NOT NULL DEFAULT 0,
    pu2            NUMERIC(14, 4) NOT NULL DEFAULT 0,
    pu3            NUMERIC(14, 4) NOT NULL DEFAULT 0,
    desc1          NUMERIC(14, 4) NOT NULL DEFAULT 0,
    desc2          NUMERIC(14, 4) NOT NULL DEFAULT 0,
    desc3          NUMERIC(14, 4) NOT NULL DEFAULT 0,
    desctipo1      VARCHAR(10) NOT NULL DEFAULT 'pct',
    desctipo2      VARCHAR(10) NOT NULL DEFAULT 'pct',
    desctipo3      VARCHAR(10) NOT NULL DEFAULT 'pct'
);

-- ------------------------------------------------------------
-- 4. Orden de compra (OC) + ítems
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.ordenes (
    id                   SERIAL PRIMARY KEY,
    nro_oc               VARCHAR(30) NOT NULL UNIQUE,
    solicitud_id         INT REFERENCES compras.solicitudes(id) ON DELETE SET NULL,
    nro_solicitud        VARCHAR(30),
    fecha_oc             DATE NOT NULL,
    proveedor_id         INT REFERENCES compras.proveedores(id) ON DELETE SET NULL,
    proveedor_adjudicado VARCHAR(150),
    iva_pct              NUMERIC(5, 2) NOT NULL DEFAULT 21,
    tipo_cambio          NUMERIC(14, 4) NOT NULL DEFAULT 1,
    estado               VARCHAR(30) NOT NULL DEFAULT 'Emitida',
    usuario_id           INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.orden_items (
    id                 SERIAL PRIMARY KEY,
    orden_id           INT NOT NULL
        REFERENCES compras.ordenes(id) ON DELETE CASCADE,
    cantidad           NUMERIC(12, 2) NOT NULL CHECK (cantidad > 0),
    unidad             VARCHAR(30) NOT NULL,
    codigo_interno     VARCHAR(50),
    nro_plano          VARCHAR(50),
    descripcion        VARCHAR(255) NOT NULL,
    proveedor_sugerido VARCHAR(150),
    fecha_entrega      DATE,
    precio_unitario    NUMERIC(14, 4) NOT NULL DEFAULT 0,
    descuento          NUMERIC(14, 4) NOT NULL DEFAULT 0,
    desctipo           VARCHAR(10) NOT NULL DEFAULT 'pct',
    precio_neto        NUMERIC(14, 4) NOT NULL DEFAULT 0,
    precio_iva         NUMERIC(14, 4) NOT NULL DEFAULT 0,
    precio_final       NUMERIC(14, 4) NOT NULL DEFAULT 0,
    estado_oc          VARCHAR(30) NOT NULL DEFAULT 'Pendiente'
);

-- ------------------------------------------------------------
-- 5. Recepción / control de stock (ex standrISO: stock / stock_items)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.recepciones (
    id              SERIAL PRIMARY KEY,
    orden_id        INT REFERENCES compras.ordenes(id) ON DELETE SET NULL,
    solicitud_id    INT REFERENCES compras.solicitudes(id) ON DELETE SET NULL,
    nro_solicitud   VARCHAR(30),
    fecha_recepcion DATE NOT NULL,
    proveedor       VARCHAR(150),
    nro_remito      VARCHAR(50),
    usuario_id      INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.recepcion_items (
    id               SERIAL PRIMARY KEY,
    recepcion_id     INT NOT NULL
        REFERENCES compras.recepciones(id) ON DELETE CASCADE,
    descripcion      VARCHAR(255) NOT NULL,
    codigo_interno   VARCHAR(50),
    nro_plano        VARCHAR(50),
    cant_pedida      NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (cant_pedida >= 0),
    cant_recibida    NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (cant_recibida >= 0),
    precio_unitario  NUMERIC(14, 4) NOT NULL DEFAULT 0,
    estado           VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    observaciones    TEXT,
    estado_repuesto  VARCHAR(40) NOT NULL DEFAULT 'A confirmar'
);

-- ------------------------------------------------------------
-- 6. Pañol — stock maestro + movimientos
--     (dominio vecino a deposito.*; no duplicar productos de depósito)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.stock_maestro (
    id               SERIAL PRIMARY KEY,
    codigo           VARCHAR(50) NOT NULL UNIQUE,
    codigo_original  VARCHAR(50),
    descripcion      VARCHAR(255) NOT NULL,
    cantidad         NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    unidad           VARCHAR(30) NOT NULL DEFAULT 'UN',
    ubicacion        VARCHAR(100),
    observaciones    TEXT,
    usuario_id       INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    actualizado_en   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.stock_movimientos (
    id           SERIAL PRIMARY KEY,
    tipo         VARCHAR(40) NOT NULL,
    maestro_id   INT REFERENCES compras.stock_maestro(id) ON DELETE SET NULL,
    codigo       VARCHAR(50),
    descripcion  VARCHAR(255),
    cantidad     NUMERIC(12, 2) NOT NULL CHECK (cantidad <> 0),
    unidad       VARCHAR(30),
    referencia   VARCHAR(100),
    responsable  VARCHAR(100),
    usuario_id   INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- 7. Salidas de pañol (a área / máquina) + ítems
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compras.stock_salidas (
    id                 SERIAL PRIMARY KEY,
    nro_salida         VARCHAR(30) NOT NULL UNIQUE,
    fecha              DATE NOT NULL,
    responsable        VARCHAR(100) NOT NULL,
    area               VARCHAR(80) NOT NULL,
    motivo             TEXT,
    estado             VARCHAR(30) NOT NULL DEFAULT 'Emitida',
    firma_img          TEXT,
    maquina            VARCHAR(100),
    tipo_reparacion    VARCHAR(80),
    grupo              VARCHAR(80),
    horas              VARCHAR(40),
    motivo_reparacion  TEXT,
    usuario_id         INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.salida_items (
    id               SERIAL PRIMARY KEY,
    salida_id        INT NOT NULL
        REFERENCES compras.stock_salidas(id) ON DELETE CASCADE,
    maestro_id       INT REFERENCES compras.stock_maestro(id) ON DELETE SET NULL,
    codigo           VARCHAR(50),
    codigo_original  VARCHAR(50),
    descripcion      VARCHAR(255) NOT NULL,
    cantidad         NUMERIC(12, 2) NOT NULL CHECK (cantidad > 0),
    unidad           VARCHAR(30)
);

-- ------------------------------------------------------------
-- Índices
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado
    ON compras.solicitudes (estado);

CREATE INDEX IF NOT EXISTS idx_solicitudes_fecha
    ON compras.solicitudes (fecha);

CREATE INDEX IF NOT EXISTS idx_solicitud_items_sc
    ON compras.solicitud_items (solicitud_id);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_solicitud
    ON compras.cotizaciones (solicitud_id);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_estado
    ON compras.cotizaciones (estado);

CREATE INDEX IF NOT EXISTS idx_ordenes_solicitud
    ON compras.ordenes (solicitud_id);

CREATE INDEX IF NOT EXISTS idx_ordenes_proveedor
    ON compras.ordenes (proveedor_id);

CREATE INDEX IF NOT EXISTS idx_ordenes_estado
    ON compras.ordenes (estado);

CREATE INDEX IF NOT EXISTS idx_recepciones_orden
    ON compras.recepciones (orden_id);

CREATE INDEX IF NOT EXISTS idx_recepciones_solicitud
    ON compras.recepciones (solicitud_id);

CREATE INDEX IF NOT EXISTS idx_stock_maestro_codigo
    ON compras.stock_maestro (codigo);

CREATE INDEX IF NOT EXISTS idx_stock_movimientos_maestro
    ON compras.stock_movimientos (maestro_id);

CREATE INDEX IF NOT EXISTS idx_stock_salidas_fecha
    ON compras.stock_salidas (fecha);

CREATE INDEX IF NOT EXISTS idx_salida_items_salida
    ON compras.salida_items (salida_id);

CREATE INDEX IF NOT EXISTS idx_proveedores_razon
    ON compras.proveedores (razon_social);
