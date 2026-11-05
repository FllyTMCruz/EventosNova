# src/application/dtos/comandos.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class FormalizarContratoCommand:
    """Comando de entrada para el caso de uso CU-03 (Formalizar Contrato)."""

    evento_id: UUID
    usuario_id: Optional[UUID] = None
    fecha_operacion: Optional[datetime] = None


@dataclass(frozen=True)
class ContratoFormalizadoDTO:
    """Respuesta tras formalizar exitosamente un contrato."""

    evento_id: UUID
    estado_anterior: str
    estado_actual: str
    monto_total_contrato: Decimal
    saldo_pendiente: Decimal
    moneda: str
    auditoria_id: UUID


@dataclass(frozen=True)
class ProcesarCambioAlcanceCommand:
    """Comando de entrada para el caso de uso CU-04 (Procesar Cambio de Alcance)."""

    evento_id: UUID
    descripcion: str
    invitados_adicionales: int
    costo_adicional: Decimal
    moneda: str = "MXN"
    porcentaje_anticipo_adicional: Decimal = Decimal("0.00")
    usuario_id: Optional[UUID] = None
    fecha_solicitud: Optional[datetime] = None


@dataclass(frozen=True)
class CambioAlcanceProcesadoDTO:
    """Respuesta tras procesar y aprobar un cambio de alcance."""

    evento_id: UUID
    cotizacion_id: UUID
    invitados_anteriores: int
    invitados_actualizados: int
    costo_adicional: Decimal
    nuevo_monto_total_contrato: Decimal
    nuevo_saldo_pendiente: Decimal
    estado_pago_actualizado: str
    auditoria_id: UUID
