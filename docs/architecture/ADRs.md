# Architecture Decision Records (ADRs) — Eventos Nova

**Equipo 16 · FIME UANL · Componentes de Lógica de Negocios**  
**Documento PDF original:** [`ADR_EventosNova_Equipo16.pdf`](ADR_EventosNova_Equipo16.pdf)

---

## Registro de Decisiones

| ID | Título | Estado | Trazabilidad Principal |
| :--- | :--- | :--- | :--- |
| **ADR-001** | Patrón de lógica de negocio: Domain Model | Aceptada | BR-04, BR-02, BR-07, BR-12, BR-14 |
| **ADR-002** | Mecanismo de Control de Acceso (RBAC) | Aceptada | BR-16, BR-17, US-16, US-10 |
| **ADR-003** | Estrategia de Auditoría e Historial Inmutable | Aceptada | FR-17, NFR-01, BN-02, BN-12, BR-08 |
| **ADR-004** | Despacho de eventos de dominio en memoria tras confirmar transacción | Aceptada (PIA) | CU-03, CU-04, CU-05, FR-17 |

---

## ADR-001: Patrón de lógica de negocio: Domain Model

* **Estado:** Aceptada (12 de octubre de 2026)
* **Decisores:** Equipo 16 Completo
* **Relacionada con:** ADR-002

### Contexto
Eventos Nova requiere orquestar reglas complejas y dependientes del tiempo, como la validación del SLA de 48 horas (`BR-04`), el límite de 7 días para cambios (`BR-02`), y la verificación de las 4 condiciones para formalizar contratos (`BR-07`). En el levantamiento (Unidad 2) se identificaron reglas interconectadas, como retenciones de anticipos y gastos comprometidos al cancelar (`BR-14`).

### Alternativas Consideradas
| Opción | Ventajas | Desventajas | Resultado |
| :--- | :--- | :--- | :--- |
| **Transaction Script** | Muy simple; rápido de entregar; fácil de entender al inicio. | Las reglas se duplican en endpoints; difícil de probar con reglas interconectadas. | Descartada |
| **Table Module** | Encaja con datos tabulares. | Poca expresividad para modelar montos o estados inmateriales (`MontoContractual`, `GastosComprometidos`). | Descartada |
| **Domain Model** | Reglas encapsuladas en entidades, especificaciones y máquinas de estado; un solo lugar para aplicar políticas financieras y operativas. | Mayor número de clases que mantener. | **Elegida** |

### Decisión
Se adopta **Domain Model** enriquecido con los patrones **Specification** y **State Machine**. Las entidades raíz (`Evento` y `CuentaDePagos`) encapsulan las reglas, validando los estados e invariantes antes de la persistencia.

### Consecuencias
* **Beneficios:** Código altamente cohesivo y testeable en aislamiento (cumpliendo SOLID).
* **Costos:** Requiere mayor abstracción para definir Aggregates, Specifications y Value Objects.
* **Riesgos:** Modelo anémico si la lógica termina escapándose a los servicios de aplicación (mitigado delegando toda validación al dominio).

---

## ADR-002: Mecanismo de Control de Acceso (RBAC)

* **Estado:** Aceptada (12 de octubre de 2026)
* **Decisores:** Equipo 16 Completo
* **Relacionada con:** ADR-001

### Contexto
El negocio exige exclusividad de funciones: solo Coordinación puede cancelar o reasignar proveedores (`BR-17`) y solo Administración puede autorizar excepciones de pago (`BR-16`). Validar esto mezclando sesiones de red dentro de las entidades de dominio acoplaría la lógica comercial con infraestructura de autenticación.

### Alternativas Consideradas
| Opción | Ventajas | Desventajas | Resultado |
| :--- | :--- | :--- | :--- |
| **Validación acoplada a sesión en Dominio** | Asegura que el modelo rechace la sesión HTTP directamente. | Ensucia el modelo de negocio con lógica de red/sesión HTTP. | Descartada |
| **Validación en Capa de Entrada / Service Layer y propagación de identidad auditable** | Mantiene el Dominio agnóstico de HTTP y propaga `usuario_id` como metadato para auditoría (`FR-17`). Respeta SRP. | Requiere asegurar la validación en los puntos de entrada. | **Elegida** |

### Decisión
El control de acceso de roles (`Cliente`, `Coordinador`, `Administración`, `Proveedor`) se gestiona en la capa de entrada/aplicación, mientras que el `usuario_id` viaja como parámetro explícito en los comandos para su registro en la bitácora de auditoría (`ADR-003`).

### Consecuencias
* **Beneficios:** Respeta el principio de Responsabilidad Única (SRP) y mantiene el dominio puro libre de dependencias web.
* **Trazabilidad:** `BR-16`, `BR-17`, `US-16`, `US-10`.

---

## ADR-003: Estrategia de Auditoría e Historial Inmutable

* **Estado:** Aceptada (12 de octubre de 2026)
* **Decisores:** Equipo 16 Completo

### Contexto
Se necesita una "fuente única de la verdad" para registrar la fecha, usuario, acción/tipo de cambio y detalle asociado (`FR-17`, `NFR-01`), evitando cotizaciones desfasadas y problemas de comunicación por WhatsApp (`BN-02`, `BN-12`).

### Alternativas Consideradas
| Opción | Ventajas | Desventajas | Resultado |
| :--- | :--- | :--- | :--- |
| **Event Sourcing Puro** | Historial perfecto al reconstruir estados desde eventos. | Sobreingeniería excesiva para el alcance del sistema. | Descartada |
| **Tabla Relacional Append-Only (`LogAuditoria`)** | No se sobrescriben ni eliminan datos. Cumple la auditoría de forma relacional e inmutable. | Costo de almacenamiento moderadamente mayor que un CRUD plano. | **Elegida** |

### Decisión
El historial de cambios y acciones críticas opera sobre una tabla relacional dedicada y estructurada (*Append-only*: `logs_auditoria`). El repositorio `ILogAuditoriaRepository` expone únicamente el método `registrar(log: LogAuditoria)` y carece de operaciones `UPDATE` o `DELETE`.

### Consecuencias
* **Beneficios:** Trazabilidad íntegra para auditorías y consultas del coordinador (`GET /eventos/{id}/auditoria`), cumpliendo `FR-17` y `NFR-01`.
* **Costos:** Crecimiento lineal de filas en la tabla `logs_auditoria`.

---

## ADR-004: Gestión Transaccional (`IUnitOfWork`) y Despacho de Eventos de Dominio en Memoria

* **Estado:** Aceptada
* **Decisores:** Equipo 16 Completo
* **Relacionada con:** ADR-001 y ADR-003

### Contexto
Los agregados `Evento` y `CuentaDePagos` registran eventos de dominio (`ContratoFormalizadoEvent`, `AlcanceModificadoEvent`, `PagoRegistradoEvent`, `ProveedorVencidoSLAEvent`) durante sus transiciones de estado. Es necesario coordinar la persistencia atómica y la publicación de dichos eventos sin acoplar el dominio a un broker externo.

### Alternativas Consideradas
* **A. Despacho en memoria tras confirmar `commit()` en `UnitOfWork`:** Simple, reproducible en pruebas automatizadas y sin infraestructura externa adicional.
* **B. Broker de mensajería externo (RabbitMQ/Kafka):** Excede el alcance operativo del proyecto.

### Decisión
`SqlAlchemyUnitOfWork` coordina la sesión transaccional y recolecta los eventos de dominio emitidos, despachándolos en memoria únicamente después de que `session.commit()` se ejecuta con éxito. Ante cualquier excepción, ejecuta `session.rollback()` garantizando atomicidad ACID.
