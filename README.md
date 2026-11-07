# 🚀 Eventos Nova — Backend DDD & Clean Architecture (Equipo 16)

**Universidad Autónoma de Nuevo León (UANL)**  
**Facultad de Ingeniería Mecánica y Eléctrica (FIME)**  
**Unidad de Aprendizaje:** Componentes de Lógica de Negocios — Producto Integrador de Aprendizaje (PIA)  
**Integrantes del Equipo 16:**
* Oscar Felipe Renaut Vega (2226683)
* Diana Lucía Hernández Fraire (2226678)
* José Tadeo Cruz Bazaldúa (2226710)

---

## 🌐 Enlaces Oficiales del Proyecto y Despliegue en Producción (Render Cloud)

* **Repositorio GitHub:** [https://github.com/FllyTMCruz/EventosNova](https://github.com/FllyTMCruz/EventosNova)
* **Sistema Desplegado (Interfaz de Prueba en Vivo):** [https://eventos-nova-equipo16.onrender.com/](https://eventos-nova-equipo16.onrender.com/)
* **Swagger UI Activo en Producción (`/docs`):** [https://eventos-nova-equipo16.onrender.com/docs](https://eventos-nova-equipo16.onrender.com/docs)
* **ReDoc Activo en Producción (`/redoc`):** [https://eventos-nova-equipo16.onrender.com/redoc](https://eventos-nova-equipo16.onrender.com/redoc)
* **Especificación OpenAPI 3.1.0 en Vivo (`/openapi.json`):** [https://eventos-nova-equipo16.onrender.com/openapi.json](https://eventos-nova-equipo16.onrender.com/openapi.json)
* **Health Check en Producción (`/health`):** [https://eventos-nova-equipo16.onrender.com/health](https://eventos-nova-equipo16.onrender.com/health)

---

## 1. Estructura del Proyecto y Trazabilidad de Entregables

El repositorio cumple estrictamente con la estructura mínima requerida para el Producto Integrador de Aprendizaje (PIA):

```text
EventosNova/
├── docs/
│   ├── BRD.md                          # BRD completo + Glosario (35 términos) + 18 User Stories (Gherkin) + BPMN
│   ├── User_Stories.md                 # Catálogo detallado de las 18 User Stories con criterios Gherkin
│   ├── Glosario_Dominio.md             # Glosario de Dominio (Lenguaje Ubicuo en 6 familias + DDD)
│   ├── BPMN.md                         # Modelado de procesos de negocio BPMN (Subprocesos 1 y 2)
│   ├── BRD2_EventosNova_final.pdf      # Entregable PDF original: BRD Unidad 2
│   ├── User_Stories_final.pdf          # Entregable PDF original: 18 User Stories Gherkin
│   ├── BPMN_Final.pdf                  # Entregable PDF original: Diagrama BPMN completo
│   ├── Glosario_Dominio_Eventos_Nova.pdf # Entregable PDF original: Glosario de Dominio
│   ├── architecture/                   # ADRs, diagramas UML/DDD, SOLID y decisiones técnicas
│   │   ├── README.md                   # Resumen ejecutivo de arquitectura y principios SOLID
│   │   ├── ADRs.md                     # ADR-001 (Domain Model), ADR-002 (RBAC), ADR-003 (Auditoría), ADR-004 (UoW)
│   │   ├── Matriz_Trazabilidad.md      # Matriz de trazabilidad de extremo a extremo (U2 -> U3 -> Código -> Tests)
│   │   ├── 01_Informe_Arquitectura_Equipo16_Final.pdf
│   │   ├── ADR_EventosNova_Equipo16.pdf
│   │   ├── Arquitectura_Fase1.pdf
│   │   ├── Mapa_Dominio_Etapa3.pdf
│   │   ├── Entregable04_Matriz_Trazabilidad.pdf
│   │   ├── 02_Diagrama_Dominio_Equipo16.pdf
│   │   ├── 02_Diagrama_Dominio_Clases_Eq16.pdf
│   │   ├── 05_Bitacora_IA_Equipo16.pdf
│   │   └── diagrams/                   # Código fuente PlantUML (.puml) y exportaciones (.pdf)
│   └── api/                            # Especificación OpenAPI 3.1.0 y catálogo de endpoints
│       ├── README.md
│       └── openapi.json
├── src/
│   ├── domain/                         # Entidades, Value Objects, Agregados, Eventos, Specifications y State Machines
│   ├── application/                    # Casos de uso (Handlers CQRS, Scheduler SLA) y DTOs
│   ├── infrastructure/                 # Persistencia SQLAlchemy, Repositorios concretos y Unit of Work
│   └── api/                            # Controladores/Endpoints REST en FastAPI y esquemas Pydantic v2
├── tests/
│   ├── unit/                           # Pruebas unitarias de Dominio, Specifications y State Machines
│   └── integration/                    # Pruebas de integración de Casos de Uso y Endpoints REST
├── .github/workflows/ci.yml            # Pipeline CI/CD (Flake8, Black, Pytest con cobertura >= 80%, Docker Build)
├── docker-compose.yml                  # Orquestación reproducible para DB (PostgreSQL) + App (FastAPI) + Tests
├── Dockerfile                          # Imagen contenedorizada multi-entorno
├── .env.example                        # Plantilla de variables de entorno (12-Factor App, sin secretos reales)
└── README.md                           # Instrucciones técnicas, ejecución y demostración en vivo
```

---

## 2. Arquitectura del Sistema

El sistema implementa una arquitectura estricta basada en **Domain-Driven Design (DDD)** y **Clean Architecture**, garantizando la regla de dependencia concéntrica: el núcleo de negocio (`src/domain`) no posee ninguna dependencia hacia frameworks web, motores ORM ni librerías externas.

| Capa | Directorio | Responsabilidad Principal |
| :--- | :--- | :--- |
| **Dominio** | `src/domain/` | Aggregates (`Evento`, `CuentaDePagos`), Entidades internas (`AsignacionProveedor`, `CotizacionIncremento`, `LogAuditoria`), Value Objects inmutables (`Dinero`, `MontoContractual`, `RangoFechas`), Máquinas de Estado, Especificaciones, Eventos de Dominio y Puertos (`IUnitOfWork`, Repositorios). |
| **Aplicación** | `src/application/` | Casos de uso transaccionales (`FormalizarContratoHandler`, `ProcesarCambioAlcanceHandler`, `ConsultarSaldoPendienteHandler`, `EvaluarSLAProveedoresScheduler`) y DTOs inmutables. |
| **Infraestructura** | `src/infrastructure/` | Modelos relacionales SQLAlchemy ORM (`EventoModel`, `CuentaDePagosModel`, `LogAuditoriaModel`), repositorios concretos, `SqlAlchemyUnitOfWork` y bus de eventos en memoria. |
| **Presentación / API** | `src/api/` | Controladores REST en FastAPI, validación de esquemas Pydantic v2, inyección de dependencias y traducción centralizada de excepciones de dominio a códigos HTTP. |

---

## 3. Justificación de Patrones de Diseño Implementados

1. **Aggregate Root con Fronteras Transaccionales Separadas (`Evento` y `CuentaDePagos` — ADR-001):**
   Separa las invariantes operativas (aforo, calendario, proveedores) de las invariantes financieras (anticipos, abonos, reembolsos por cancelación), reduciendo la contención transaccional y manteniendo cohesión alta.
2. **State Machine Explícita (`EstadoEventoStateMachine` y `AsignacionProveedorStateMachine`):**
   Previene transiciones ilegales (por ejemplo, pasar un evento `CANCELADO` a `CONFIRMADO` o vencer un proveedor que ya estaba `CONFIRMADO`), arrojando `TransicionInvalidaException` mapeada a `HTTP 409 Conflict`.
3. **Specification Pattern Compuesto (`Specification[T]`):**
   Encapsula reglas de negocio críticas y combinables booleana y declarativamente:
   - `FormalizacionContratoSpecification` (**BR-07**): Valida las 4 precondiciones obligatorias antes de confirmar un contrato.
   - `VentanaCambioAlcanceSpecification` (**BR-02 / BR-12**): Verifica la anticipación mínima de 7 días naturales (calendario).
   - `CapacidadInvitadosSpecification` (**BR-05**): Garantiza el rango operativo de 20 a 300 invitados.
   - `LimiteProveedoresSpecification` (**BR-15**): Restringe las asignaciones activas a un máximo de 15 proveedores por evento.
4. **Unit of Work (`SqlAlchemyUnitOfWork`) y Registro de Auditoría Inmutable (ADR-003 y ADR-004):**
   Garantiza que todo cambio de estado en `Evento` o `CuentaDePagos` se persista en la misma transacción atómica junto con su registro `LogAuditoria` (*append-only*), publicando los eventos de dominio únicamente tras confirmar el `commit()`.

---

## 4. Guía de Ejecución Local y con Docker Compose

### Opción A: Ejecución con Docker Compose (Recomendado)

1. Copiar el archivo de variables de entorno:
   ```bash
   cp .env.example .env
   ```
2. Construir y levantar la base de datos PostgreSQL y la API FastAPI:
   ```bash
   docker compose up --build -d db app
   ```
3. Acceder a la documentación interactiva OpenAPI (Swagger UI):
   - **Swagger UI:** `http://localhost:8000/docs`
   - **ReDoc:** `http://localhost:8000/redoc`
   - **Healthcheck:** `http://localhost:8000/health`

### Opción B: Ejecución en Entorno Virtual Local (Python 3.11 / 3.12)

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000
```

---

## 5. Ejecución de la Suite de Pruebas y Cobertura ($\ge 80\%$)

Ejecución local con Pytest y reporte de cobertura:
```bash
pytest
```

Ejecución dentro del contenedor aislado de Docker:
```bash
docker compose run --rm tests
```

Verificación de estilo y calidad de código (mismos pasos que el pipeline de GitHub Actions):
```bash
flake8 src tests
black --check --line-length 120 src tests
```

---

## 6. Guía Paso a Paso para la Demostración en Vivo (Live Demo)

Ejecute la siguiente secuencia para demostrar las reglas de negocio y la trazabilidad de auditoría.  
La fecha del evento debe ser futura respecto al día de la demo (el ejemplo usa `2027-11-20`).

### Paso 1: Crear un Evento Preliminar con 1 Proveedor Confirmado (`POST /eventos`)
```bash
curl -X POST "http://localhost:8000/eventos" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": "11111111-2222-3333-4444-555555555555",
    "fecha_evento": "2027-11-20T20:00:00Z",
    "cantidad_invitados": 150,
    "subtotal_contrato": "120000.00",
    "anticipo_pactado": "36000.00",
    "moneda": "MXN",
    "proveedores_iniciales": [
      {
        "proveedor_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "nombre_servicio": "Banquete Imperial Nova",
        "confirmado": true
      }
    ],
    "usuario_id": "99999999-8888-7777-6666-555555555555"
  }'
```
*(Copie el `evento_id` de la respuesta y reemplácelo en los pasos siguientes).*

### Paso 2: Bloqueo de Formalización sin Anticipo Cubierto — BR-07 (`HTTP 409`)
```bash
curl -X POST "http://localhost:8000/eventos/{EVENTO_ID}/formalizar" \
  -H "Content-Type: application/json" \
  -d '{"usuario_id": "99999999-8888-7777-6666-555555555555"}'
```

### Paso 3: Registrar el Pago del Anticipo (`POST /eventos/{id}/pagos`)
```bash
curl -X POST "http://localhost:8000/eventos/{EVENTO_ID}/pagos" \
  -H "Content-Type: application/json" \
  -d '{
    "monto": "36000.00",
    "moneda": "MXN",
    "referencia_pago": "SPEI-DEMO-PIA-16",
    "usuario_id": "99999999-8888-7777-6666-555555555555"
  }'
```

### Paso 4: Formalizar el Contrato — CU-03 / BR-07 (`POST /eventos/{id}/formalizar`)
```bash
curl -X POST "http://localhost:8000/eventos/{EVENTO_ID}/formalizar" \
  -H "Content-Type: application/json" \
  -d '{"usuario_id": "99999999-8888-7777-6666-555555555555"}'
```

### Paso 5: Cambio de Alcance Válido — CU-04 / BR-02 (`POST /eventos/{id}/cambios-alcance`)
```bash
curl -X POST "http://localhost:8000/eventos/{EVENTO_ID}/cambios-alcance" \
  -H "Content-Type: application/json" \
  -d '{
    "descripcion": "Incremento de 30 invitados y barra de postres",
    "invitados_adicionales": 30,
    "costo_adicional": "25000.00",
    "moneda": "MXN",
    "porcentaje_anticipo_adicional": "0.00",
    "usuario_id": "99999999-8888-7777-6666-555555555555"
  }'
```

### Paso 6: Consultar Saldo Pendiente — CU-05 (`GET /eventos/{id}/saldo`)
```bash
curl -X GET "http://localhost:8000/eventos/{EVENTO_ID}/saldo"
```

### Paso 7: Bitácora Inmutable de Auditoría — ADR-003 (`GET /eventos/{id}/auditoria`)
```bash
curl -X GET "http://localhost:8000/eventos/{EVENTO_ID}/auditoria"
```
