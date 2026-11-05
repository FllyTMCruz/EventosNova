# src/domain/events.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Clase base inmutable para eventos de dominio."""

    event_id: UUID = field(default_factory=uuid4, init=False)
    occurred_on: datetime = field(default_factory=lambda: datetime.now(timezone.utc), init=False)


@dataclass(frozen=True)
class ContratoFormalizadoEvent(DomainEvent):
    """Se emite cuando un Evento cumple BR-07 y pasa al estado CONFIRMADO."""

    evento_id: UUID
    cliente_id: UUID
    fecha_evento: datetime
    monto_total_pactado: Decimal
    anticipo_pagado: Decimal


@dataclass(frozen=True)
class AlcanceModificadoEvent(DomainEvent):
    """Se emite cuando se aprueba o registra una modificación de alcance en el Evento (BR-02 / BR-12)."""

    evento_id: UUID
    cotizacion_id: UUID
    invitados_anteriores: int
    invitados_nuevos: int
    costo_adicional: Decimal


@dataclass(frozen=True)
class ProveedorVencidoSLAEvent(DomainEvent):
    """Se emite cuando una asignación de proveedor supera las 48 horas sin confirmación (BR-04)."""

    evento_id: UUID
    asignacion_id: UUID
    proveedor_id: UUID
    fecha_limite: datetime


@dataclass(frozen=True)
class EventoLiquidadoEvent(DomainEvent):
    """Se emite cuando el evento ha sido pagado en su totalidad y finaliza su ejecución."""

    evento_id: UUID
    cuenta_pagos_id: UUID
    total_pagado: Decimal
