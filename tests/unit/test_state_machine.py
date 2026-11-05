# tests/unit/test_state_machine.py
import pytest
from src.domain.exceptions import TransicionInvalidaException
from src.domain.state_machine.estado_asignacion_proveedor import (
    AsignacionProveedorStateMachine,
    EstadoAsignacionProveedorEnum,
)
from src.domain.state_machine.estado_evento import (
    EstadoEventoEnum,
    EstadoEventoStateMachine,
)


class TestEstadoEventoStateMachine:
    """Verificación exhaustiva de transiciones válidas e inválidas de Evento."""

    @pytest.mark.parametrize(
        "origen,destino",
        [
            (EstadoEventoEnum.BORRADOR, EstadoEventoEnum.PENDIENTE_ANTICIPO),
            (EstadoEventoEnum.BORRADOR, EstadoEventoEnum.CONFIRMADO),
            (EstadoEventoEnum.BORRADOR, EstadoEventoEnum.CANCELADO),
            (EstadoEventoEnum.PENDIENTE_ANTICIPO, EstadoEventoEnum.CONFIRMADO),
            (EstadoEventoEnum.PENDIENTE_ANTICIPO, EstadoEventoEnum.CANCELADO),
            (EstadoEventoEnum.CONFIRMADO, EstadoEventoEnum.EN_EJECUCION),
            (EstadoEventoEnum.CONFIRMADO, EstadoEventoEnum.CANCELADO),
            (EstadoEventoEnum.EN_EJECUCION, EstadoEventoEnum.FINALIZADO),
        ],
    )
    def test_transiciones_validas_evento(self, origen: EstadoEventoEnum, destino: EstadoEventoEnum) -> None:
        assert EstadoEventoStateMachine.puede_transicionar(origen, destino) is True
        resultado = EstadoEventoStateMachine.validar_transicion(origen, destino)
        assert resultado == destino

    @pytest.mark.parametrize(
        "origen,destino",
        [
            (EstadoEventoEnum.BORRADOR, EstadoEventoEnum.EN_EJECUCION),
            (EstadoEventoEnum.BORRADOR, EstadoEventoEnum.FINALIZADO),
            (EstadoEventoEnum.PENDIENTE_ANTICIPO, EstadoEventoEnum.BORRADOR),
            (EstadoEventoEnum.PENDIENTE_ANTICIPO, EstadoEventoEnum.FINALIZADO),
            (EstadoEventoEnum.CONFIRMADO, EstadoEventoEnum.BORRADOR),
            (EstadoEventoEnum.CONFIRMADO, EstadoEventoEnum.FINALIZADO),
            (EstadoEventoEnum.EN_EJECUCION, EstadoEventoEnum.CANCELADO),
            (EstadoEventoEnum.FINALIZADO, EstadoEventoEnum.CANCELADO),
            (EstadoEventoEnum.FINALIZADO, EstadoEventoEnum.CONFIRMADO),
            (EstadoEventoEnum.CANCELADO, EstadoEventoEnum.CONFIRMADO),
            (EstadoEventoEnum.CANCELADO, EstadoEventoEnum.BORRADOR),
        ],
    )
    def test_transiciones_invalidas_evento_lanzan_excepcion(
        self, origen: EstadoEventoEnum, destino: EstadoEventoEnum
    ) -> None:
        assert EstadoEventoStateMachine.puede_transicionar(origen, destino) is False
        with pytest.raises(TransicionInvalidaException) as exc_info:
            EstadoEventoStateMachine.validar_transicion(origen, destino)

        assert exc_info.value.entidad == "Evento"
        assert exc_info.value.estado_actual == origen.value
        assert exc_info.value.estado_destino == destino.value
        assert exc_info.value.codigo == "TRANSICION_ESTADO_INVALIDA"


class TestAsignacionProveedorStateMachine:
    """Verificación exhaustiva de transiciones válidas e inválidas de AsignacionProveedor."""

    @pytest.mark.parametrize(
        "origen,destino",
        [
            (EstadoAsignacionProveedorEnum.ASIGNADO, EstadoAsignacionProveedorEnum.CONFIRMADO),
            (EstadoAsignacionProveedorEnum.ASIGNADO, EstadoAsignacionProveedorEnum.DECLINADO),
            (EstadoAsignacionProveedorEnum.ASIGNADO, EstadoAsignacionProveedorEnum.VENCIDO),
            (EstadoAsignacionProveedorEnum.CONFIRMADO, EstadoAsignacionProveedorEnum.DECLINADO),
        ],
    )
    def test_transiciones_validas_asignacion_proveedor(
        self,
        origen: EstadoAsignacionProveedorEnum,
        destino: EstadoAsignacionProveedorEnum,
    ) -> None:
        assert AsignacionProveedorStateMachine.puede_transicionar(origen, destino) is True
        resultado = AsignacionProveedorStateMachine.validar_transicion(origen, destino)
        assert resultado == destino

    @pytest.mark.parametrize(
        "origen,destino",
        [
            (EstadoAsignacionProveedorEnum.CONFIRMADO, EstadoAsignacionProveedorEnum.VENCIDO),
            (EstadoAsignacionProveedorEnum.CONFIRMADO, EstadoAsignacionProveedorEnum.ASIGNADO),
            (EstadoAsignacionProveedorEnum.DECLINADO, EstadoAsignacionProveedorEnum.CONFIRMADO),
            (EstadoAsignacionProveedorEnum.VENCIDO, EstadoAsignacionProveedorEnum.CONFIRMADO),
            (EstadoAsignacionProveedorEnum.VENCIDO, EstadoAsignacionProveedorEnum.DECLINADO),
        ],
    )
    def test_transiciones_invalidas_asignacion_proveedor_lanzan_excepcion(
        self,
        origen: EstadoAsignacionProveedorEnum,
        destino: EstadoAsignacionProveedorEnum,
    ) -> None:
        assert AsignacionProveedorStateMachine.puede_transicionar(origen, destino) is False
        with pytest.raises(TransicionInvalidaException) as exc_info:
            AsignacionProveedorStateMachine.validar_transicion(origen, destino)

        assert exc_info.value.entidad == "AsignacionProveedor"
        assert exc_info.value.estado_actual == origen.value
        assert exc_info.value.estado_destino == destino.value
