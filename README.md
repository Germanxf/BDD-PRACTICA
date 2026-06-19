# Transacciones Distribuidas, Protocolos de Compromiso y Estrategias de Recuperación

**Facultad Ciencias de la Vida y Tecnologías**
**Carrera Ingeniería de Software 4to. Nivel – A**

**Autores:**
* Molina Nikolái
* Castro Jorge
* Frías Germán

**Profesor/a:** Ing. Israel
**Fecha:** Junio – 2026

---

## Objetivos
Diseñar, analizar e implementar una maqueta técnica reproducible que evalúe el comportamiento de las transacciones distribuidas bajo los protocolos de compromiso de dos fases (2PC) y tres fases (3PC), identificando formalmente los escenarios de bloqueo sistémico causados por fallos en el nodo coordinador, con el fin de emitir una recomendación arquitectónica fundamentada para el Proyecto Integrador de la cadena de farmacias en el territorio ecuatoriano.

## Desarrollo
En las arquitecturas empresariales contemporáneas, los datos se encuentran fragmentados en múltiples subsistemas físicos para garantizar escalabilidad. Sin embargo, cuando una operación del negocio requiere alterar concurrentemente el estado de múltiples nodos independientes (por ejemplo, descontar el stock de un medicamento y registrar un comprobante electrónico contable), los mecanismos tradicionales de bases de datos locales son insuficientes. Surge la necesidad de implementar Transacciones Distribuidas, las cuales deben satisfacer estrictamente las propiedades ACID a escala global, priorizando la Atomicidad: o se consolidan todos los cambios en todos los nodos, o el sistema entero se revierte a su estado inicial.

### El Protocolo de Compromiso de Dos Fases (2PC)
El protocolo 2PC es el mecanismo clásico para alcanzar un acuerdo atómico entre múltiples nodos. Estructura el flujo operacional alrededor de dos roles claramente diferenciados: un único nodo Coordinador, que orquesta la secuencia, y múltiples nodos Participantes, que ejecutan las mutaciones locales sobre sus respectivos recursos. El protocolo opera en dos etapas discretas:

* **Fase de Preparación (Prepare Phase):** El coordinador envía una notificación de preparación (PREPARE) a todos los participantes. Cada participante ejecuta la transacción localmente hasta el límite previo a su consolidación definitiva, bloqueando los recursos asignados (filas, tablas o registros), escribe sus acciones en su Write-Ahead Log (WAL) local y responde con un voto: VOTE_COMMIT si está listo o VOTE_ABORT si experimentó un fallo.
* **Fase de Compromiso (Commit Phase):** El coordinador recopila todos los votos. Si y solo si el total de participantes respondió unánimemente con un VOTE_COMMIT, el coordinador escribe la decisión en su propio log físico y propaga un mensaje global de GLOBAL_COMMIT. En caso de que exista al menos un voto negativo o se cumpla un tiempo de espera (timeout), el coordinador decide abortar y propaga un GLOBAL_ROLLBACK. Cada participante ejecuta la instrucción final, libera los bloqueos y retorna un acuse de recibo (ACK).

### La Problemática del Bloqueo en 2PC y la Necesidad de Recuperación por Logs
El defecto fundamental de 2PC radica en su carácter estrictamente síncrono y bloqueante. Si el nodo coordinador sufre una desconexión o un fallo de hardware catastrófico inmediatamente después de que los participantes han votado positivamente pero antes de transmitir el veredicto final, los participantes entran en un estado de incertidumbre absoluta. Debido a que han comprometido su voto, los participantes no pueden tomar una decisión unilateral de abortar o consolidar de forma autónoma, ya que desconocen si el coordinador llegó a notificar a otros nodos. En consecuencia, los recursos permanecen bloqueados indefinidamente, degradando severamente la disponibilidad del sistema. La única alternativa de restauración depende de la inspección manual o automatizada de los logs persistentes tras el reinicio del coordinador accidentado.

### El Protocolo de Compromiso de Tres Fases (3PC) como Mitigación
Para resolver el bloqueo permanente de 2PC, se diseñó el protocolo 3PC. Este introduce una propiedad de no-bloqueo al dividir la segunda fase en dos sub-etapas e incorporar una restricción de temporización (timeouts) en los participantes. Las fases de 3PC se definen como:
* **Fase 1: Can Commit:** Equivalente a la fase de preparación de 2PC. Se obtienen los votos.
* **Fase 2: Pre Commit:** Si los votos son unánimes, el coordinador emite un mensaje de PRE_COMMIT. Los participantes entran en un estado intermedio donde saben que la decisión global es confirmar, pero aún no hacen permanentes los cambios. Si un participante no recibe el siguiente mensaje dentro de un umbral temporal, ejecuta un timeout y asume con seguridad el commit.
* **Fase 3: Do Commit:** El coordinador emite la orden final de DO_COMMIT para consolidar definitivamente los datos en disco de forma síncrona.
A pesar de eliminar el bloqueo ante caídas del coordinador en redes ideales, 3PC introduce un volumen significativamente mayor de mensajes de red (esquemas 4N o 5N) y es altamente vulnerable al fenómeno del Split-Brain (Cerebro Dividido) cuando ocurren particiones de red de topología WAN, motivo por el cual su adopción práctica en la industria es limitada.

### Relación con Algoritmos de Consenso Modernos (Raft / Paxos)
A diferencia de los protocolos de compromiso (donde todos los nodos deben coordinarse unánimemente para validar una transacción), los algoritmos de consenso como Raft o Paxos operan bajo una lógica de replicación por quórum de mayoría simple (Q=[N/2]+1). En Raft, la pérdida del nodo líder no interrumpe ni bloquea el progreso del sistema de forma permanente; los nodos supervivientes inician una nueva fase de elección de manera automatizada. Mientras la mayoría de los nodos esté operativa, el clúster continúa procesando escrituras con consistencia fuerte y tolerancia activa a fallos, superando por completo las limitaciones estructurales de 2PC.

## Demo
Para validar de forma empírica el comportamiento bloqueante del protocolo 2PC, se desarrolló una maqueta técnica compuesta por tres microservicios independientes integrados dentro de una red virtual privada y aislada. La infraestructura técnica está constituida por los siguientes componentes distribuidos:
* **coordinador-tx:** Servicio encargado de la orquestación, recepción de peticiones del cliente, emisión de directivas distribuidas y persistencia de la bitácora global.
* **participante-inventario:** Nodo esclavo encargado de la reserva y mutación de existencias físicas de productos de la sucursal.
* **participante-facturacion:** Nodo esclavo encargado de procesar el registro contable y la emisión del comprobante tributario.

El escenario experimental crítico diseñado para forzar el fallo consiste en alterar el flujo lógico estándar del coordinador. Tras enviar la señal de PREPARE y recolectar exitosamente los acuses de recibo afirmativos de ambos participantes, el código ejecuta una terminación abrupta e inducida de su proceso (process.exit(1)), impidiendo de forma deliberada el envío de los mensajes de confirmación (COMMIT) o reversión (ROLLBACK).

## Resultados
Los datos recopilados en la traza demuestran empíricamente el fallo estructural de 2PC. Los participantes quedaron en un limbo transaccional conocido técnicamente como estado de incertidumbre distribuidora. Durante este periodo, las solicitudes entrantes que requerían acceso a los mismos recursos farmacéuticos (SKU-44102) experimentaron fallos por timeout de lectura/escritura, lo que paralizaría por completo la operación de un punto de venta real.

## Conclusiones

### Conclusiones Arquitectónicas
El experimento demostró que el uso de protocolos síncronos puros como 2PC compromete severamente la resiliencia operativa ante fallos de infraestructura. En sistemas altamente distribuidos geográficamente, el costo de mantener una consistencia lineal e inmediata (CP) se traduce en una pérdida drástica de disponibilidad, un riesgo inaceptable para sistemas orientados al consumidor final. 3PC, por su parte, añade una sobrecarga de red insostenible sin ofrecer una protección real frente a particiones de conectividad.

### Propuesta de Mitigación y Recomendación para el Proyecto Integrador
El Proyecto Integrador plantea el diseño arquitectónico de una cadena de farmacias distribuidas a nivel nacional en Ecuador (conectando sucursales críticas en Quito, Guayaquil, Cuenca, Manta, entre otras). La infraestructura de red interprovincial en el país está sujeta de manera inherente a fluctuaciones de latencia, cortes de fibra y micro-cortes de conectividad WAN. Si se implementara un modelo de transacciones distribuidas basado en 2PC clásico, un corte de fibra o latencia elevada en el enlace Guayaquil-Quito durante una venta provocaría que las cajas de facturación locales de la sucursal de Guayaquil queden completamente congeladas, impidiendo despachar medicamentos a los clientes locales debido a la retención de bloqueos a nivel de base de datos centralizada.

Por lo tanto, se emite la siguiente directiva técnica para la arquitectura del sistema del Proyecto Integrador:
1. **Rechazar el uso de 2PC en la red WAN interprovincial:** Las operaciones de venta de medicamentos en las sucursales deben diseñarse siguiendo el principio AP (Disponibilidad y Tolerancia a Particiones) del teorema CAP. El punto de venta local debe facturar de forma autónoma garantizando la continuidad del negocio.
2. **Adoptar el Patrón Saga (Orquestación/Coreografía):** Reemplazar la atomicidad síncrona global por una estrategia de Consistencia Eventual. Cada acción se ejecuta como una transacción local independiente. Si el registro posterior en la matriz contable centralizada falla tras múltiples reintentos asíncronos debido a una desconexión, el sistema dispara automáticamente una Transacción de Compensación (por ejemplo, reponer el stock reservado o emitir una nota de crédito automatizada).
3. **Implementación de Almacenamiento NewSQL para Datos Core:** Para componentes críticos que exijan consistencia estricta indestructible (como la consolidación general del balance financiero), se recomienda delegar el control en motores de bases de datos distribuidos modernos que utilicen el algoritmo de consenso Raft internamente (como CockroachDB o clústeres de PostgreSQL replicados por quórum), garantizando alta disponibilidad nativa sin riesgos de bloqueo en el limbo por fallo de nodo único.
