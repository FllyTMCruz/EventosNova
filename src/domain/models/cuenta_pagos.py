# src/domain/models/cuenta_pagos.py
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
from src.domain.events import DomainEvent
from src.domain.exceptions import OperacionFinancieraInvalidaException, ReglaNegocioException
from src.domain.state_machine.estado_asignacion_proveedor import EstadoPagoEnum
from src.domain.value_objects.dinero import Dinero
from src.domain.value_objects.monto_contractual import MontoContractual
from src.domain.value_objects.rango_fechas import RangoFechas


class CuentaDePagos:
    """
    Aggregate Root Financiero.
    Gestiona el estado financiero del contrato, registro de pagos, incrementos de alcance
    y cálculo de devoluciones por cancelación.
    """

    def __init__(
        self,
        evento_id: UUID,
        monto_contractual: MontoContractual,
        id: Optional[UUID] = None,
        estado_pago: Optional[EstadoPagoEnum] = None,
    ) -> None:
        self._id: UUID = id or uuid4()
        self._evento_id: UUID = evento_id
        self._monto_contractual: MontoContractual = monto_contractual
        self._domain_events: List[DomainEvent] = []

        if estado_pago is not None:
            self._estado_pago = estado_pago
        else:
            self._estado_pago = self._determinar_estado_por_monto(monto_contractual)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def evento_id(self) -> UUID:
        return self._evento_id

    @property
    def estado_pago(self) -> EstadoPagoEnum:
        return self._estado_pago

    @property
    def monto_contractual(self) -> MontoContractual:
        return self._monto_contractual

    def _determinar_estado_por_monto(self, monto: MontoContractual) -> EstadoPagoEnum:
        if monto.esta_liquidado():
            return EstadoPagoEnum.LIQUIDADO
        if monto.cubre_anticipo_requerido():
            if monto.pagos_realizados.es_mayor_que(monto.anticipo_pactado):
                return EstadoPagoEnum.PARCIALMENTE_PAGADO
            return EstadoPagoEnum.ANTICIPO_CUBIERTO
        return EstadoPagoEnum.PENDIENTE_ANTICIPO

    def esta_anticipo_cubierto(self) -> bool:
        """Indica si los pagos acumulados igualan o superan el anticipo requerido."""
        return self._monto_contractual.cubre_anticipo_requerido()

    def esta_liquidada(self) -> bool:
        """Indica si el contrato no presenta saldo pendiente."""
        return self._monto_contractual.esta_liquidado()

    def registrar_pago(self, monto_pago: Dinero) -> Dinero:
        """
        Registra un abono monetario en la cuenta, actualiza el Value Object MontoContractual
        y recalcula el estado financiero. Retorna el nuevo saldo pendiente.
        """
        if self._estado_pago in (
            EstadoPagoEnum.REEMBOLSADO_PARCIAL,
            EstadoPagoEnum.CANCELADO_SIN_REEMBOLSO,
        ):
            raise OperacionFinancieraInvalidaException(
                f"No se pueden registrar pagos en una cuenta con estado '{self._estado_pago.value}'."
            )
        if self._estado_pago == EstadoPagoEnum.LIQUIDADO:
            raise OperacionFinancieraInvalidaException("La cuenta de pagos ya se encuentra completamente liquidada.")

        self._monto_contractual = self._monto_contractual.con_nuevo_pago(monto_pago)
        self._estado_pago = self._determinar_estado_por_monto(self._monto_contractual)
        return self._monto_contractual.calcular_saldo_pendiente()

    def registrar_incremento_alcance(
        self,
        costo_adicional: Dinero,
        porcentaje_anticipo_adicional: Decimal = Decimal("0.00"),
    ) -> Dinero:
        """
        Incorpora el costo de una CotizacionIncremento aprobada al MontoContractual
        y actualiza el estado de pago. Retorna el nuevo saldo pendiente.
        """
        if self._estado_pago in (
            EstadoPagoEnum.REEMBOLSADO_PARCIAL,
            EstadoPagoEnum.CANCELADO_SIN_REEMBOLSO,
        ):
            raise OperacionFinancieraInvalidaException("No se pueden agregar incrementos a una cuenta cancelada.")

        self._monto_contractual = self._monto_contractual.con_incremento_alcance(
            costo_adicional=costo_adicional,
            porcentaje_anticipo_incremento=porcentaje_anticipo_adicional,
        )
        self._estado_pago = self._determinar_estado_por_monto(self._monto_contractual)
        return self._monto_contractual.calcular_saldo_pendiente()

    def calcular_devolucion_cancelacion(
        self,
        fecha_cancelacion: datetime,
        fecha_evento: datetime,
    ) -> Dinero:
        """
        Calcula el monto a devolver al cliente en caso de cancelación según la anticipación:
        - Más de 30 días naturales antes del evento: se retiene el anticipo pactado (no reembolsable)
          y se devuelve el 100% de los pagos excedentes sobre el anticipo.
        - Entre 15 y 30 días naturales: se devuelve el 50% de los pagos excedentes sobre el anticipo.
        - Menos de 15 días naturales: penalización del 100%, devolución de 0.00 MXN.
        Actualiza el estado de la cuenta de pagos.
        """
        if fecha_cancelacion > fecha_evento:
            raise ReglaNegocioException("La fecha de cancelación no puede ser posterior a la fecha del evento.")

        rango = RangoFechas(fecha_inicio=fecha_cancelacion, fecha_fin=fecha_evento)
        dias_anticipacion = rango.diferencia_dias_naturales
        moneda = self._monto_contractual.subtotal.moneda

        pagado = self._monto_contractual.pagos_realizados
        anticipo = self._monto_contractual.anticipo_pactado

        if not pagado.es_mayor_que(anticipo):
            self._estado_pago = EstadoPagoEnum.CANCELADO_SIN_REEMBOLSO
            return Dinero.cero(moneda)

        excedente_sobre_anticipo = pagado.restar(anticipo)

        if dias_anticipacion > 30:
            monto_devolucion = excedente_sobre_anticipo
        elif 15 <= dias_anticipacion <= 30:
            monto_devolucion = excedente_sobre_anticipo.multiplicar_porcentaje(Decimal("50.00"))
        else:
            monto_devolucion = Dinero.cero(moneda)

        if monto_devolucion.es_mayor_que(Dinero.cero(moneda)):
            self._estado_pago = EstadoPagoEnum.REEMBOLSADO_PARCIAL
        else:
            self._estado_pago = EstadoPagoEnum.CANCELADO_SIN_REEMBOLSO

        return monto_devolucion

    def pull_domain_events(self) -> List[DomainEvent]:
        eventos = list(self._domain_events)
        self._domain_events.clear()
        return eventos
