# User Stories y Criterios de Aceptación (Gherkin) — Caso Eventos Nova

**Universidad Autónoma de Nuevo León (UANL) · FIME**  
**Unidad 2 y PIA · Análisis de Requerimientos de Negocio · Equipo 16**  
**Documento PDF original:** [`User_Stories_final.pdf`](User_Stories_final.pdf)

---

## Introducción
Este documento presenta las **18 historias de usuario (User Stories)** elaboradas a partir de la entrevista simulada al stakeholder del caso Eventos Nova. Cada historia sigue el formato *"Como [rol], quiero [capacidad], para [beneficio]"* y cuenta con criterios de aceptación redactados en notación **Gherkin (`Dado que` / `Cuando` / `Entonces`)**.

Se incorpora además un indicador de importancia (**Alta** / **Media**) para cada historia, que refleja su criticidad para la operación del negocio y sirve como referencia para la priorización del backlog.

---

## Resumen de Historias con Nivel de Importancia

| ID | Rol | Quiero | Para | Importancia | Reglas / FR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **US-01** | Cliente | Solicitar la cotización de mi evento con al menos 15 días naturales de anticipación | Garantizar disponibilidad de fecha y proveedores | Alta | BR-01, FR-01 |
| **US-02** | Cliente | Poder modificar mi evento hasta 7 días naturales antes de la fecha | Ajustar detalles sin poner en riesgo la ejecución | Alta | BR-02, FR-02 |
| **US-03** | Coordinador | Que el número definitivo de invitados quede confirmado 7 días naturales antes del evento | Ajustar alimentos, mobiliario y servicios contratados por cantidad | Alta | BR-03, FR-03 |
| **US-04** | Coordinador | Que cada proveedor tenga un límite de 48 horas para confirmar disponibilidad, precio y condiciones | Evitar retrasos en la planeación del evento | Alta | BR-04, FR-04 |
| **US-05** | Coordinador | Validar que el número de invitados esté entre 20 y 300 | Identificar cuándo un evento requiere evaluación especial de capacidad | Alta | BR-05, FR-05 |
| **US-06** | Cliente | Poder hacer hasta 2 solicitudes de cambio sin costo adicional | Ajustar detalles menores de mi evento sin afectar mi presupuesto | Media | BR-06, FR-06 |
| **US-07** | Coordinador | Convertir una propuesta en contrato solo cuando el cliente cumpla todas las condiciones requeridas | Asegurar que el compromiso quede formalizado correctamente | Alta | BR-07, FR-07 |
| **US-08** | Coordinador | Que cualquier cambio que modifique el costo total genere una actualización de la cotización y monto contractual | Que el cliente autorice el nuevo monto antes de aplicarlo | Alta | BR-08, FR-08 |
| **US-09** | Administrador | Que el sistema controle que el saldo se liquide a más tardar 3 días naturales antes del evento | Suspender la coordinación o cancelar aplicando penalizaciones si no se cumple | Alta | BR-09, FR-09 |
| **US-10** | Coordinador | Registrar una cancelación de proveedor y buscar un sustituto equivalente | Evitar que el evento se vea afectado | Alta | BR-10, BR-17, FR-10 |
| **US-11** | Coordinador | Recalcular el costo cuando el número de invitados aumenta después de confirmado | Que el cliente autorice y pague el incremento antes de agregar los servicios | Alta | BR-11, FR-11 |
| **US-12** | Coordinador | Validar la viabilidad de un cambio solicitado después de la fecha límite | Confirmarlo únicamente si los proveedores afectados lo permiten | Media | BR-12, BR-08, FR-12 |
| **US-13** | Coordinador | Que el sistema me alerte cuando un proveedor confirmado cambia precio, disponibilidad o características del servicio | Buscar una alternativa cuando el impacto lo requiera | Media | BR-13, BR-17, FR-13 |
| **US-14** | Cliente | Poder notificar la cancelación de mi evento con al menos 7 días naturales de anticipación | Que se defina la devolución o retención del anticipo según el contrato | Alta | BR-14, FR-14 |
| **US-15** | Coordinador | Que el sistema valide que no se asignen más de 15 proveedores simultáneos a un mismo evento | Mantener un control operativo adecuado | Media | BR-15, FR-15 |
| **US-16** | Administrador | Ser el único rol que puede autorizar una excepción de pago | Mantener el control financiero del proceso | Alta | BR-16, FR-16 |
| **US-17** | Coordinador | Consultar el historial completo de cambios solicitados en un evento | Dar seguimiento y justificar decisiones ante el cliente o administración | Media | FR-17, NFR-01 |
| **US-18** | Administrador | Generar reportes de eventos confirmados/pendientes por mes, saldos pendientes por cliente, proveedores con más cancelaciones o retrasos, y el porcentaje de eventos con cambios fuera de plazo | Dar seguimiento operativo al negocio | Media | FR-18, BN-13 |

---

## Detalle de Historias y Criterios de Aceptación

### US-01 — Solicitar cotización con anticipación mínima
* **Importancia:** Alta
* **Historia:** Como cliente, quiero solicitar la cotización de mi evento con al menos 15 días naturales de anticipación, para garantizar disponibilidad de fecha y proveedores.
```gherkin
Escenario: Solicitud dentro del plazo mínimo
  Dado que un cliente desea cotizar un evento
  Cuando solicita la cotización con 15 o más días naturales de anticipación
  Entonces el sistema registra la solicitud y permite continuar el proceso

Escenario: Solicitud fuera del plazo mínimo
  Dado que un cliente desea cotizar un evento
  Cuando solicita la cotización con menos de 15 días naturales de anticipación
  Entonces el sistema registra la solicitud y alerta que la disponibilidad de proveedores no está garantizada
```

### US-02 — Solicitar cambios antes de la fecha límite
* **Importancia:** Alta
* **Historia:** Como cliente, quiero poder modificar mi evento hasta 7 días naturales antes de la fecha, para ajustar detalles sin poner en riesgo la ejecución.
```gherkin
Escenario: Cambio dentro del plazo permitido
  Dado que faltan 7 o más días naturales para el evento
  Cuando el cliente solicita un cambio
  Entonces el coordinador procesa la solicitud normalmente

Escenario: Cambio fuera del plazo permitido
  Dado que faltan menos de 7 días naturales para el evento
  Cuando el cliente solicita un cambio
  Entonces el sistema marca la solicitud como "sujeta a viabilidad operativa y de proveedores"
```

### US-03 — Confirmar número final de invitados
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero que el número definitivo de invitados quede confirmado 7 días naturales antes del evento, para ajustar alimentos, mobiliario y servicios contratados por cantidad.
```gherkin
Escenario: Recordatorio automático a fecha límite
  Dado que faltan 7 días naturales para el evento
  Cuando el cliente aún no ha registrado la confirmación definitiva de invitados
  Entonces el sistema genera automáticamente una notificación de recordatorio al cliente y al coordinador

Escenario: Confirmación registrada
  Dado que el cliente confirma el número final de invitados
  Cuando el coordinador registra dicho número
  Entonces el sistema actualiza los servicios asociados a la cantidad de invitados
```

### US-04 — Dar seguimiento a la confirmación de proveedores
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero que cada proveedor tenga un límite de 48 horas para confirmar disponibilidad, precio y condiciones, para evitar retrasos en la planeación del evento.
```gherkin
Escenario: Proveedor confirma a tiempo
  Dado que se envió una solicitud a un proveedor
  Cuando el proveedor responde dentro de las 48 horas
  Entonces el sistema registra su confirmación con precio y condiciones

Escenario: Proveedor no responde a tiempo
  Dado que se envió una solicitud a un proveedor
  Cuando pasan más de 48 horas sin respuesta
  Entonces el sistema marca al proveedor como "sin confirmar" y notifica al coordinador
```

### US-05 — Gestionar el rango de invitados permitido
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero validar que el número de invitados esté entre 20 y 300, para identificar cuándo un evento requiere evaluación especial de capacidad.
```gherkin
Escenario: Evento dentro del rango estándar
  Dado que un evento tiene entre 20 y 300 invitados
  Cuando se registra la solicitud
  Entonces el sistema la procesa con el flujo normal

Escenario: Evento que excede el rango estándar
  Dado que un evento tiene más de 300 invitados
  Cuando se registra la solicitud
  Entonces el sistema la marca para evaluación especial de capacidad y proveedores
```

### US-06 — Solicitar cambios sin costo adicional
* **Importancia:** Media
* **Historia:** Como cliente, quiero poder hacer hasta 2 solicitudes de cambio sin costo adicional, para ajustar detalles menores de mi evento sin afectar mi presupuesto.
```gherkin
Escenario: Cambio dentro del límite gratuito
  Dado que el cliente ha solicitado menos de 2 cambios sin costo
  Cuando solicita un nuevo cambio que no modifica servicios contratados ni genera costos a Nova
  Entonces el sistema lo aplica sin costo adicional

Escenario: Cambio que excede el límite gratuito
  Dado que el cliente ya ha consumido sus 2 solicitudes de cambio sin costo
  Cuando solicita un cambio adicional
  Entonces el sistema calcula y presenta el costo administrativo adicional antes de proceder con la solicitud

Escenario: Cambio dentro del límite numérico que altera servicios contratados
  Dado que el cliente ha realizado menos de 2 cambios sin costo
  Cuando solicita una modificación que altera servicios contratados o genera costos directos con proveedores
  Entonces el sistema determina que no aplica la gratuidad, genera la cotización complementaria y solicita la autorización del cliente
```

### US-07 — Formalizar el contrato
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero convertir una propuesta en contrato solo cuando el cliente cumpla todas las condiciones requeridas, para asegurar que el compromiso quede formalizado correctamente.
```gherkin
Escenario: Condiciones completas
  Dado que el cliente aceptó la propuesta, proporcionó la información del evento, confirmó los servicios y pagó el anticipo
  Cuando el coordinador revisa la solicitud
  Entonces el sistema permite formalizar el contrato

Escenario: Condiciones incompletas
  Dado que falta alguna condición (aceptación, información, confirmación de servicios o anticipo)
  Cuando el coordinador intenta formalizar el contrato
  Entonces el sistema lo bloquea y señala el requisito faltante
```

### US-08 — Actualizar la cotización ante cambios de costo
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero que cualquier cambio que modifique el costo total genere una actualización de la cotización y del monto contractual, para que el cliente autorice el nuevo monto antes de aplicarlo.
```gherkin
Escenario: Cambio con impacto en costo
  Dado que un cambio solicitado incrementa o reduce el costo total
  Cuando el coordinador lo registra
  Entonces el sistema genera una nueva cotización y actualiza el monto contractual pendiente de aceptación formal del cliente

Escenario: Cliente no acepta el nuevo costo
  Dado que se generó una nueva cotización por cambio de costo
  Cuando el cliente no la acepta
  Entonces el cambio permanece como "no autorizado" y no se aplica
```

### US-09 — Dar seguimiento al pago del saldo pendiente
* **Importancia:** Alta
* **Historia:** Como administrador, quiero que el sistema controle que el saldo se liquide a más tardar 3 días naturales antes del evento, para suspender la coordinación o cancelar aplicando penalizaciones si no se cumple.
```gherkin
Escenario: Pago dentro del plazo
  Dado que faltan 3 o más días naturales para el evento
  Cuando el cliente liquida el saldo pendiente
  Entonces el sistema marca el evento como "pagado" y continúa la coordinación normal

Escenario: Saldo pendiente fuera del plazo contractual
  Dado que faltan menos de 3 días naturales para la fecha del evento
  Cuando el saldo continúa en estatus pendiente
  Entonces el sistema emite una alerta crítica a administración para suspender la coordinación y habilitar la opción de cancelación del evento aplicando penalizaciones contractuales
```

### US-10 — Sustituir proveedor cancelado
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero registrar una cancelación de proveedor y buscar un sustituto equivalente, para evitar que el evento se vea afectado.
```gherkin
Escenario: Sustituto sin diferencia de precio
  Dado que un proveedor confirmado cancela su servicio
  Cuando el coordinador asigna un proveedor sustituto con el mismo precio
  Entonces el sistema actualiza la asignación sin generar cambios en la cotización

Escenario: Sustituto con diferencia de precio
  Dado que un proveedor confirmado cancela su servicio
  Cuando el sustituto disponible tiene un precio distinto
  Entonces el sistema notifica al coordinador para evaluar si Nova absorbe la diferencia o se presenta una alternativa al cliente

Escenario: Intento de sustitución por rol no autorizado
  Dado que un proveedor confirmado ha cancelado su participación
  Cuando un usuario que no cuenta con el rol de Coordinador intenta registrar la sustitución o reasignación
  Entonces el sistema bloquea la operación e informa que dicha acción es facultad exclusiva de Coordinación
```

### US-11 — Procesar aumento de invitados ya confirmados
* **Importancia:** Alta
* **Historia:** Como coordinador, quiero recalcular el costo cuando el número de invitados aumenta después de confirmado, para que el cliente autorice y pague el incremento antes de agregar los servicios.
```gherkin
Escenario: Proveedores con disponibilidad
  Dado que el número de invitados confirmados aumenta
  Cuando los proveedores tienen capacidad disponible
  Entonces el sistema genera una cotización de incremento pendiente de aceptación y pago del cliente

Escenario: Proveedores sin disponibilidad
  Dado que el número de invitados confirmados aumenta
  Cuando los proveedores no tienen capacidad disponible
  Entonces el sistema notifica al coordinador que el incremento no puede procesarse en las condiciones actuales
```

### US-12 — Evaluar cambios solicitados fuera de plazo
* **Importancia:** Media
* **Historia:** Como coordinador, quiero validar la viabilidad de un cambio solicitado después de la fecha límite, para confirmarlo únicamente si los proveedores afectados lo permiten.
```gherkin
Escenario: Cambio viable fuera de plazo sujeto a aceptación
  Dado que el cliente solicita un cambio después de la fecha límite de 7 días naturales
  Cuando los proveedores afectados confirman viabilidad operativa
  Entonces el sistema calcula el costo adicional generado y lo envía como propuesta condicionada a la aceptación y confirmación del cliente antes de procesarlo

Escenario: Cambio no viable fuera de plazo
  Dado que el cliente solicita un cambio después de la fecha límite
  Cuando los proveedores afectados no confirman disponibilidad
  Entonces el sistema marca el cambio como "no garantizado" y lo rechaza
```

### US-13 — Gestionar cambios de condiciones de un proveedor
* **Importancia:** Media
* **Historia:** Como coordinador, quiero que el sistema me alerte cuando un proveedor confirmado cambia precio, disponibilidad o características del servicio, para buscar una alternativa cuando el impacto lo requiera.
```gherkin
Escenario: Proveedor sin disponibilidad en la fecha solicitada
  Dado que un proveedor no tiene disponibilidad para la fecha del evento
  Cuando el coordinador lo detecta
  Entonces el sistema sugiere buscar otro proveedor que cumpla los requisitos

Escenario: Proveedor modifica condiciones tras confirmar
  Dado que un proveedor ya confirmado cambia precio, disponibilidad o características
  Cuando el coordinador registra el cambio
  Entonces el sistema evalúa el impacto y, si es significativo, solicita evaluar una alternativa

Escenario: Reasignación por cambio de condiciones restringida por rol
  Dado que un proveedor modificó sus condiciones de servicio de forma sustancial
  Cuando un usuario con rol distinto a Coordinador intenta reasignar al proveedor por una alternativa
  Entonces el sistema deniega el acceso y registra el intento de acción no autorizada
```

### US-14 — Notificar cancelación de evento
* **Importancia:** Alta
* **Historia:** Como cliente, quiero poder notificar la cancelación de mi evento con al menos 7 días naturales de anticipación, para que se defina la devolución o retención del anticipo según el contrato.
```gherkin
Escenario: Cancelación dentro del plazo mínimo
  Dado que faltan 7 o más días naturales para la fecha del evento
  Cuando el cliente notifica la cancelación formal
  Entonces el sistema calcula la retención o reembolso del anticipo aplicando las cláusulas del contrato y deduciendo los gastos que Nova ya haya comprometido con proveedores

Escenario: Cancelación fuera del plazo mínimo
  Dado que faltan menos de 7 días naturales para el evento
  Cuando el cliente notifica la cancelación
  Entonces el sistema considera los gastos ya comprometidos con proveedores al calcular la devolución
```

### US-15 — Controlar el máximo de proveedores por evento
* **Importancia:** Media
* **Historia:** Como coordinador, quiero que el sistema valide que no se asignen más de 15 proveedores simultáneos a un mismo evento, para mantener un control operativo adecuado.
```gherkin
Escenario: Asignación dentro del límite
  Dado que un evento tiene menos de 15 proveedores asignados
  Cuando el coordinador asigna un proveedor adicional
  Entonces el sistema lo registra sin restricción

Escenario: Asignación que excede el límite
  Dado que un evento ya tiene 15 proveedores asignados
  Cuando el coordinador intenta asignar uno más
  Entonces el sistema bloquea la asignación y solicita revisión especial
```

### US-16 — Autorizar excepciones de pago
* **Importancia:** Alta
* **Historia:** Como administrador, quiero ser el único rol que puede autorizar una excepción de pago, para mantener el control financiero del proceso.
```gherkin
Escenario: Solicitud de excepción por administración
  Dado que existe una situación de pago que requiere excepción
  Cuando un usuario con rol de administración la autoriza
  Entonces el sistema aplica la excepción y registra quién la autorizó

Escenario: Intento de excepción por otro rol
  Dado que existe una situación de pago que requiere excepción
  Cuando un usuario que no es administración intenta autorizarla
  Entonces el sistema rechaza la acción
```

### US-17 — Consultar historial de cambios de un evento
* **Importancia:** Media
* **Historia:** Como coordinador, quiero consultar el historial completo de cambios solicitados en un evento, para dar seguimiento y justificar decisiones ante el cliente o administración.
```gherkin
Escenario: Historial disponible
  Dado que un evento ha tenido una o más solicitudes de cambio
  Cuando el coordinador consulta el historial
  Entonces el sistema muestra fecha, tipo de cambio, estatus y costo asociado de cada solicitud
```

### US-18 — Generar reportes e indicadores de seguimiento
* **Importancia:** Media
* **Historia:** Como administrador, quiero generar reportes de eventos confirmados/pendientes por mes, saldos pendientes por cliente, proveedores con más cancelaciones o retrasos, y el porcentaje de eventos con cambios fuera de plazo, para dar seguimiento operativo al negocio.
```gherkin
Escenario: Reporte mensual de estatus de eventos
  Dado que existen eventos registrados en el sistema
  Cuando el administrador solicita el consolidado mensual
  Entonces el sistema genera el reporte agrupando el volumen de eventos confirmados frente a eventos pendientes por mes

Escenario: Reporte de saldos pendientes por cliente
  Dado que existen contratos vigentes con pagos en proceso
  Cuando el administrador consulta los estados de cuenta
  Entonces el sistema genera un listado de cuentas por cobrar desglosando los saldos pendientes por cliente y fecha de vencimiento

Escenario: Indicador de desempeño y retrasos de proveedores
  Dado que existen proveedores asignados a eventos
  Cuando el administrador genera el análisis de proveedores
  Entonces el sistema calcula y muestra la tasa de cancelaciones y el índice de demoras en responder dentro del SLA de 48 horas por cada proveedor

Escenario: Indicador de eventos con cambios fuera de plazo
  Dado que existen solicitudes de cambio registradas
  Cuando el administrador consulta el indicador
  Entonces el sistema calcula el porcentaje de eventos con cambios solicitados fuera del plazo establecido
```
