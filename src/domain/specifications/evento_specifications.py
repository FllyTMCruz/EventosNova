# src/domain/specifications/evento_specifications.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, TYPE_CHECKING
from src.domain.specifications.base import Specification
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.domain.state_machine.estado_asignacion_proveedor import EstadoAsignacionProveedorEnum
from src.domain.value_objects.rango_fechas import RangoFechas

if TYPE_CHECKING:
    from src.domain.models.evento import Evento
    from src.domain.models.cuenta_pagos import CuentaDePagos


class CapacidadInvitadosSpecification(Specification[int]):
    """
    Regla de Negocio BR-05:
    La capacidad operativa de un evento debe encontrarse estrictamente entre 20 y 300 invitados.
    """

    MINIMO_INVITADOS: int = 20
    MAXIMO_INVITADOS: int = 300

    def is_satisfied_by(self, cantidad_invitados: int) -> bool:
        return self.MINIMO_INVITADOS <= cantidad_invitados <= self.MAXIMO_INVITADOS


class LimiteProveedoresSpecification(Specification["Evento"]):
    """
    Regla de Negocio BR-15:
    Un evento no puede tener más de 15 proveedores activos (ASIGNADO o CONFIRMADO).
    """

    MAXIMO_PROVEEDORES: int = 15

    def is_satisfied_by(self, evento: "Evento") -> bool:
        proveedores_activos = [
            asig
            for asig in evento.asignaciones_proveedores
            if asig.estado
            in (
                EstadoAsignacionProveedorEnum.ASIGNADO,
                EstadoAsignacionProveedorEnum.CONFIRMADO,
            )
        ]
        return len(proveedores_activos) <= self.MAXIMO_PROVEEDORES

    def puede_agregar_proveedor(self, evento: "Evento") -> bool:
        proveedores_activos = [
            asig
            for asig in evento.asignaciones_proveedores
            if asig.estado
            in (
                EstadoAsignacionProveedorEnum.ASIGNADO,
                EstadoAsignacionProveedorEnum.CONFIRMADO,
            )
        ]
        return (len(proveedores_activos) + 1) <= self.MAXIMO_PROVEEDORES


class VentanaCambioAlcanceSpecification(Specification["Evento"]):
    """
    Reglas de Negocio BR-02 y BR-12:
    Cualquier solicitud de modificación de alcance debe realizarse con un mínimo
    de 7 días naturales de anticipación respecto a la fecha del evento, y el evento
    debe estar en estado CONFIRMADO.
    """

    DIAS_MINIMOS_ANTICIPACION: int = 7

    def __init__(self, fecha_solicitud: datetime) -> None:
        self._fecha_solicitud = fecha_solicitud

    def is_satisfied_by(self, evento: "Evento") -> bool:
        if evento.estado != EstadoEventoEnum.CONFIRMADO:
            return False
        if self._fecha_solicitud >= evento.fecha_evento:
            return False
        rango = RangoFechas(
            fecha_inicio=self._fecha_solicitud,
            fecha_fin=evento.fecha_evento,
        )
        return rango.diferencia_dias_naturales >= self.DIAS_MINIMOS_ANTICIPACION


@dataclass(frozen=True)
class ContextoFormalizacionContrato:
    """Objeto portador de datos para evaluar las 4 condiciones de BR-07."""

    evento: "Evento"
    cuenta_pagos: "CuentaDePagos"
    fecha_actual: datetime


class FormalizacionContratoSpecification(Specification[ContextoFormalizacionContrato]):
    """
    Regla de Negocio BR-07:
    Evalúa las 4 condiciones obligatorias para permitir la formalización de un contrato:
    1. El evento se encuentra en estado BORRADOR o PENDIENTE_ANTICIPO y su fecha es futura.
    2. La cantidad de invitados cumple con el rango operativo de 20 a 300 (BR-05).
    3. Existe al menos 1 proveedor CONFIRMADO, no existen proveedores pendientes/vencidos
       sin resolver y no se excede el límite de 15 proveedores (BR-15).
    4. La CuentaDePagos asociada tiene cubierto el anticipo mínimo pactado.
    """

    def __init__(self) -> None:
        self._capacidad_spec = CapacidadInvitadosSpecification()
        self._limite_proveedores_spec = LimiteProveedoresSpecification()

    def obtener_motivos_incumplimiento(self, candidato: ContextoFormalizacionContrato) -> List[str]:
        motivos: List[str] = []
        evento = candidato.evento
        cuenta = candidato.cuenta_pagos

        # Condición 1: Estado válido y fecha futura
        estados_validos = {EstadoEventoEnum.BORRADOR, EstadoEventoEnum.PENDIENTE_ANTICIPO}
        if evento.estado not in estados_validos:
            motivos.append(f"El evento debe estar en BORRADOR o PENDIENTE_ANTICIPO (actual: {evento.estado.value}).")
        if evento.fecha_evento <= candidato.fecha_actual:
            motivos.append("La fecha programada del evento debe ser posterior a la fecha actual.")

        # Condición 2: Capacidad de invitados válida (BR-05)
        if not self._capacidad_spec.is_satisfied_by(evento.cantidad_invitados):
            motivos.append(
                f"La cantidad de invitados ({evento.cantidad_invitados}) no cumple con el rango de 20 a 300 (BR-05)."
            )

        # Condición 3: Proveedores confirmados y dentro del límite (BR-15)
        confirmados = [
            a for a in evento.asignaciones_proveedores if a.estado == EstadoAsignacionProveedorEnum.CONFIRMADO
        ]
        pendientes = [a for a in evento.asignaciones_proveedores if a.estado == EstadoAsignacionProveedorEnum.ASIGNADO]
        if len(confirmados) == 0:
            motivos.append("El evento debe contar con al menos un proveedor CONFIRMADO.")
        if len(pendientes) > 0:
            motivos.append(f"Existen {len(pendientes)} proveedor(es) en estado ASIGNADO pendientes de confirmar.")
        if not self._limite_proveedores_spec.is_satisfied_by(evento):
            motivos.append("Se excede el límite máximo de 15 proveedores permitidos (BR-15).")

        # Condición 4: Anticipo pactado cubierto en la CuentaDePagos
        if cuenta.evento_id != evento.id:
            motivos.append("La cuenta de pagos proporcionada no corresponde al evento a formalizar.")
        elif not cuenta.esta_anticipo_cubierto():
            pagado = cuenta.monto_contractual.pagos_realizados.monto
            requerido = cuenta.monto_contractual.anticipo_pactado.monto
            motivos.append(f"El anticipo pactado no ha sido cubierto (pagado: {pagado}, requerido: {requerido}).")

        return motivos

    def is_satisfied_by(self, candidate: ContextoFormalizacionContrato) -> bool:
        motivos = self.obtener_motivos_incumplimiento(candidate)
        return len(motivos) == 0
