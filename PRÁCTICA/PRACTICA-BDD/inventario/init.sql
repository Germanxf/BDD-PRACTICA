CREATE TABLE IF NOT EXISTS medicamentos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    stock INTEGER NOT NULL,
    precio NUMERIC(10,2) NOT NULL,
    sucursal VARCHAR(50) NOT NULL
);

INSERT INTO medicamentos (nombre, stock, precio, sucursal) VALUES
    ('Paracetamol 500mg', 150, 0.45, 'Quito-Norte'),
    ('Amoxicilina 500mg', 80,  1.20, 'Quito-Norte'),
    ('Ibuprofeno 400mg',  200, 0.60, 'Quito-Norte'),
    ('Metformina 850mg',  60,  0.90, 'Quito-Norte'),
    ('Losartan 50mg',     45,  1.10, 'Quito-Norte');

CREATE TABLE IF NOT EXISTS transacciones_log (
    id SERIAL PRIMARY KEY,
    transaccion_id VARCHAR(50),
    fase VARCHAR(30),
    estado VARCHAR(30),
    detalle TEXT,
    ts TIMESTAMP DEFAULT NOW()
);
