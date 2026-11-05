# src/domain/state_machine/estado_asignacion_proveedor.py
from enum import Enum
from typing import Dict, Set
from src.domain.exceptions import TransicionInvalidaException


class EstadoAsignacionProveedorEnum(str, Enum):
    """Estados del ciclo de vida de una AsignacionProveedor dentro de un Evento."""

    ASIGNADO = "ASIGNADO"
    CONFIRMADO = "CONFIRMADO"
    DECLINADO = "DECLINADO"
    VENCIDO = "VENCIDO"


class EstadoPagoEnum(str, Enum):
    """Estados financieros para el Aggregate Root CuentaDePagos."""

    PENDIENTE_ANTICIPO = "PENDIENTE_ANTICIPO"
    ANTICIPO_CUBIERTO = "ANTICIPO_CUBIERTO"
    PARCIALMENTE_PAGADO = "PARCIALMENTE_PAGADO"
    LIQUIDADO = "LIQUIDADO"
    REEMBOLSADO_PARCIAL = "REEMBOLSADO_PARCIAL"
    CANCELADO_SIN_REEMBOLSO = "CANCELADO_SIN_REEMBOLSO"


class EstadoCotizacionEnum(str, Enum):
    """Estados de una CotizacionIncremento por cambio de alcance."""

    SOLICITADA = "SOLICITADA"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class AsignacionProveedorStateMachine:
    """
    Máquina de estados determinista para AsignacionProveedor.
    Controla confirmaciones, rechazos y vencimientos por SLA de 48 horas (BR-04).
    """

    _TRANSICIONES_PERMITIDAS: Dict[EstadoAsignacionProveedorEnum, Set[EstadoAsignacionProveedorEnum]] = {
        EstadoAsignacionProveedorEnum.ASIGNADO: {
            EstadoAsignacionProveedorEnum.CONFIRMADO,
            EstadoAsignacionProveedorEnum.DECLINADO,
            EstadoAsignacionProveedorEnum.VENCIDO,
        },
        EstadoAsignacionProveedorEnum.CONFIRMADO: {
            EstadoAsignacionProveedorEnum.DECLINADO,
        },
        EstadoAsignacionProveedorEnum.DECLINADO: set(),
        EstadoAsignacionProveedorEnum.VENCIDO: set(),
    }

    @classmethod
    def puede_transicionar(
        cls,
        origen: EstadoAsignacionProveedorEnum,
        destino: EstadoAsignacionProveedorEnum,
    ) -> bool:
        destinos_validos = cls._TRANSICIONES_PERMITIDAS.get(origen, set())
        return destino in destinos_validos

    @classmethod
    def validar_transicion(
        cls,
        origen: EstadoAsignacionProveedorEnum,
        destino: EstadoAsignacionProveedorEnum,
    ) -> EstadoAsignacionProveedorEnum:
        if not cls.puede_transicionar(origen, destino):
            raise TransicionInvalidaException(
                entidad="AsignacionProveedor",
                estado_actual=origen.value,
                estado_destino=destino.value,
            )
        return destino
