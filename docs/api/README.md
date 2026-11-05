# Especificación OpenAPI / Swagger — Eventos Nova API

**Equipo 16 · FIME UANL · Componentes de Lógica de Negocios**  
**Archivo de especificación OpenAPI 3.1.0:** [`openapi.json`](openapi.json)

---

## 1. Acceso a la Documentación Interactiva

Cuando el servidor FastAPI se encuentra en ejecución (`uvicorn src.api.main:app --reload --port 8000` o vía Docker Compose), la documentación interactiva está disponible en:
* **Swagger UI:** `http://localhost:8000/docs`
* **ReDoc:** `http://localhost:8000/redoc`
* **Esquema JSON en vivo:** `http://localhost:8000/openapi.json`

---

## 2. Catálogo de Endpoints REST

| Método | Ruta | Caso de Uso / Regla | Descripción | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Infraestructura | Verifica el estado operativo del servicio. | `200 OK` |
| `POST` | `/eventos` | **CU-01** (`BR-01`, `BR-05`, `BR-15`) | Crea un `Evento` preliminar, asigna proveedores iniciales, inicializa `CuentaDePagos` y audita la creación (`ADR-003`). | `201 Created`, `400`, `409`, `422` |
| `POST` | `/eventos/{evento_id}/proveedores` | **CU-01 / CU-02** (`BR-04`, `BR-15`) | Asigna un nuevo proveedor al evento validando el límite de 15 proveedores activos (`LimiteProveedoresSpecification`) y el SLA de 48 horas. | `201 Created`, `404`, `409` |
| `POST` | `/eventos/{evento_id}/formalizar` | **CU-03** (`BR-07`) | Ejecuta `FormalizarContratoHandler` validando las 4 condiciones obligatorias mediante `FormalizacionContratoSpecification`. | `200 OK`, `404`, `409` |
| `POST` | `/eventos/{evento_id}/cambios-alcance` | **CU-04** (`BR-02`, `BR-05`, `BR-08`, `BR-12`) | Ejecuta `ProcesarCambioAlcanceHandler` validando el plazo de 7 días (`VentanaCambioAlcanceSpecification`), aforo máximo y actualización del `MontoContractual`. | `200 OK`, `400`, `404`, `422` |
| `POST` | `/eventos/evaluar-sla-proveedores` | **CU-02 Scheduler** (`BR-04`) | Ejecuta `EvaluarSLAProveedoresScheduler` para marcar como `VENCIDO` a los proveedores con más de 48 horas sin confirmar. | `200 OK` |
| `POST` | `/eventos/{evento_id}/pagos` | **CU-05** (`BR-07`, `BR-09`) | Registra un abono o anticipo sobre `CuentaDePagos`, actualiza el estado financiero (`ANTICIPO_CUBIERTO`, `PARCIALMENTE_PAGADO`, `LIQUIDADO`) y audita el movimiento. | `200 OK`, `404`, `422` |
| `GET` | `/eventos/{evento_id}/saldo` | **CU-05 Query** (`BR-09`) | Ejecuta `ConsultarSaldoPendienteHandler` devolviendo el desglose financiero completo del evento. | `200 OK`, `404` |
| `GET` | `/eventos/{evento_id}/auditoria` | **FR-17 / ADR-003** | Consulta el historial inmutable (*append-only*) de cambios y eventos registrados para el evento. | `200 OK`, `404` |

---

## 3. Traducción de Excepciones de Dominio a HTTP

| Excepción de Dominio (`src/domain/exceptions.py`) | Código HTTP | Reglas Relacionadas |
| :--- | :--- | :--- |
| `EntidadNoEncontradaException` | `404 Not Found` | Recurso inexistente (`Evento` o `CuentaDePagos`) |
| `RequisitoFormalizacionFaltanteException` | `409 Conflict` | `BR-07` (4 condiciones de formalización) |
| `TransicionInvalidaException` | `409 Conflict` | State Machines (`EstadoEventoStateMachine`, `AsignacionProveedorStateMachine`) |
| `LimiteProveedoresExcedidoException` | `409 Conflict` | `BR-15` (Máximo 15 proveedores activos) |
| `PlazoVencidoException` | `422 Unprocessable Entity` | `BR-01`, `BR-02`, `BR-04`, `BR-12` (Plazos y SLA) |
| `CapacidadInvitadosInvalidaException` | `422 Unprocessable Entity` | `BR-05` (Rango operativo de 20 a 300 invitados) |
| `OperacionFinancieraInvalidaException` | `422 Unprocessable Entity` | Invariantes de `CuentaDePagos` y `MontoContractual` |
