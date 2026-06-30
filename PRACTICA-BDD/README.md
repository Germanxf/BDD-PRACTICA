
## Estructura del proyecto

```
practica_2pc/
├── coordinador/
│   ├── coordinador.py          # Orquestador 2PC
│   └── Dockerfile
├── inventario/
│   ├── participante_inventario.py  # Nodo + PostgreSQL real
│   ├── init.sql                    # Tabla medicamentos
│   └── Dockerfile
├── facturacion/
│   ├── participante_facturacion.py # Nodo + PostgreSQL real
│   ├── init.sql                    # Tabla facturas
│   └── Dockerfile
├── interfaz/
│   └── interfaz_2pc.py         # GUI Tkinter
├── docker-compose.yml
├── start.ps1                   # Arranque Windows
└── start.sh                    # Arranque Linux/Mac
```

## Requisitos

- Docker Desktop (corriendo)
- Python 3.9+ con tkinter (incluido en la instalación estándar)

## Cómo ejecutar



## PASO 1 — Entrar a la carpeta del proyecto


- cd "Ruta de la carpeta extraida"


## PASO 2 — Levantar los contenedores Docker


- docker compose up --build -d



## PASO 3 — Verificar que todo esté corriendo


- docker compose ps



## PASO 4 — Abrir la interfaz gráfica


python interfaz/interfaz_2pc.py



### 3. Verificar los datos reales en PostgreSQL

Abre una nueva ventana de PowerShell:
- cd "Ruta de la carpeta extraida"


Ver el stock de medicamentos:

- docker exec practicabdd-db_inventario-1 psql -U postgres -d inventario_db -c "SELECT * FROM medicamentos;"


Ver las facturas emitidas:

- docker exec practicabdd-db_facturacion-1 psql -U postgres -d facturacion_db -c "SELECT * FROM facturas ORDER BY id DESC LIMIT 10;"


Ver el log interno de transacciones (fase por fase):

- docker exec practicabdd-db_inventario-1 psql -U postgres -d inventario_db -c "SELECT * FROM transacciones_log ORDER BY id DESC LIMIT 10;"



## PASO FINAL — Apagar todo al terminar la demostración


- docker compose down
