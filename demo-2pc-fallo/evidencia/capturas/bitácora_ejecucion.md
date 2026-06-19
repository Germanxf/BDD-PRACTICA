# Bitácora de Ejecución - Demostración Protocolo 2PC

| Fase | Acción Ejecutada | Resultado Esperado | Observación / Estado |
| :--- | :--- | :--- | :--- |
| **Inicio** | Ejecución de `docker-compose up` | Tres contenedores levantados en red local puente. | Nodos a la escucha en puertos 8000, 8001 y 8002. |
| **Fase 1 (Prepare)** | Envío de petición `POST /venta` al puerto 8000. | Coordinador envía señales a Inventario y Facturación. | Ambos participantes cambian su estado a `PREPARED`. |
| **Simulación de Fallo** | Ejecución de `os._exit(1)` en script del coordinador. | Contenedor del Coordinador se detiene (Exit code 1). | El coordinador jamás envía la orden de `COMMIT`. |
| **Bloqueo (Incertidumbre)** | Espera de 4+ segundos en los nodos participantes. | Los participantes entran en ciclo de advertencia. | El sistema colapsa; los registros simulados quedan bloqueados permanentemente. |

## Checklist de Capturas Adjuntas (Carpeta /capturas)
- [ ] Captura 1: El código de `docker-compose.yml` en el editor.
- [ ] Captura 2: Terminal tras ejecutar `docker-compose up`.
- [ ] Captura 3: Los logs de la terminal mostrando el "FATAL ERROR" y los recursos bloqueados.