# Matriz de Trazabilidad Arquitectónica e Implementación — Eventos Nova

**Equipo 16 · FIME UANL · Componentes de Lógica de Negocios**  
**Documento PDF original:** [`Entregable04_Matriz_Trazabilidad.pdf`](Entregable04_Matriz_Trazabilidad.pdf)

---

## 1. Matriz de Trazabilidad de Extremo a Extremo (Análisis $\rightarrow$ Arquitectura $\rightarrow$ Código $\rightarrow$ Pruebas)

Esta matriz establece la trazabilidad directa y verificable entre los artefactos de la **Unidad 2** (Necesidades `BN`, Reglas de Negocio `BR`, Historias de Usuario `US`, Requerimientos `FR`/`NFR`), el diseño de la **Unidad 3** (Casos de Uso `CU`, Componentes DDD y `ADRs`) y la **Implementación del PIA** (`src/` y `tests/`):

| Unidad 2: Reglas / US / Requerimientos | Unidad 3: Caso de Uso | Componente DDD / Patrón en `src/` | Decisión (ADR) | Endpoint API REST (`src/api/`) | Pruebas Automatizadas (`tests/`) | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BR-01** (15 días anticipación)<br>**BR-05** (20 a 300 invitados)<br>**BR-15** (Máx. 15 proveedores)<br>**US-01, US-05, US-15** | **CU-01** Solicitar cotización de evento y asignar proveedores | `Evento` (`src/domain/models/evento.py`)<br>`CapacidadInvitadosSpecification`<br>`LimiteProveedoresSpecification`<br>`RangoFechas` | ADR-001 | `POST /eventos` | `tests/unit/test_specifications.py`<br>`tests/unit/test_domain_models.py`<br>`tests/integration/test_api_endpoints.py` | **Cubierto** |
| **BR-04** (SLA 48h)<br>**BR-10** (Sustituto equivalente)<br>**BR-17** (Exclusividad Coordinación)<br>**US-04, US-10, US-13** | **CU-02** Confirmar respuesta de proveedor / Evaluar SLA | `AsignacionProveedor`<br>`AsignacionProveedorStateMachine`<br>`EvaluarSLAProveedoresScheduler` | ADR-001<br>ADR-002 | `POST /eventos/scheduler/evaluar-sla` | `tests/unit/test_state_machine.py`<br>`tests/unit/test_domain_models.py`<br>`tests/integration/test_use_cases.py` | **Cubierto** |
| **BR-07** (4 condiciones obligatorias para formalizar)<br>**US-07, FR-07, BN-06** | **CU-03** Formalizar contrato de evento | `Evento.formalizar_contrato()`<br>`FormalizacionContratoSpecification`<br>`EstadoEventoStateMachine`<br>`FormalizarContratoHandler` | ADR-001<br>ADR-004 | `POST /eventos/{id}/formalizar` | `tests/unit/test_specifications.py`<br>`tests/integration/test_use_cases.py`<br>`tests/integration/test_api_endpoints.py` | **Cubierto** |
| **BR-02** (7 días límite cambios)<br>**BR-06** (2 gratuitos)<br>**BR-08** (Nueva cotización)<br>**BR-12** (Fuera de plazo)<br>**FR-17 / NFR-01** (Historial auditable)<br>**US-02, US-06, US-08, US-11, US-12, US-17** | **CU-04** Procesar cambio de alcance y consultar auditoría | `Evento.solicitar_cambio_alcance()`<br>`VentanaCambioAlcanceSpecification`<br>`CotizacionIncremento`<br>`ProcesarCambioAlcanceHandler`<br>`LogAuditoria` (Append-Only) | ADR-001<br>ADR-003<br>ADR-004 | `POST /eventos/{id}/cambios-alcance`<br>`GET /eventos/{id}/auditoria` | `tests/unit/test_specifications.py`<br>`tests/integration/test_use_cases.py`<br>`tests/integration/test_api_endpoints.py` | **Cubierto** |
| **BR-09** (Liquidación a tiempo)<br>**BR-14** (Cancelación y retención de gastos comprometidos)<br>**BR-16** (Excepción por Administración)<br>**US-09, US-14, US-16** | **CU-05** Registrar pagos, liquidar saldo y consultar estado financiero | `CuentaDePagos` (`src/domain/models/cuenta_pagos.py`)<br>`MontoContractual` (`src/domain/value_objects/monto_contractual.py`)<br>`ConsultarSaldoPendienteHandler` | ADR-001<br>ADR-002<br>ADR-003 | `POST /eventos/{id}/pagos`<br>`GET /eventos/{id}/saldo` | `tests/unit/test_domain_models.py`<br>`tests/integration/test_use_cases.py`<br>`tests/integration/test_api_endpoints.py` | **Cubierto** |

---

## 2. Dictamen de Cobertura

El equipo certifica que el 100% de las reglas críticas interconectadas definidas en el BRD de la Unidad 2 han sido mapeadas a los 5 casos de uso operativos de la Unidad 3 y materializadas en el código funcional del PIA (Agregados DDD, Value Objects, Specifications, State Machines, Repositorios SQLAlchemy, Unit of Work, Endpoints FastAPI y Suite de Pruebas con cobertura $>90\%$).
