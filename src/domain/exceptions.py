# src/domain/exceptions.py
from typing import List, Optional


class DomainException(Exception):
    """Excepción base para todos los errores de la capa de dominio."""

    def __init__(self, mensaje: str, codigo: str = "ERROR_DOMINIO") -> None:
        self.mensaje = mensaje
        self.codigo = codigo
        super().__init__(self.mensaje)


class ReglaNegocioException(DomainException):
    """Se lanza cuando se infringe una regla de negocio general."""

    def __init__(self, mensaje: str, codigo: str = "REGLA_NEGOCIO_VIOLADA") -> None:
        super().__init__(mensaje=mensaje, codigo=codigo)


class TransicionInvalidaException(ReglaNegocioException):
    """Se lanza al intentar realizar una transición de estado no permitida en la State Machine."""

    def __init__(self, entidad: str, estado_actual: str, estado_destino: str) -> None:
        self.entidad = entidad
        self.estado_actual = estado_actual
        self.estado_destino = estado_destino
        mensaje = (
            f"Transición de estado inválida en '{entidad}': "
            f"no es posible pasar de '{estado_actual}' a '{estado_destino}'."
        )
        super().__init__(mensaje=mensaje, codigo="TRANSICION_ESTADO_INVALIDA")


class PlazoVencidoException(ReglaNegocioException):
    """Se lanza cuando una operación se solicita fuera de la ventana de tiempo permitida (BR-02, BR-04, BR-12)."""

    def __init__(self, operacion: str, detalle_plazo: str) -> None:
        self.operacion = operacion
        self.detalle_plazo = detalle_plazo
        mensaje = f"Plazo vencido para la operación '{operacion}': {detalle_plazo}"
        super().__init__(mensaje=mensaje, codigo="PLAZO_OPERACION_VENCIDO")


class RequisitoFormalizacionFaltanteException(ReglaNegocioException):
    """Se lanza cuando el evento no cumple las 4 condiciones de BR-07 para formalizar el contrato."""

    def __init__(self, motivos: List[str]) -> None:
        self.motivos = motivos
        detalle = "; ".join(motivos)
        mensaje = f"No es posible formalizar el contrato (BR-07). Requisitos incumplidos: {detalle}"
        super().__init__(mensaje=mensaje, codigo="REQUISITO_FORMALIZACION_FALTANTE")


class CapacidadInvitadosInvalidaException(ReglaNegocioException):
    """Se lanza cuando la cantidad de invitados está fuera del rango de 20 a 300 (BR-05)."""

    def __init__(self, cantidad_solicitada: int, minimo: int = 20, maximo: int = 300) -> None:
        self.cantidad_solicitada = cantidad_solicitada
        mensaje = (
            f"La cantidad de invitados ({cantidad_solicitada}) viola la regla BR-05. "
            f"El rango permitido es de {minimo} a {maximo} invitados."
        )
        super().__init__(mensaje=mensaje, codigo="CAPACIDAD_INVITADOS_INVALIDA")


class LimiteProveedoresExcedidoException(ReglaNegocioException):
    """Se lanza cuando se intenta superar el límite máximo de 15 proveedores activos (BR-15)."""

    def __init__(self, cantidad_actual: int, limite_maximo: int = 15) -> None:
        self.cantidad_actual = cantidad_actual
        self.limite_maximo = limite_maximo
        mensaje = (
            f"Se ha alcanzado el límite máximo de proveedores permitidos por evento ({limite_maximo}) "
            f"según la regla BR-15 (actuales: {cantidad_actual})."
        )
        super().__init__(mensaje=mensaje, codigo="LIMITE_PROVEEDORES_EXCEDIDO")


class OperacionFinancieraInvalidaException(ReglaNegocioException):
    """Se lanza ante inconsistencias en montos, pagos negativos o excesos sobre el saldo pendiente."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje=mensaje, codigo="OPERACION_FINANCIERA_INVALIDA")


class EntidadNoEncontradaException(DomainException):
    """Se lanza cuando un Aggregate Root o Entidad interna no existe en el contexto."""

    def __init__(self, tipo_entidad: str, identificador: Optional[str] = None) -> None:
        detalle_id = f" con ID '{identificador}'" if identificador else ""
        mensaje = f"La entidad '{tipo_entidad}'{detalle_id} no fue encontrada."
        super().__init__(mensaje=mensaje, codigo="ENTIDAD_NO_ENCONTRADA")
