# Bitacora de Ejecucion - Protocolo 2PC

## Comandos utilizados

```bash
# Levantar contenedores
docker compose up

# Disparar la transaccion
Invoke-WebRequest -Uri http://localhost:8000/venta -Method POST

# Escenario de fallo
$env:MODO_FALLO="1"; docker compose up
```

## Escenario 1 - Flujo exitoso

| Fase | Accion | Estado observado |
| :--- | :--- | :--- |
| Inicio | `docker compose up` | 3 contenedores levantados en puertos 8000, 8001, 8002 |
| Fase 1 | Coordinador envia PREPARE a ambos participantes | Inventario y Facturacion: ESTADO = PREPARED |
| Fase 2 | Coordinador envia COMMIT a ambos participantes | Inventario y Facturacion: ESTADO = COMMITTED |
| Cierre | Transaccion completada | Sistema en IDLE, sin bloqueos |

![Captura flujo exitoso](capturas/Escenario 1 - Flujo exitoso.png)

## Escenario 2 - Fallo del coordinador

| Fase | Accion | Estado observado |
| :--- | :--- | :--- |
| Inicio | `MODO_FALLO=1 docker compose up` | Coordinador inicia en modo fallo |
| Fase 1 | Ambos participantes responden YES | ESTADO = PREPARED |
| Fallo | `os._exit(1)` ejecutado | Coordinador cae, exit code 1 |
| Bloqueo | Timeout de 4 segundos superado | ESTADO = INCERTIDUMBRE. Recursos bloqueados indefinidamente |

![Captura fallo coordinador](capturas/Escenario 2 - Fallo del coordinador.png)