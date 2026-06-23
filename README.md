Transacciones Distribuidas, Protocolos de Compromiso y Estrategias de Recuperación
Facultad Ciencias de la Vida y Tecnologías

Carrera Ingeniería de Software 4to. Nivel – A
Autores:

Castro Zambrano Jorge Luis
Molina Rengifo Nikolái
Frías Mero Germán

Profesor/a: Ing. Quiroz Palma Patricia

Fecha: Junio – 2026

Objetivos
Explicar como un sistema distribuido decide entre hacer commit o rollback cuando una transacción afecta múltiples nodos, analizando los protocolos 2PC y 3PC como mecanismos de coordinación, partiendo desde los conceptos base hasta su implementación práctica.
Desarrollo
En las arquitecturas empresariales contemporáneas, los datos se encuentran fragmentados en múltiples subsistemas físicos para garantizar escalabilidad. Sin embargo, cuando una operación del negocio requiere alterar concurrentemente el estado de múltiples nodos independientes (por ejemplo, descontar el stock de un medicamento y registrar un comprobante electrónico contable), los mecanismos tradicionales de bases de datos locales son insuficientes. Surge la necesidad de implementar Transacciones Distribuidas, las cuales deben satisfacer estrictamente las propiedades ACID a escala global, priorizando la Atomicidad: o se consolidan todos los cambios en todos los nodos, o el sistema entero se revierte a su estado inicial.
El Protocolo de Compromiso de Dos Fases (2PC)
El protocolo 2PC es el mecanismo clásico para alcanzar un acuerdo atómico entre múltiples nodos. Estructura el flujo operacional alrededor de dos roles claramente diferenciados: un único nodo Coordinador, que orquesta la secuencia, y múltiples nodos Participantes, que ejecutan las mutaciones locales sobre sus respectivos recursos. El protocolo opera en dos etapas discretas:

Fase de Preparación (Prepare Phase): El coordinador envía una notificación de preparación (PREPARE) a todos los participantes. Cada participante ejecuta la transacción localmente hasta el límite previo a su consolidación definitiva, bloqueando los recursos asignados (filas, tablas o registros), escribe sus acciones en su Write-Ahead Log (WAL) local y responde con un voto: VOTE_COMMIT si está listo o VOTE_ABORT si experimentó un fallo.
Fase de Compromiso (Commit Phase): El coordinador recopila todos los votos. Si y solo si el total de participantes respondió unánimemente con un VOTE_COMMIT, el coordinador escribe la decisión en su propio log físico y propaga un mensaje global de GLOBAL_COMMIT. En caso de que exista al menos un voto negativo o se cumpla un tiempo de espera (timeout), el coordinador decide abortar y propaga un GLOBAL_ROLLBACK. Cada participante ejecuta la instrucción final, libera los bloqueos y retorna un acuse de recibo (ACK).

La Problemática del Bloqueo en 2PC y la Necesidad de Recuperación por Logs
El defecto fundamental de 2PC radica en su carácter estrictamente síncrono y bloqueante. Si el nodo coordinador sufre una desconexión o un fallo de hardware catastrófico inmediatamente después de que los participantes han votado positivamente pero antes de transmitir el veredicto final, los participantes entran en un estado de incertidumbre absoluta. Debido a que han comprometido su voto, los participantes no pueden tomar una decisión unilateral de abortar o consolidar de forma autónoma, ya que desconocen si el coordinador llegó a notificar a otros nodos. En consecuencia, los recursos permanecen bloqueados indefinidamente, degradando severamente la disponibilidad del sistema. La única alternativa de restauración depende de la inspección manual o automatizada de los logs persistentes tras el reinicio del coordinador accidentado.
El Protocolo de Compromiso de Tres Fases (3PC) como Mitigación
Para resolver el bloqueo permanente de 2PC, se diseñó el protocolo 3PC. Este introduce una propiedad de no-bloqueo al dividir la segunda fase en dos sub-etapas e incorporar una restricción de temporización (timeouts) en los participantes. Las fases de 3PC se definen como:

Fase 1: Can Commit: Equivalente a la fase de preparación de 2PC. Se obtienen los votos.
Fase 2: Pre Commit: Si los votos son unánimes, el coordinador emite un mensaje de PRE_COMMIT. Los participantes entran en un estado intermedio donde saben que la decisión global es confirmar, pero aún no hacen permanentes los cambios. Si un participante no recibe el siguiente mensaje dentro de un umbral temporal, ejecuta un timeout y asume con seguridad el commit.
Fase 3: Do Commit: El coordinador emite la orden final de DO_COMMIT para consolidar definitivamente los datos en disco de forma síncrona.

A pesar de eliminar el bloqueo ante caídas del coordinador en redes ideales, 3PC introduce un volumen significativamente mayor de mensajes de red (esquemas 4N o 5N) y es altamente vulnerable al fenómeno del Split-Brain (Cerebro Dividido) cuando ocurren particiones de red de topología WAN, motivo por el cual su adopción práctica en la industria es limitada.
Relación con Algoritmos de Consenso Modernos (Raft / Paxos)
A diferencia de los protocolos de compromiso (donde todos los nodos deben coordinarse unánimemente para validar una transacción), los algoritmos de consenso como Raft o Paxos operan bajo una lógica de replicación por quórum de mayoría simple (Q=[N/2]+1). En Raft, la pérdida del nodo líder no interrumpe ni bloquea el progreso del sistema de forma permanente; los nodos supervivientes inician una nueva fase de elección de manera automatizada. Mientras la mayoría de los nodos esté operativa, el clúster continúa procesando escrituras con consistencia fuerte y tolerancia activa a fallos, superando por completo las limitaciones estructurales de 2PC.
Demo
La maqueta técnica está compuesta por tres contenedores Docker que se comunican mediante peticiones HTTP sobre una red interna, simulando un entorno distribuido real:

coordinador: Orquesta la transacción, envía PREPARE y COMMIT a los participantes y controla el flujo del protocolo 2PC.
inventario: Participante que recibe PREPARE, COMMIT y ROLLBACK. Simula la gestión de stock de la sucursal.
facturacion: Participante que recibe PREPARE, COMMIT y ROLLBACK. Simula el registro contable de la venta.

La variable de entorno MODO_FALLO controla el escenario a ejecutar:
Escenario 1 - Flujo exitoso (MODO_FALLO=0): El coordinador envía PREPARE a ambos participantes, recibe respuesta afirmativa de los dos y procede a enviar COMMIT. Ambos confirman los cambios y liberan sus recursos.
Escenario 2 - Fallo del coordinador (MODO_FALLO=1): El coordinador recibe ambos votos YES pero cae con os._exit(1) antes de enviar COMMIT. Los participantes superan el timeout de 4 segundos y entran en estado de INCERTIDUMBRE con sus recursos bloqueados indefinidamente, demostrando el bloqueo estructural del 2PC.
Comandos de ejecución
bash# Escenario exitoso
docker compose up

# Escenario de fallo
$env:MODO_FALLO="1"; docker compose up

# Disparar la transacción (PowerShell)
Invoke-WebRequest -Uri http://localhost:8000/venta -Method POST

# Detener contenedores
docker compose down
Resultados
Los datos recopilados en la traza demuestran empíricamente el fallo estructural de 2PC. Los participantes quedaron en un limbo transaccional conocido técnicamente como estado de incertidumbre. Durante este periodo los recursos permanecen bloqueados indefinidamente, lo que paralizaría por completo la operación de un punto de venta real.
Conclusiones
Conclusiones Arquitectónicas
El experimento demostró que el uso de protocolos síncronos puros como 2PC compromete severamente la resiliencia operativa ante fallos de infraestructura. En sistemas altamente distribuidos geográficamente, el costo de mantener una consistencia lineal e inmediata (CP) se traduce en una pérdida drástica de disponibilidad, un riesgo inaceptable para sistemas orientados al consumidor final. 3PC, por su parte, añade una sobrecarga de red insostenible sin ofrecer una protección real frente a particiones de conectividad.
Propuesta de Mitigación y Recomendación para el Proyecto Integrador
El Proyecto Integrador plantea el diseño arquitectónico de una cadena de farmacias distribuidas a nivel nacional en Ecuador (conectando sucursales críticas en Quito, Guayaquil, Cuenca, Manta, entre otras). La infraestructura de red interprovincial en el país está sujeta de manera inherente a fluctuaciones de latencia, cortes de fibra y micro-cortes de conectividad WAN. Si se implementara un modelo de transacciones distribuidas basado en 2PC clásico, un corte de fibra o latencia elevada en el enlace Guayaquil-Quito durante una venta provocaría que las cajas de facturación locales de la sucursal de Guayaquil queden completamente congeladas, impidiendo despachar medicamentos a los clientes locales debido a la retención de bloqueos a nivel de base de datos centralizada.
Por lo tanto, se emite la siguiente directiva técnica para la arquitectura del sistema del Proyecto Integrador:

Rechazar el uso de 2PC en la red WAN interprovincial: Las operaciones de venta de medicamentos en las sucursales deben diseñarse siguiendo el principio AP (Disponibilidad y Tolerancia a Particiones) del teorema CAP. El punto de venta local debe facturar de forma autónoma garantizando la continuidad del negocio.
Adoptar el Patrón Saga (Orquestación/Coreografía): Reemplazar la atomicidad síncrona global por una estrategia de Consistencia Eventual. Cada acción se ejecuta como una transacción local independiente. Si el registro posterior en la matriz contable centralizada falla tras múltiples reintentos asíncronos debido a una desconexión, el sistema dispara automáticamente una Transacción de Compensación (por ejemplo, reponer el stock reservado o emitir una nota de crédito automatizada).
Implementación de Almacenamiento NewSQL para Datos Core: Para componentes críticos que exijan consistencia estricta indestructible (como la consolidación general del balance financiero), se recomienda delegar el control en motores de bases de datos distribuidos modernos que utilicen el algoritmo de consenso Raft internamente (como CockroachDB o clústeres de PostgreSQL replicados por quórum), garantizando alta disponibilidad nativa sin riesgos de bloqueo en el limbo por fallo de nodo único.
