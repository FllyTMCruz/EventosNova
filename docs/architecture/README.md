# Arquitectura del Sistema — Eventos Nova (Equipo 16)

**Universidad Autónoma de Nuevo León (UANL) · Facultad de Ingeniería Mecánica y Eléctrica (FIME)**  
**Materia:** Componentes de Lógica de Negocios — Unidad 3 y PIA

---

## 1. Índice de Documentos y Artefactos de Arquitectura

Esta carpeta (`docs/architecture/`) reúne toda la documentación arquitectónica formal del proyecto, tanto en formato Markdown navegable como en sus entregables PDF oficiales y código fuente PlantUML:

### Documentos en Markdown
* [`ADRs.md`](ADRs.md) — Registro de Decisiones de Arquitectura (`ADR-001` a `ADR-004`).
* [`Matriz_Trazabilidad.md`](Matriz_Trazabilidad.md) — Matriz de trazabilidad integral (Análisis U2 $\rightarrow$ Arquitectura U3 $\rightarrow$ Código DDD $\rightarrow$ Pruebas Automatizadas).

### Entregables Oficiales en PDF
* [`01_Informe_Arquitectura_Equipo16_Final.pdf`](01_Informe_Arquitectura_Equipo16_Final.pdf) — Informe completo de arquitectura del sistema (66 páginas).
* [`Arquitectura_Fase1.pdf`](Arquitectura_Fase1.pdf) — Fase 1: Preparación del caso y elección del patrón *Domain Model*.
* [`Mapa_Dominio_Etapa3.pdf`](Mapa_Dominio_Etapa3.pdf) — Etapa 3: Construcción del Mapa de Dominio, Lenguaje Ubicuo y Fichas de Aggregates.
* [`ADR_EventosNova_Equipo16.pdf`](ADR_EventosNova_Equipo16.pdf) — Documento formal de Architecture Decision Records (`ADR-001`, `ADR-002`, `ADR-003`).
* [`Entregable04_Matriz_Trazabilidad.pdf`](Entregable04_Matriz_Trazabilidad.pdf) — Entregable 04: Matriz de Trazabilidad Arquitectónica.
* [`02_Diagrama_Dominio_Equipo16.pdf`](02_Diagrama_Dominio_Equipo16.pdf) — Diagrama UML del Modelo de Dominio (`Evento` y `CuentaDePagos`).
* [`02_Diagrama_Dominio_Clases_Eq16.pdf`](02_Diagrama_Dominio_Clases_Eq16.pdf) — Diagrama UML de Clases por Capas (*Service Layer*, *Domain Layer*, *Infraestructura*).
* [`05_Bitacora_IA_Equipo16.pdf`](05_Bitacora_IA_Equipo16.pdf) — Entregable 05: Bitácora Oficial de Uso y Auditoría de IA.

### Diagramas UML / DDD (`diagrams/`)
* **Fuentes PlantUML (`.puml`):**
  * [`diagrams/source/modelo-dominio-eventos.puml`](diagrams/source/modelo-dominio-eventos.puml) — Modelo de Dominio y Agregados.
  * [`diagrams/source/Diagrama_Clases_EventosNova.puml`](diagrams/source/Diagrama_Clases_EventosNova.puml) — Diagrama de Clases de las 3 Capas.
  * [`diagrams/source/Secuencia_CU03_Exito.puml`](diagrams/source/Secuencia_CU03_Exito.puml) — Secuencia CU-03: Formalizar Contrato de Evento (Flujo Exitoso).
  * [`diagrams/source/Secuencia_CU04_Alternativa.puml`](diagrams/source/Secuencia_CU04_Alternativa.puml) — Secuencia CU-04: Procesar Cambio de Alcance Extemporáneo.
* **Exportaciones en PDF (`diagrams/exports/`):**
  * [`diagrams/exports/02_Diagrama_Dominio_Equipo16.pdf`](diagrams/exports/02_Diagrama_Dominio_Equipo16.pdf)
  * [`diagrams/exports/Secuencia_CU03_Exito.pdf`](diagrams/exports/Secuencia_CU03_Exito.pdf)
  * [`diagrams/exports/Secuencia_CU04_Alternativa.pdf`](diagrams/exports/Secuencia_CU04_Alternativa.pdf)

---

## 2. Resumen de la Arquitectura y Modelo DDD

El sistema implementa **Clean Architecture** combinada con **Domain-Driven Design (DDD)** táctico y estratégico, separando el núcleo en dos *Aggregate Roots* con fronteras transaccionales independientes:

### 2.1 Agregado Operativo: `Evento` (`src/domain/models/evento.py`)
* **Raíz:** `Evento`
* **Entidades Internas:** `AsignacionProveedor` ($1..15$, `BR-15`), `CotizacionIncremento` ($0..*$, `BR-08`)
* **Value Objects asociados:** `RangoFechas` (`BR-01`, `BR-02`, `BR-04`), `Dinero`
* **Máquinas de Estado:** `EstadoEventoStateMachine` (`BORRADOR` $\rightarrow$ `COTIZADO` $\rightarrow$ `CONFIRMADO` $\rightarrow$ `EN_EJECUCION` $\rightarrow$ `LIQUIDADO` / `CANCELADO`) y `AsignacionProveedorStateMachine` (`PENDIENTE` $\rightarrow$ `CONFIRMADO` / `VENCIDO` / `CANCELADO`)
* **Specifications encapsuladas (`src/domain/specifications/evento_specifications.py`):**
  * `CapacidadInvitadosSpecification` (`BR-05`: rango operativo de 20 a 300 invitados)
  * `LimiteProveedoresSpecification` (`BR-15`: máximo 15 proveedores activos simultáneos)
  * `FormalizacionContratoSpecification` (`BR-07`: las 4 condiciones obligatorias para formalizar)
  * `VentanaCambioAlcanceSpecification` (`BR-02` / `BR-12`: plazo mínimo de 7 días naturales)

### 2.2 Agregado Financiero: `CuentaDePagos` (`src/domain/models/cuenta_pagos.py`)
* **Raíz:** `CuentaDePagos`
* **Value Objects encapsulados:** `MontoContractual` (`subtotal_base`, `anticipo_requerido`, `incrementos_autorizados`, `pagos_recibidos`), `Dinero`
* **Responsabilidades:** Registrar pagos/anticipos sin exceder el total vigente, verificar cobertura del anticipo (`BR-07`) y calcular devoluciones o penalizaciones ante cancelación deduciendo gastos comprometidos (`BR-14`).

### 2.3 Evaluación de Principios SOLID

| Principio | Aplicación Demostrable en Eventos Nova |
| :--- | :--- |
| **S — Single Responsibility (SRP)** | Las entidades de dominio (`Evento`, `CuentaDePagos`) gobiernan exclusivamente reglas de negocio, mientras que la persistencia SQL reside en `src/infrastructure/persistence/` y cada caso de uso tiene su propio Handler en `src/application/use_cases/`. |
| **O — Open/Closed (OCP)** | El patrón `Specification[T]` (`src/domain/specifications/base.py`) permite componer nuevas reglas de negocio mediante operadores booleanos (`&`, `|`, `~`) sin modificar las reglas existentes. |
| **L — Liskov Substitution (LSP)** | Los repositorios concretos de SQLAlchemy (`SqlAlchemyEventoRepository`, `SqlAlchemyCuentaDePagosRepository`, `SqlAlchemyLogAuditoriaRepository`) cumplen íntegramente los contratos abstractos definidos en `src/domain/repositories/interfaces.py`, permitiendo intercambiar PostgreSQL en producción por SQLite en memoria durante las pruebas sin alterar los casos de uso. |
| **I — Interface Segregation (ISP)** | Los contratos de repositorio están segregados por Aggregate Root (`IEventoRepository`, `ICuentaDePagosRepository`) y el repositorio de auditoría (`ILogAuditoriaRepository`) expone únicamente `registrar()` (*append-only*, sin métodos de actualización ni borrado, cumpliendo `ADR-003`). |
| **D — Dependency Inversion (DIP)** | Los handlers de la capa de aplicación (`FormalizarContratoHandler`, `ProcesarCambioAlcanceHandler`, `ConsultarSaldoPendienteHandler`, `EvaluarSLAProveedoresScheduler`) dependen exclusivamente de la abstracción `IUnitOfWork` inyectada en `src/api/dependencies.py`. |
