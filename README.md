# [cite_start]Transacciones Distribuidas, Protocolos de Compromiso y Estrategias de Recuperación [cite: 65]

[cite_start]**Facultad Ciencias de la Vida y Tecnologías** [cite: 62]
**Carrera Ingeniería de Software 4to. [cite_start]Nivel – A** [cite: 63]

[cite_start]**Autores:** [cite: 66]
* [cite_start]Molina Nikolái [cite: 67]
* Castro Jorge [cite: 68]
* [cite_start]Frías Germán [cite: 69]

**Profesor/a:** Ing. [cite_start]Israel [cite: 70, 71]
[cite_start]**Fecha:** Junio – 2026 [cite: 72, 73]

---

## Objetivos
[cite_start]Diseñar, analizar e implementar una maqueta técnica reproducible que evalúe el comportamiento de las transacciones distribuidas bajo los protocolos de compromiso de dos fases (2PC) y tres fases (3PC), identificando formalmente los escenarios de bloqueo sistémico causados por fallos en el nodo coordinador, con el fin de emitir una recomendación arquitectónica fundamentada para el Proyecto Integrador de la cadena de farmacias en el territorio ecuatoriano. [cite: 75]

## Desarrollo
[cite_start]En las arquitecturas empresariales contemporáneas, los datos se encuentran fragmentados en múltiples subsistemas físicos para garantizar escalabilidad. [cite: 77] [cite_start]Sin embargo, cuando una operación del negocio requiere alterar concurrentemente el estado de múltiples nodos independientes (por ejemplo, descontar el stock de un medicamento y registrar un comprobante electrónico contable), los mecanismos tradicionales de bases de datos locales son insuficientes. [cite: 78] [cite_start]Surge la necesidad de implementar Transacciones Distribuidas, las cuales deben satisfacer estrictamente las propiedades ACID a escala global, priorizando la Atomicidad: o se consolidan todos los cambios en todos los nodos, o el sistema entero se revierte a su estado inicial. [cite: 79]

### El Protocolo de Compromiso de Dos Fases (2PC)
[cite_start]El protocolo 2PC es el mecanismo clásico para alcanzar un acuerdo atómico entre múltiples nodos. [cite: 81] [cite_start]Estructura el flujo operacional alrededor de dos roles claramente diferenciados: un único nodo Coordinador, que orquesta la secuencia, y múltiples nodos Participantes, que ejecutan las mutaciones locales sobre sus respectivos recursos [1]. [cite: 82] [cite_start]El protocolo opera en dos etapas discretas: [cite: 83]

* **Fase de Preparación (Prepare Phase):** El coordinador envía una notificación de preparación (PREPARE) a todos los participantes. [cite: 84] Cada participante ejecuta la transacción localmente hasta el límite previo a su consolidación definitiva, bloqueando los recursos asignados (filas, tablas o registros), escribe sus acciones en su Write-Ahead Log (WAL) local y responde con un voto: VOTE_COMMIT si está listo o VOTE_ABORT si experimentó un fallo. [cite: 85]
* [cite_start]**Fase de Compromiso (Commit Phase):** El coordinador recopila todos los votos. [cite: 86] [cite_start]Si y solo si el total de participantes respondió unánimemente con un VOTE_COMMIT, el coordinador escribe la decisión en su propio log físico y propaga un mensaje global de GLOBAL_COMMIT. [cite: 87] [cite_start]En caso de que exista al menos un voto negativo o se cumpla un tiempo de espera (timeout), el coordinador decide abortar y propaga un GLOBAL_ROLLBACK. [cite: 88] [cite_start]Cada participante ejecuta la instrucción final, libera los bloqueos y retorna un acuse de recibo (ACK). [cite: 89]

### La Problemática del Bloqueo en 2PC y la Necesidad de Recuperación por Logs
[cite_start]El defecto fundamental de 2PC radica en su carácter estrictamente síncrono y bloqueante. [cite: 91] [cite_start]Si el nodo coordinador sufre una desconexión o un fallo de hardware catastrófico inmediatamente después de que los participantes han votado positivamente pero antes de transmitir el veredicto final, los participantes entran en un estado de incertidumbre absoluta. [cite: 92] [cite_start]Debido a que han comprometido su voto, los participantes no pueden tomar una decisión unilateral de abortar o consolidar de forma autónoma, ya que desconocen si el coordinador llegó a notificar a otros nodos. [cite: 93] [cite_start]En consecuencia, los recursos permanecen bloqueados indefinidamente, degradando severamente la disponibilidad del sistema. [cite: 94] [cite_start]La única alternativa de restauración depende de la inspección manual o automatizada de los logs persistentes tras el reinicio del coordinador accidentado. [cite: 95]

### El Protocolo de Compromiso de Tres Fases (3PC) como Mitigación
[cite_start]Para resolver el bloqueo permanente de 2PC, se diseñó el protocolo 3PC. [cite: 97] [cite_start]Este introduce una propiedad de no-bloqueo al dividir la segunda fase en dos sub-etapas e incorporar una restricción de temporización (timeouts) en los participantes [2]. [cite: 98] [cite_start]Las fases de 3PC se definen como: [cite: 99]
* **Fase 1: Can Commit:** Equivalente a la fase de preparación de 2PC. [cite_start]Se obtienen los votos. [cite: 100]
* **Fase 2: Pre Commit:** Si los votos son unánimes, el coordinador emite un mensaje de PRE_COMMIT. [cite: 101] Los participantes entran en un estado intermedio donde saben que la decisión global es confirmar, pero aún no hacen permanentes los cambios. [cite: 102] Si un participante no recibe el siguiente mensaje dentro de un umbral temporal, ejecuta un timeout y asume con seguridad el commit. [cite: 103]
* [cite_start]**Fase 3: Do Commit:** El coordinador emite la orden final de DO_COMMIT para consolidar definitivamente los datos en disco de forma síncrona. [cite: 104]
[cite_start]A pesar de eliminar el bloqueo ante caídas del coordinador en redes ideales, 3PC introduce un volumen significativamente mayor de mensajes de red (esquemas 4N o 5N) y es altamente vulnerable al fenómeno del Split-Brain (Cerebro Dividido) cuando ocurren particiones de red de topología WAN, motivo por el cual su adopción práctica en la industria es limitada [4]. [cite: 105]

### Relación con Algoritmos de Consenso Modernos (Raft / Paxos)
[cite_start]A diferencia de los protocolos de compromiso (donde todos los nodos deben coordinarse unánimemente para validar una transacción), los algoritmos de consenso como Raft o Paxos operan bajo una lógica de replicación por quórum de mayoría simple (Q=[N/2]+1) [3]. [cite: 107] [cite_start]En Raft, la pérdida del nodo líder no interrumpe ni bloquea el progreso del sistema de forma permanente; [cite: 108] [cite_start]los nodos supervivientes inician una nueva fase de elección de manera automatizada. [cite: 109] [cite_start]Mientras la mayoría de los nodos esté operativa, el clúster continúa procesando escrituras con consistencia fuerte y tolerancia activa a fallos, superando por completo las limitaciones estructurales de 2PC. [cite: 110]

## Demo
[cite_start]Para validar de forma empírica el comportamiento bloqueante del protocolo 2PC, se desarrolló una maqueta técnica compuesta por tres microservicios independientes integrados dentro de una red virtual privada y aislada. [cite: 112] [cite_start]La infraestructura técnica está constituida por los siguientes componentes distribuidos: [cite: 113]
* [cite_start]**coordinador-tx:** Servicio encargado de la orquestación, recepción de peticiones del cliente, emisión de directivas distribuidas y persistencia de la bitácora global. [cite: 114]
* **participante-inventario:** Nodo esclavo encargado de la reserva y mutación de existencias físicas de productos de la sucursal. [cite: 115]
* [cite_start]**participante-facturacion:** Nodo esclavo encargado de procesar el registro contable y la emisión del comprobante tributario. [cite: 116]

[cite_start]El escenario experimental crítico diseñado para forzar el fallo consiste en alterar el flujo lógico estándar del coordinador. [cite: 117] [cite_start]Tras enviar la señal de PREPARE y recolectar exitosamente los acuses de recibo afirmativos de ambos participantes, el código ejecuta una terminación abrupta e inducida de su proceso (process.exit(1)), impidiendo de forma deliberada el envío de los mensajes de confirmación (COMMIT) o reversión (ROLLBACK). [cite: 118]

## Resultados
[cite_start]Los datos recopilados en la traza demuestran empíricamente el fallo estructural de 2PC. [cite: 124] [cite_start]Los participantes quedaron en un limbo transaccional conocido técnicamente como estado de incertidumbre distribuidora. [cite: 125] [cite_start]Durante este periodo, las solicitudes entrantes que requerían acceso a los mismos recursos farmacéuticos (SKU-44102) experimentaron fallos por timeout de lectura/escritura, lo que paralizaría por completo la operación de un punto de venta real. [cite: 126]

## Conclusiones

### Conclusiones Arquitectónicas
[cite_start]El experimento demostró que el uso de protocolos síncronos puros como 2PC compromete severamente la resiliencia operativa ante fallos de infraestructura. [cite: 133] [cite_start]En sistemas altamente distribuidos geográficamente, el costo de mantener una consistencia lineal e inmediata (CP) se traduce en una pérdida drástica de disponibilidad, un riesgo inaceptable para sistemas orientados al consumidor final. [cite: 134] [cite_start]3PC, por su parte, añade una sobrecarga de red insostenible sin ofrecer una protección real frente a particiones de conectividad. [cite: 135]

### Propuesta de Mitigación y Recomendación para el Proyecto Integrador
[cite_start]El Proyecto Integrador plantea el diseño arquitectónico de una cadena de farmacias distribuidas a nivel nacional en Ecuador (conectando sucursales críticas en Quito, Guayaquil, Cuenca, Manta, entre otras). [cite: 137] [cite_start]La infraestructura de red interprovincial en el país está sujeta de manera inherente a fluctuaciones de latencia, cortes de fibra y micro-cortes de conectividad WAN. [cite: 138] [cite_start]Si se implementara un modelo de transacciones distribuidas basado en 2PC clásico, un corte de fibra o latencia elevada en el enlace Guayaquil-Quito durante una venta provocaría que las cajas de facturación locales de la sucursal de Guayaquil queden completamente congeladas, impidiendo despachar medicamentos a los clientes locales debido a la retención de bloqueos a nivel de base de datos centralizada. [cite: 139]

[cite_start]Por lo tanto, se emite la siguiente directiva técnica para la arquitectura del sistema del Proyecto Integrador: [cite: 140]
1. [cite_start]**Rechazar el uso de 2PC en la red WAN interprovincial:** Las operaciones de venta de medicamentos en las sucursales deben diseñarse siguiendo el principio AP (Disponibilidad y Tolerancia a Particiones) del teorema CAP. [cite: 141] [cite_start]El punto de venta local debe facturar de forma autónoma garantizando la continuidad del negocio. [cite: 142]
2. [cite_start]**Adoptar el Patrón Saga (Orquestación/Coreografía):** Reemplazar la atomicidad síncrona global por una estrategia de Consistencia Eventual. [cite: 143] Cada acción se ejecuta como una transacción local independiente. [cite_start]Si el registro posterior en la matriz contable centralizada falla tras múltiples reintentos asíncronos debido a una desconexión, el sistema dispara automáticamente una Transacción de Compensación (por ejemplo, reponer el stock reservado o emitir una nota de crédito automatizada). [cite: 144]
3. [cite_start]**Implementación de Almacenamiento NewSQL para Datos Core:** Para componentes críticos que exijan consistencia estricta indestructible (como la consolidación general del balance financiero), se recomienda delegar el control en motores de bases de datos distribuidos modernos que utilicen el algoritmo de consenso Raft internamente (como CockroachDB o clústeres de PostgreSQL replicados por quórum), garantizando alta disponibilidad nativa sin riesgos de bloqueo en el limbo por fallo de nodo único. [cite: 145]
