# 🚀 Eventos Nova - Sistema de Gestión de Eventos

> **Repositorio oficial del Equipo 16**  
> **Universidad Autónoma de Nuevo León (UANL) | FIME**  
> **Materia:** Componentes de Lógica de Negocios  
> **Unidad 3:** Diseño Arquitectónico del Sistema

---

## 📌 Descripción del Proyecto
**Eventos Nova** es una plataforma integral diseñada para la planificación, gestión financiera y coordinación logística de eventos. 

Este repositorio contiene la arquitectura base del sistema, desarrollada aplicando los principios de **Domain-Driven Design (DDD)**, **Clean Architecture** y **SOLID**, garantizando un alto nivel de desacoplamiento, escalabilidad y una clara separación de responsabilidades a través de contextos delimitados (*Bounded Contexts*).

---

## 🏗️ Arquitectura y Modelo de Dominio
El núcleo del sistema está dividido en dos agregados principales que se comunican mediante **Consistencia Eventual** (Eventos de Dominio), evitando el acoplamiento transaccional:

1. **Agregado Operativo (`Evento`):** Orquesta la logística, el ciclo de vida del evento, y administra las asignaciones de proveedores (Regla de negocio: Límite de 15 proveedores y SLA de 48h).
2. **Agregado Financiero (`CuentaDePagos`):** Maneja de forma aislada los cálculos de presupuestos, pagos, devoluciones y penalizaciones.



---

## 📁 Estructura del Repositorio

La organización del código y la documentación sigue los estándares de la industria para arquitecturas limpias:

* 📂 **`/docs`**: Contiene la documentación formal del proyecto (ADRs, Mapas de Dominio en PDF, Matrices de Trazabilidad y Bitácoras).
* 📂 **`/diagrams`**: Archivos de código fuente de los diagramas (`.puml` PlantUML) y sus renderizados en `.png`.
* 📂 **`/src`**: Código base (*boilerplate*) en C# con las definiciones de la capa de Dominio y la capa de Infraestructura (Interfaces genéricas, Repositorios e `IUnitOfWork`).
* 📂 **`/tests`**: Carpeta reservada para la futura implementación de pruebas unitarias y de integración.
