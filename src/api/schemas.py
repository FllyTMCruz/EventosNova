# src/api/schemas.py
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ErrorResponseSchema(BaseModel):
    """Estructura estándar de error devuelta por la API ante violaciones de dominio."""

    codigo: str = Field(..., description="Código identificador de la excepción de dominio")
    mensaje: str = Field(..., description="Descripción legible de la regla de negocio infringida")
    detalles: Optional[List[str]] = Field(default=None, description="Lista detallada de motivos si aplica")


class ProveedorInicialInputSchema(BaseModel):
    """Datos para asignar un proveedor durante la creación o preparación de un evento."""

    proveedor_id: UUID = Field(..., description="UUID del proveedor en el catálogo")
    nombre_servicio: str = Field(..., min_length=2, max_length=150, description="Nombre del servicio contratado")
    confirmado: bool = Field(default=False, description="Indica si el proveedor ya confirmó su asignación")


class CrearEventoPreliminarRequest(BaseModel):
    """Payload para registrar un evento preliminar junto con su cuenta de pagos inicial."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cliente_id": "11111111-2222-3333-4444-555555555555",
                "fecha_evento": "2026-12-20T19:00:00Z",
                "cantidad_invitados": 150,
                "subtotal_contrato": "120000.00",
                "anticipo_pactado": "36000.00",
                "moneda": "MXN",
                "proveedores_iniciales": [
                    {
                        "proveedor_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "nombre_servicio": "Banquete Gourmet Nova",
                        "confirmado": True,
                    }
                ],
                "usuario_id": "99999999-8888-7777-6666-555555555555",
            }
        }
    )

    cliente_id: UUID
    fecha_evento: datetime
    cantidad_invitados: int = Field(..., description="Cantidad de invitados (BR-05: 20 a 300)")
    subtotal_contrato: Decimal = Field(..., gt=Decimal("0.00"), description="Subtotal base del contrato")
    anticipo_pactado: Decimal = Field(..., gt=Decimal("0.00"), description="Monto mínimo de anticipo para formalizar")
    moneda: str = Field(default="MXN", min_length=3, max_length=3)
    proveedores_iniciales: List[ProveedorInicialInputSchema] = Field(default_factory=list)
    usuario_id: Optional[UUID] = None


class AsignacionProveedorResponseSchema(BaseModel):
    id: UUID
    proveedor_id: UUID
    nombre_servicio: str
    estado: str
    fecha_asignacion: datetime
    fecha_limite_confirmacion: datetime


class EventoPreliminarResponseSchema(BaseModel):
    evento_id: UUID
    cuenta_pagos_id: UUID
    cliente_id: UUID
    fecha_evento: datetime
    cantidad_invitados: int
    estado_evento: str
    estado_pago: str
    subtotal_contrato: Decimal
    anticipo_pactado: Decimal
    saldo_pendiente: Decimal
    moneda: str
    proveedores: List[AsignacionProveedorResponseSchema]
    auditoria_id: UUID


class AsignarProveedorRequest(BaseModel):
    proveedor_id: UUID
    nombre_servicio: str = Field(..., min_length=2, max_length=150)
    confirmar_inmediatamente: bool = Field(default=False)
    usuario_id: Optional[UUID] = None


class FormalizarContratoRequest(BaseModel):
    usuario_id: Optional[UUID] = Field(default=None, description="UUID del operador o cliente que formaliza")
    fecha_operacion: Optional[datetime] = Field(
        default=None,
        description="Fecha de referencia opcional (UTC) para pruebas deterministas",
    )


class FormalizarContratoResponseSchema(BaseModel):
    evento_id: UUID
    estado_anterior: str
    estado_actual: str
    monto_total_contrato: Decimal
    saldo_pendiente: Decimal
    moneda: str
    auditoria_id: UUID


class SolicitarCambioAlcanceRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "descripcion": "Ampliación de 30 invitados adicionales y barra de postres",
                "invitados_adicionales": 30,
                "costo_adicional": "25000.00",
                "moneda": "MXN",
                "porcentaje_anticipo_adicional": "0.00",
                "usuario_id": "99999999-8888-7777-6666-555555555555",
            }
        }
    )

    descripcion: str = Field(..., min_length=5, max_length=255)
    invitados_adicionales: int = Field(..., ge=0, description="Invitados adicionales a sumar al aforo actual")
    costo_adicional: Decimal = Field(..., gt=Decimal("0.00"), description="Costo monetario del incremento")
    moneda: str = Field(default="MXN", min_length=3, max_length=3)
    porcentaje_anticipo_adicional: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    usuario_id: Optional[UUID] = None
    fecha_solicitud: Optional[datetime] = None


class CambioAlcanceResponseSchema(BaseModel):
    evento_id: UUID
    cotizacion_id: UUID
    invitados_anteriores: int
    invitados_actualizados: int
    costo_adicional: Decimal
    nuevo_monto_total_contrato: Decimal
    nuevo_saldo_pendiente: Decimal
    estado_pago_actualizado: str
    auditoria_id: UUID


class RegistrarPagoRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "monto": "36000.00",
                "moneda": "MXN",
                "referencia_pago": "SPEI-984512",
                "usuario_id": "99999999-8888-7777-6666-555555555555",
            }
        }
    )

    monto: Decimal = Field(..., gt=Decimal("0.00"), description="Monto del abono a registrar")
    moneda: str = Field(default="MXN", min_length=3, max_length=3)
    referencia_pago: str = Field(default="PAGO_DIRECTO", max_length=100)
    usuario_id: Optional[UUID] = None


class PagoRegistradoResponseSchema(BaseModel):
    evento_id: UUID
    cuenta_pagos_id: UUID
    monto_abonado: Decimal
    pagos_acumulados: Decimal
    saldo_pendiente: Decimal
    estado_pago_anterior: str
    estado_pago_actual: str
    anticipo_cubierto: bool
    esta_liquidado: bool
    moneda: str
    auditoria_id: UUID


class SaldoPendienteResponseSchema(BaseModel):
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


class LogAuditoriaResponseSchema(BaseModel):
    id: UUID
    entidad_id: UUID
    tipo_entidad: str
    accion: str
    estado_anterior: Optional[str]
    estado_nuevo: str
    detalles: Dict[str, Any]
    usuario_id: Optional[UUID]
    fecha_registro: datetime


class HistorialAuditoriaResponseSchema(BaseModel):
    evento_id: UUID
    total_registros: int
    registros: List[LogAuditoriaResponseSchema]


class ConfirmarProveedorRequest(BaseModel):
    fecha_confirmacion: Optional[datetime] = Field(
        default=None,
        description="Fecha de confirmación opcional (UTC) para verificar SLA de 48h (BR-04)",
    )
    usuario_id: Optional[UUID] = None


class FinalizarEventoRequest(BaseModel):
    usuario_id: Optional[UUID] = None


class FinalizarEventoResponseSchema(BaseModel):
    evento_id: UUID
    estado_anterior: str
    estado_actual: str
    estado_pago: str
    total_pagado: Decimal
    moneda: str
    auditoria_id: UUID


class CancelarEventoRequest(BaseModel):
    fecha_cancelacion: Optional[datetime] = Field(
        default=None,
        description="Fecha de cancelación (UTC) para evaluar ventana de reembolso BR-03 (>30d, 15..30d, <15d)",
    )
    motivo: str = Field(default="Cancelación solicitada por el cliente", max_length=255)
    usuario_id: Optional[UUID] = None


class CancelarEventoResponseSchema(BaseModel):
    evento_id: UUID
    estado_evento_anterior: str
    estado_evento_actual: str
    estado_pago_actual: str
    pagos_realizados: Decimal
    anticipo_retenido: Decimal
    monto_devolucion: Decimal
    moneda: str
    auditoria_id: UUID
