CREATE TABLE IF NOT EXISTS facturas (
    id SERIAL PRIMARY KEY,
    numero_factura VARCHAR(20) UNIQUE NOT NULL,
    cliente VARCHAR(100) NOT NULL,
    subtotal NUMERIC(10,2),
    iva NUMERIC(10,2),
    total NUMERIC(10,2),
    estado VARCHAR(20) DEFAULT 'PENDIENTE',
    fecha TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transacciones_log (
    id SERIAL PRIMARY KEY,
    transaccion_id VARCHAR(50),
    fase VARCHAR(30),
    estado VARCHAR(30),
    detalle TEXT,
    ts TIMESTAMP DEFAULT NOW()
);
