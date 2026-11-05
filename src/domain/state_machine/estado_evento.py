# src/domain/state_machine/estado_evento.py
from enum import Enum
from typing import Dict, Set
from src.domain.exceptions import TransicionInvalidaException


class EstadoEventoEnum(str, Enum):
    """Estados del ciclo de vida del Aggregate Root Evento."""

    BORRADOR = "BORRADOR"
    PENDIENTE_ANTICIPO = "PENDIENTE_ANTICIPO"
    CONFIRMADO = "CONFIRMADO"
    EN_EJECUCION = "EN_EJECUCION"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


class EstadoEventoStateMachine:
    """
    Máquina de estados determinista para el Aggregate Evento.
    Define las transiciones válidas y bloquea cualquier cambio no autorizado.
    """

    _TRANSICIONES_PERMITIDAS: Dict[EstadoEventoEnum, Set[EstadoEventoEnum]] = {
        EstadoEventoEnum.BORRADOR: {
            EstadoEventoEnum.PENDIENTE_ANTICIPO,
            EstadoEventoEnum.CONFIRMADO,
            EstadoEventoEnum.CANCELADO,
        },
        EstadoEventoEnum.PENDIENTE_ANTICIPO: {
            EstadoEventoEnum.CONFIRMADO,
            EstadoEventoEnum.CANCELADO,
        },
        EstadoEventoEnum.CONFIRMADO: {
            EstadoEventoEnum.EN_EJECUCION,
            EstadoEventoEnum.CANCELADO,
        },
        EstadoEventoEnum.EN_EJECUCION: {
            EstadoEventoEnum.FINALIZADO,
        },
        EstadoEventoEnum.FINALIZADO: set(),
        EstadoEventoEnum.CANCELADO: set(),
    }

    @classmethod
    def puede_transicionar(cls, origen: EstadoEventoEnum, destino: EstadoEventoEnum) -> bool:
        destinos_validos = cls._TRANSICIONES_PERMITIDAS.get(origen, set())
        return destino in destinos_validos

    @classmethod
    def validar_transicion(cls, origen: EstadoEventoEnum, destino: EstadoEventoEnum) -> EstadoEventoEnum:
        if not cls.puede_transicionar(origen, destino):
            raise TransicionInvalidaException(
                entidad="Evento",
                estado_actual=origen.value,
                estado_destino=destino.value,
            )
        return destino
