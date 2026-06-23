#  Transacciones Distribuidas, Protocolos de Compromiso y Estrategias de Recuperación

**Facultad:** Ciencias de la Vida y Tecnologías  
**Carrera:** Ingeniería de Software · 4to Nivel – A  
**Fecha:** Junio 2026

**Autores:**
- Castro Zambrano Jorge Luis
- Molina Rengifo Nikolái
- Frías Mero Germán

**Docente:** Ing. Quiroz Palma Patricia

---

##  Objetivos

Explicar cómo un sistema distribuido decide entre hacer **commit** o **rollback** cuando una transacción afecta múltiples nodos, analizando los protocolos **2PC** y **3PC** como mecanismos de coordinación, partiendo desde los conceptos base hasta su implementación práctica.

---

##  Desarrollo

En las arquitecturas empresariales contemporáneas, los datos se encuentran fragmentados en múltiples subsistemas físicos para garantizar escalabilidad. Cuando una operación del negocio requiere alterar concurrentemente el estado de múltiples nodos independientes (por ejemplo, descontar el stock de un medicamento y registrar un comprobante electrónico contable), los mecanismos tradicionales de bases de datos locales son insuficientes.

Surge la necesidad de implementar **Transacciones Distribuidas**, las cuales deben satisfacer estrictamente las propiedades **ACID** a escala global, priorizando la **Atomicidad**: o se consolidan todos los cambios en todos los nodos, o el sistema entero se revierte a su estado inicial.

---

##  El Protocolo de Compromiso de Dos Fases (2PC)

El protocolo **2PC** es el mecanismo clásico para alcanzar un acuerdo atómico entre múltiples nodos. Opera alrededor de dos roles:

- **Coordinador:** orquesta la secuencia.
- **Participantes:** ejecutan las mutaciones locales sobre sus respectivos recursos.

### Fases del protocolo

#### Fase 1 — Preparación (Prepare Phase)
El coordinador envía `PREPARE` a todos los participantes. Cada participante:
1. Ejecuta la transacción localmente hasta el límite previo al commit.
2. Bloquea los recursos asignados (filas, tablas o registros).
3. Escribe sus acciones en su **Write-Ahead Log (WAL)**.
4. Responde con un voto: `VOTE_COMMIT`  o `VOTE_ABORT` .

#### Fase 2 — Compromiso (Commit Phase)
- Si **todos** los participantes votaron `VOTE_COMMIT` → el coordinador propaga `GLOBAL_COMMIT`.
- Si **al menos uno** votó negativo o se cumple un **timeout** → el coordinador propaga `GLOBAL_ROLLBACK`.

Cada participante ejecuta la instrucción final, libera los bloqueos y retorna un `ACK`.

---

##  La Problemática del Bloqueo en 2PC

El defecto fundamental de 2PC es su carácter **estrictamente síncrono y bloqueante**.

> Si el coordinador cae **después** de que los participantes votaron positivamente pero **antes** de transmitir el veredicto final, los participantes entran en un **estado de incertidumbre absoluta**.

Los recursos permanecen bloqueados indefinidamente, degradando severamente la disponibilidad del sistema. La única alternativa de restauración depende de la inspección de los **logs persistentes** tras el reinicio del coordinador.

---

## 🟢 El Protocolo de Tres Fases (3PC) como Mitigación

El protocolo **3PC** introduce una propiedad de **no-bloqueo** al dividir la segunda fase de 2PC en dos sub-etapas e incorporar **timeouts** en los participantes.

| Fase | Nombre | Descripción |
|------|--------|-------------|
| 1 | **Can Commit** | Equivalente a la fase Prepare de 2PC. Se obtienen los votos. |
| 2 | **Pre Commit** | El coordinador emite `PRE_COMMIT`. Los participantes saben que el commit está decidido, pero aún no lo hacen permanente. Si no reciben la siguiente orden dentro del umbral temporal, ejecutan **timeout** y asumen el commit de forma segura. |
| 3 | **Do Commit** | El coordinador emite `DO_COMMIT` para consolidar definitivamente los datos en disco. |

> **Limitación:** 3PC introduce un volumen significativamente mayor de mensajes de red (esquemas `4N` o `5N`) y es altamente vulnerable al **Split-Brain** en redes WAN, lo que limita su adopción en la industria.

---

##  Relación con Algoritmos de Consenso Modernos (Raft / Paxos)

A diferencia de 2PC/3PC (que requieren unanimidad), algoritmos como **Raft** o **Paxos** operan bajo una lógica de **replicación por quórum de mayoría simple** (`Q = ⌊N/2⌋ + 1`).

En **Raft**, la pérdida del líder no bloquea el sistema: los nodos supervivientes inician automáticamente una nueva elección. Mientras la mayoría esté operativa, el clúster continúa con **consistencia fuerte** y **tolerancia activa a fallos**, superando las limitaciones estructurales de 2PC.

---

## 🐳 Demo — Maqueta con Docker

La maqueta técnica simula un entorno distribuido real con **tres contenedores Docker** comunicados por HTTP:

| Contenedor | Rol |
|------------|-----|
| `coordinador` | Orquesta la transacción. Envía `PREPARE` y `COMMIT` a los participantes. |
| `inventario` | Participante que simula la gestión de stock de la sucursal. |
| `facturacion` | Participante que simula el registro contable de la venta. |

La variable de entorno `MODO_FALLO` controla el escenario a ejecutar.

### Escenario 1 — Flujo exitoso (`MODO_FALLO=0`)

El coordinador envía `PREPARE` a ambos participantes, recibe `YES` de los dos y procede a enviar `COMMIT`. Ambos confirman los cambios y liberan sus recursos.

### Escenario 2 — Fallo del coordinador (`MODO_FALLO=1`)

El coordinador recibe ambos votos `YES` pero cae con `os._exit(1)` antes de enviar `COMMIT`. Los participantes superan el **timeout de 4 segundos** y entran en estado de **INCERTIDUMBRE** con sus recursos bloqueados indefinidamente, demostrando el bloqueo estructural del 2PC.

### Comandos de ejecución

```bash
# Escenario exitoso
docker compose up

# Escenario de fallo
$env:MODO_FALLO="1"; docker compose up

# Disparar la transacción (PowerShell)
Invoke-WebRequest -Uri http://localhost:8000/venta -Method POST

# Detener contenedores
docker compose down
```

---

## 📊 Resultados

Los datos recopilados en la traza demuestran empíricamente el fallo estructural de **2PC**. Los participantes quedaron en un **limbo transaccional** conocido técnicamente como *estado de incertidumbre*. Durante este periodo, los recursos permanecen bloqueados indefinidamente, lo que paralizaría por completo la operación de un punto de venta real.

---

## 🏁 Conclusiones

### Conclusiones Arquitectónicas

El experimento demostró que el uso de protocolos síncronos puros como **2PC** compromete severamente la resiliencia operativa ante fallos de infraestructura. En sistemas altamente distribuidos geográficamente:

- El costo de mantener consistencia **CP** se traduce en una pérdida drástica de disponibilidad.
- **3PC** añade sobrecarga de red insostenible sin protección real frente a particiones WAN.

### Propuesta de Mitigación — Proyecto Integrador (Cadena de Farmacias Nacional)

El proyecto plantea el diseño de una cadena de farmacias distribuida en Ecuador (Quito, Guayaquil, Cuenca, Manta, entre otras). La infraestructura interprovincial está sujeta a fluctuaciones de latencia, cortes de fibra y micro-cortes WAN.

> Un modelo basado en **2PC clásico** provocaría que un corte de fibra en el enlace Guayaquil–Quito congele completamente las cajas de facturación locales, impidiendo despachar medicamentos a clientes.

Se emiten las siguientes directivas técnicas:

#### 1.  Rechazar 2PC en la red WAN interprovincial
Las operaciones de venta en sucursales deben seguir el principio **AP** del Teorema CAP. El punto de venta local debe facturar de forma **autónoma**, garantizando la continuidad del negocio.

#### 2.  Adoptar el Patrón Saga (Orquestación / Coreografía)
Reemplazar la atomicidad síncrona global por **Consistencia Eventual**:
- Cada acción se ejecuta como una transacción local independiente.
- Si el registro posterior en la matriz contable falla, el sistema dispara automáticamente una **Transacción de Compensación** (reponer stock o emitir nota de crédito).

#### 3.  Implementar Almacenamiento NewSQL para Datos Core
Para componentes que exijan consistencia estricta (consolidación del balance financiero), se recomienda motores con **algoritmo Raft** internamente:
- [CockroachDB](https://www.cockroachlabs.com/)
- Clústeres de PostgreSQL replicados por quórum

Esto garantiza **alta disponibilidad nativa** sin riesgos de bloqueo por fallo de nodo único.
