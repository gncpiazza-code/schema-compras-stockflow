-- Migración: codificación oficial + insumos internos de Compras
-- Aplicar sobre bases ya instaladas (schema compras existente).

CREATE TABLE IF NOT EXISTS compras.codificacion (
    id           SERIAL PRIMARY KEY,
    codigo       VARCHAR(50) NOT NULL UNIQUE,
    nombre       VARCHAR(255) NOT NULL,
    descripcion  VARCHAR(255) NOT NULL,
    unidad       VARCHAR(30) NOT NULL,
    categoria    VARCHAR(80),
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras.insumos (
    id               SERIAL PRIMARY KEY,
    codigo           VARCHAR(50),
    nombre           VARCHAR(255) NOT NULL,
    descripcion      VARCHAR(255),
    unidad           VARCHAR(30) NOT NULL DEFAULT 'UN',
    codificacion_id  INT REFERENCES compras.codificacion(id) ON DELETE SET NULL,
    activo           BOOLEAN NOT NULL DEFAULT TRUE,
    usuario_id       INT REFERENCES public.usuarios(id) ON DELETE SET NULL,
    creado_en        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_insumos_codigo UNIQUE (codigo)
);

ALTER TABLE compras.solicitud_items
    ADD COLUMN IF NOT EXISTS codificacion_id INT
        REFERENCES compras.codificacion(id) ON DELETE SET NULL;

ALTER TABLE compras.solicitud_items
    ADD COLUMN IF NOT EXISTS insumo_id INT
        REFERENCES compras.insumos(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_codificacion_categoria
    ON compras.codificacion (categoria);

CREATE INDEX IF NOT EXISTS idx_codificacion_nombre
    ON compras.codificacion (nombre);

CREATE INDEX IF NOT EXISTS idx_insumos_codificacion
    ON compras.insumos (codificacion_id);

CREATE INDEX IF NOT EXISTS idx_insumos_nombre
    ON compras.insumos (nombre);

CREATE INDEX IF NOT EXISTS idx_solicitud_items_codificacion
    ON compras.solicitud_items (codificacion_id);

CREATE INDEX IF NOT EXISTS idx_solicitud_items_insumo
    ON compras.solicitud_items (insumo_id);
