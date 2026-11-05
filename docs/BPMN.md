# Modelo de Procesos de Negocio (BPMN) — Caso Eventos Nova

**Universidad Autónoma de Nuevo León (UANL) · FIME**  
**Unidad 2 y PIA · Equipo 16**  
**Diagrama BPMN original en PDF:** [`BPMN_Final.pdf`](BPMN_Final.pdf)

---

## 1. Subproceso 1: Cotización y Asignación Preliminar de Proveedores (Etapas 1 y 2)

Carriles (*Swimlanes*) participantes: **Cliente**, **Coordinador**, **Proveedor**.

```mermaid
flowchart LR
    subgraph Cliente
        C1(["Inicio: Solicita cotización"]) --> C2["Indica fecha, tipo de evento y número estimado de invitados"]
        C3["Recibe propuesta y cotización"] --> C4(["Fin: Continúa en Contratación"])
    end

    subgraph Coordinador
        K1["Recibir y registrar solicitud"] --> K2{"¿Anticipación >= 15 días? (BR-01)"}
        K2 -- "No (< 15 días)" --> K3["Alertar: disponibilidad no garantizada (FR-01)"]
        K2 -- "Sí (>= 15 días)" --> K4["Registrar solicitud y continuar"]
        K3 --> K4
        K4 --> K5{"¿Invitados > 300? (BR-05)"}
        K5 -- "Sí (> 300)" --> K6["Evaluación especial de capacidad y proveedores"]
        K5 -- "No (20 a 300)" --> K7["Continuar con flujo normal"]
        K6 --> K8["Preparar propuesta preliminar e identificar proveedores"]
        K7 --> K8
        K8 --> K9{"¿Proveedores asignados = 15? (BR-15)"}
        K9 -- "Sí (= 15)" --> K10["Solicitar autorización especial para exceder límite"]
        K9 -- "No (< 15)" --> K11["Solicitar disponibilidad, precio y condiciones al proveedor"]
        K11 --> K12["Esperar / recibir respuesta del proveedor"]
        K12 --> K13{"¿Respondió dentro de 48 h? (BR-04)"}
        K13 -- "No (> 48 h)" --> K14["Marcar proveedor 'Sin confirmar' y notificar"]
        K13 -- "Sí (<= 48 h)" --> K15{"¿Disponible y acepta condiciones?"}
        K14 --> K16["Buscar proveedor alternativo (BR-10 / BR-13)"]
        K15 -- "No" --> K16
        K16 --> K11
        K15 -- "Sí" --> K17["Registrar confirmación del proveedor"]
        K17 --> K18{"¿Quedan más proveedores por asignar?"}
        K18 -- "Sí" --> K9
        K18 -- "No" --> K19["Consolidar proveedores y enviar cotización al cliente"]
    end

    subgraph Proveedor
        P1["Evaluar y responder disponibilidad, precio y condiciones (máx. 48 h - BR-04)"]
    end

    C2 --> K1
    K11 --> P1
    P1 --> K12
    K19 --> C3
```

---

## 2. Subproceso 2: Formalización de Contrato, Cambios de Alcance y Liquidación (Etapas 3, 4 y 5)

Carriles (*Swimlanes*) participantes: **Cliente**, **Coordinador**, **Administración**.

```mermaid
flowchart TD
    subgraph Formalizacion ["Etapa 3: Formalización Contractual (CU-03)"]
        F1["Cliente acepta propuesta, entrega datos y paga anticipo"] --> F2{"¿Cumple las 4 condiciones de BR-07?"}
        F2 -- "No" --> F3["Bloquear formalización e indicar requisito faltante (FR-07)"]
        F2 -- "Sí" --> F4["Coordinador formaliza Contrato y se crea CuentaDePagos"]
    end

    subgraph Coordinacion ["Etapa 4: Cambios de Alcance e Invitados (CU-04)"]
        F4 --> M1["Cliente solicita modificación de alcance o aumento de invitados"]
        M1 --> M2{"¿Faltan >= 7 días naturales? (BR-02)"}
        M2 -- "No (< 7 días)" --> M3{"¿Proveedores confirman viabilidad? (BR-12)"}
        M3 -- "No" --> M4["Marcar cambio como 'No garantizado' y rechazar"]
        M3 -- "Sí" --> M5["Generar CotizacionIncremento pendiente de aceptación (BR-08)"]
        M2 -- "Sí (>= 7 días)" --> M6{"¿<= 2 cambios gratuitos y sin costo extra? (BR-06)"}
        M6 -- "Sí" --> M7["Aplicar cambio sin costo adicional"]
        M6 -- "No" --> M5
        M5 --> M8{"¿Cliente autoriza nuevo monto? (BR-08)"}
        M8 -- "Sí" --> M9["Actualizar MontoContractual y aplicar cambio"]
        M8 -- "No" --> M10["Mantener cambio como 'No autorizado'"]
    end

    subgraph Liquidacion ["Etapa 5: Liquidación de Saldo o Cancelación (CU-05)"]
        M7 --> L1{"¿Liquidación >= 3 días antes del evento? (BR-09)"}
        M9 --> L1
        M4 --> L1
        M10 --> L1
        L1 -- "Sí (Saldo = 0)" --> L2(["Evento en estado PAGADO -> Ejecución y Cierre"])
        L1 -- "No (< 3 días con saldo)" --> L3{"¿Administración autoriza excepción de pago? (BR-16)"}
        L3 -- "Sí" --> L4["Registrar excepción en LogAuditoria (FR-16, FR-17)"] --> L2
        L3 -- "No" --> L5(["Suspender coordinación / Cancelar evento deduciendo gastos comprometidos (BR-09, BR-14)"])
    end
```
