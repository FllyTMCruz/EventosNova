# Glosario de Dominio (Lenguaje Ubicuo) — Caso Eventos Nova

**Universidad Autónoma de Nuevo León (UANL) · FIME**  
**Unidad 2, Unidad 3 y PIA · Equipo 16**  
**Documento PDF original:** [`Glosario_Dominio_Eventos_Nova.pdf`](Glosario_Dominio_Eventos_Nova.pdf)

---

## 1. Glosario de Dominio del Negocio (35 términos en 6 familias)

### Familia 1: Roles y Entidades (6 términos)
| Término | Categoría | Definición | Rol relacionado |
| :--- | :--- | :--- | :--- |
| **Cliente** | Rol / Aggregate Root | Persona que solicita y contrata un evento con Eventos Nova. Es responsable de proporcionar la información necesaria para organizar el evento y de confirmar los datos acordados para su realización. | Cliente |
| **Coordinador** | Rol | Colaborador de Eventos Nova encargado de organizar y dar seguimiento a los eventos, preparando la propuesta con la información proporcionada por el Cliente y coordinando a los proveedores necesarios para su realización. | Coordinador |
| **Proveedor** | Rol / Aggregate Root | Empresa o persona externa contratada por Eventos Nova para prestar un servicio específico durante un evento, como alimentos, mobiliario, música, decoración o fotografía. | Proveedor |
| **Administración** | Rol | Área de Eventos Nova encargada de supervisar y gestionar los aspectos administrativos de los eventos, incluyendo el seguimiento de pagos, costos y situaciones que requieran autorización. | Administración |
| **Evento** | Entidad (`Aggregate Root`) | Compromiso de organización que Eventos Nova coordina para un Cliente, desde la solicitud hasta su realización y cierre administrativo. Contiene la fecha, el tipo, el número de invitados, los servicios contratados, los proveedores asignados y el estado de los pagos. | Proceso de Eventos Nova |
| **Proveedor sustituto equivalente** | Rol / Entidad | Proveedor alternativo del catálogo de Nova que cuenta con condiciones de calidad, servicio y costo similares al original, asignado exclusivamente por el Coordinador tras una cancelación imprevista (`BR-10`, `BR-17`). | Coordinador / Proveedor |

### Familia 2: Documentos y Artefactos (6 términos)
| Término | Categoría | Definición | Rol relacionado |
| :--- | :--- | :--- | :--- |
| **Solicitud de cotización** | Documento / Artefacto | Petición que el Cliente presenta a Eventos Nova para obtener una cotización de un evento, indicando la fecha, el tipo de evento y el número estimado de invitados. | Cliente |
| **Propuesta** | Documento / Artefacto | Documento que el Coordinador elabora a partir de la solicitud de cotización, donde se presentan los servicios, costos y condiciones planteadas para el evento. | Coordinador |
| **Cotización** | Documento / Artefacto | Documento que registra el costo de los servicios incluidos en un evento, elaborado a partir de la propuesta. | Coordinador |
| **Cotización de incremento** | Documento / Entidad Interna | Propuesta de ajuste económico emitida cuando el número de invitados confirmados aumenta o cambia el alcance, la cual requiere aceptación formal y pago por parte del cliente antes de incorporar los nuevos servicios. | Coordinador / Cliente |
| **Contrato de evento** | Documento / Artefacto | Documento que formaliza el acuerdo entre el Cliente y Eventos Nova para la realización de un evento cuando se cumplen las 4 condiciones de `BR-07`. | Coordinador |
| **Historial de cambios (`LogAuditoria`)** | Documento / Entidad Append-Only | Registro inmutable de las solicitudes de cambio realizadas sobre un evento, incluyendo fecha, usuario, rol, tipo de cambio, estado y costo asociado (`FR-17`, `ADR-003`). | Coordinador |

### Familia 3: Transacciones y Montos (7 términos)
| Término | Categoría | Definición | Rol relacionado |
| :--- | :--- | :--- | :--- |
| **Monto contractual** | Transacción / Value Object | Importe económico total pactado y formalizado en el contrato del evento. Se actualiza formalmente ante cambios de alcance, costo o número de asistentes autorizados por el cliente. | Coordinador / Administración |
| **Anticipo** | Transacción | Pago inicial que el Cliente realiza a Eventos Nova para cubrir parte del costo del evento y avanzar con su organización. | Cliente / Administración |
| **Saldo pendiente** | Transacción | Monto restante del costo total del evento que el Cliente debe pagar a Eventos Nova después de realizar el anticipo: $(\text{Subtotal} + \text{Incrementos Aprobados}) - (\text{Anticipo} + \text{Pagos Realizados})$. | Cliente / Administración |
| **Gastos comprometidos** | Transacción / Value Object | Erogaciones, pagos no reembolsables o compromisos comerciales legalmente adquiridos por Nova con proveedores externos para el evento, los cuales se deducen del anticipo ante una cancelación (`BR-14`). | Administración / Coordinador |
| **Cambio solicitado** | Transacción | Modificación que el Cliente solicita sobre un evento ya cotizado o contratado, como un cambio de horario, menú o servicio. | Cliente / Coordinador |
| **Sustitución de proveedor** | Transacción | Proceso mediante el cual el Coordinador reemplaza a un Proveedor confirmado por otro que pueda prestar el mismo servicio para un evento (`BR-10`, `BR-17`). | Coordinador |
| **Cancelación de evento** | Transacción | Acción mediante la cual el Cliente solicita que un evento previamente acordado ya no se lleve a cabo (`BR-14`). | Cliente |

### Familia 4: Reglas, Políticas y Procesos (3 términos)
| Término | Categoría | Definición | Rol relacionado |
| :--- | :--- | :--- | :--- |
| **Excepción de pago** | Regla / Política | Autorización especial exclusiva de Administración que permite modificar las condiciones normales de pago establecidas para un evento (`BR-16`). | Administración |
| **Penalización** | Regla / Política | Deducción o sanción económica estipulada en el contrato que Nova puede aplicar ante la falta de liquidación del saldo a menos de 3 días del evento o ante cancelaciones extemporáneas (`BR-09`, `BR-14`). | Administración |
| **Cierre administrativo** | Proceso / Hito | Finiquito formal y conclusión del contrato de un evento, que se ejecuta una vez que el servicio ha sido realizado en su totalidad y el saldo pendiente ha sido liquidado al 100%. | Coordinador / Administración |

### Familia 5: Parámetros y Datos Operativos (6 términos)
| Término | Categoría | Definición | Rol relacionado |
| :--- | :--- | :--- | :--- |
| **Límite de cambios sin costo** | Parámetro operativo | Cantidad máxima de cambios (2) que el Cliente puede solicitar para un evento sin generar un costo adicional (`BR-06`). | Proceso de Eventos Nova |
| **Fecha límite de cambios** | Parámetro operativo | Fecha establecida como límite (7 días naturales antes del evento) para que el Cliente pueda solicitar cambios bajo condiciones normales (`BR-02`). | Proceso de Eventos Nova |
| **Fecha límite de cancelación** | Parámetro operativo | Plazo límite fijado con un mínimo de 7 días naturales de anticipación al evento para que el cliente notifique formalmente una cancelación ordinaria (`BR-14`). | Cliente / Administración |
| **Confirmación final de invitados** | Dato operativo / Value Object | Número definitivo de asistentes que el cliente confirma formalmente a más tardar 7 días naturales antes del evento (`BR-03`). | Cliente / Coordinador |
| **SLA de confirmación de proveedor** | Parámetro operativo / Value Object | Plazo estricto de 48 horas para que un Proveedor confirme su disponibilidad, precio y condiciones del servicio solicitado (`BR-04`). | Proveedor |
| **Límite de proveedores por evento** | Parámetro operativo | Número máximo de proveedores (15) que pueden asignarse simultáneamente a un mismo evento (`BR-15`). | Coordinador |

### Familia 6: Estados del Sistema (7 términos)
| Término | Categoría | Definición | Rol relacionado |
| :--- | :--- | :--- | :--- |
| **Proveedor confirmado** | Estado | Estado de un Proveedor que ha aceptado prestar el servicio solicitado y ha confirmado su disponibilidad, precio y condiciones dentro de las 48h. | Coordinador |
| **Sin confirmar** | Estado | Estado de un Proveedor que aún no ha confirmado su disponibilidad, precio y condiciones o cuyo SLA de 48 horas venció. | Coordinador |
| **Sujeta a viabilidad operativa y de proveedores** | Estado | Estado de un cambio solicitado por el Cliente fuera del plazo de 7 días que requiere verificar si puede realizarse (`BR-02`, `BR-12`). | Coordinador |
| **Evaluación especial de capacidad** | Estado | Estado de un evento con más de 300 invitados que requiere revisión adicional para determinar si Eventos Nova cuenta con la capacidad y proveedores necesarios (`BR-05`). | Coordinador |
| **Pagado** | Estado | Estado de cuenta del evento que certifica que el saldo pendiente ha sido cubierto y liquidado en su totalidad dentro del plazo contractual (`BR-09`). | Administración |
| **No autorizado** | Estado | Estado asignado a una solicitud de cambio o modificación de alcance cuyo costo asociado fue declinado o no ha sido aceptado formalmente por el cliente (`BR-08`). | Cliente / Coordinador |
| **No garantizado** | Estado | Estado asignado a una solicitud de cambio extemporánea (a menos de 7 días del evento) cuando los proveedores involucrados no cuentan con viabilidad operativa para atenderla (`BR-12`). | Coordinador |

---

## 2. Glosario Arquitectónico DDD (Unidad 3)

| Término Técnico | Clasificación DDD | Definición en el Código (`src/domain/`) |
| :--- | :--- | :--- |
| **`Evento`** | Aggregate Root (Operativo) | Raíz de agregado operativa (`src/domain/models/evento.py`). Orquesta el estado del evento (`EstadoEventoStateMachine`), las asignaciones de proveedores (`1..15`), las cotizaciones de incremento y emite eventos de dominio. |
| **`CuentaDePagos`** | Aggregate Root (Financiero) | Raíz de agregado financiera (`src/domain/models/cuenta_pagos.py`). Administra de forma aislada el `MontoContractual`, el registro de pagos/abonos, y el cálculo de devolución ante cancelación deduciendo gastos comprometidos (`BR-14`). |
| **`AsignacionProveedor`** | Entidad Interna | Entidad encapsulada dentro de `Evento`. Rastrea el estado del proveedor (`AsignacionProveedorStateMachine`) y evalúa el vencimiento de su SLA de 48 horas (`BR-04`). |
| **`CotizacionIncremento`** | Entidad Interna | Entidad encapsulada dentro de `Evento`. Representa ajustes de alcance o aforo y el costo adicional asociado (`BR-08`, `BR-11`, `BR-12`). |
| **`LogAuditoria`** | Entidad Append-Only | Registro transaccional inmutable (`src/domain/models/auditoria.py`) alimentado en cada mutación de estado para garantizar trazabilidad (`FR-17`, `ADR-003`). |
| **`MontoContractual`** | Value Object | Objeto de valor inmutable (`src/domain/value_objects/monto_contractual.py`) que encapsula subtotal, anticipo pactado, incrementos autorizados y pagos recibidos, calculando el saldo pendiente. |
| **`Dinero`** | Value Object | Objeto de valor inmutable (`src/domain/value_objects/dinero.py`) con precisión decimal financiera y validación de moneda. |
| **`RangoFechas`** | Value Object | Objeto de valor inmutable (`src/domain/value_objects/rango_fechas.py`) que calcula días naturales de anticipación (`BR-01`, `BR-02`, `BR-09`, `BR-14`) y horas transcurridas para SLA (`BR-04`). |
