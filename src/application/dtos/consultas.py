# src/application/dtos/consultas.py
from dataclasses import dataclass
from decimal import Decimal
from typing import List
from uuid import UUID


@dataclass(frozen=True)
class ConsultarSaldoPendienteQuery:
    """Query de entrada para el caso de uso CU-05 (Consultar Saldo Pendiente)."""

    evento_id: UUID


@dataclass(frozen=True)
class SaldoPendienteResponseDTO:
    """Proyección financiera detallada del contrato de un evento (CU-05)."""

    evento_id: UUID
    cuenta_pagos_id: UUID
    estado_evento: str
    estado_pago: str
    subtotal_base: Decimal
    total_incrementos: Decimal
    monto_total_actualizado: Decimal
    anticipo_pactado: Decimal
    pagos_realizados: Decimal
    saldo_pendiente: Decimal
    moneda: str
    anticipo_cubierto: bool
    esta_liquidado: bool


@dataclass(frozen=True)
class ProveedorVencidoDTO:
    """Detalle de una asignación de proveedor marcada como VENCIDO por SLA."""

    evento_id: UUID
    asignacion_id: UUID
    proveedor_id: UUID
    nombre_servicio: str
    fecha_limite_confirmacion: str


@dataclass(frozen=True)
class ResultadoEvaluacionSLADTO:
    """Resumen de ejecución del job EvaluarSLAProveedoresScheduler (BR-04)."""

    fecha_corte: str
    eventos_evaluados: int
    total_asignaciones_vencidas: int
    proveedores_vencidos: List[ProveedorVencidoDTO]
