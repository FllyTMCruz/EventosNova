# src/domain/value_objects/monto_contractual.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from src.domain.exceptions import OperacionFinancieraInvalidaException
from src.domain.value_objects.dinero import Dinero


@dataclass(frozen=True)
class MontoContractual:
    """
    Value Object financiero del Aggregate CuentaDePagos.
    Encapsula el subtotal original, el anticipo mínimo pactado, los incrementos de alcance
    autorizados y el acumulado de pagos recibidos.
    """

    subtotal: Dinero
    anticipo_pactado: Dinero
    pagos_realizados: Dinero
    total_incrementos: Dinero

    def __post_init__(self) -> None:
        if not self.subtotal.es_mayor_que(Dinero.cero(self.subtotal.moneda)):
            raise OperacionFinancieraInvalidaException(
                "El subtotal contractual base debe ser estrictamente mayor a cero."
            )
        if not self.anticipo_pactado.es_mayor_que(Dinero.cero(self.subtotal.moneda)):
            raise OperacionFinancieraInvalidaException("El anticipo pactado debe ser estrictamente mayor a cero.")
        if self.anticipo_pactado.es_mayor_que(self.subtotal):
            raise OperacionFinancieraInvalidaException(
                "El anticipo pactado no puede superar el subtotal original del contrato."
            )
        total_contrato = self.subtotal.sumar(self.total_incrementos)
        if self.pagos_realizados.es_mayor_que(total_contrato):
            raise OperacionFinancieraInvalidaException(
                f"Los pagos realizados ({self.pagos_realizados.monto}) exceden "
                f"el monto total contractual ({total_contrato.monto})."
            )

    @property
    def monto_total_actualizado(self) -> Dinero:
        """Retorna la suma del subtotal original más el total de incrementos autorizados."""
        return self.subtotal.sumar(self.total_incrementos)

    def calcular_saldo_pendiente(self) -> Dinero:
        """Calcula exactamente cuánto falta por pagar del contrato total actualizado."""
        return self.monto_total_actualizado.restar(self.pagos_realizados)

    def cubre_anticipo_requerido(self) -> bool:
        """Determina si los pagos acumulados cubren al menos el anticipo pactado (BR-07)."""
        return self.pagos_realizados.es_mayor_o_igual_que(self.anticipo_pactado)

    def esta_liquidado(self) -> bool:
        """Determina si el saldo pendiente es exactamente cero."""
        return self.calcular_saldo_pendiente().es_igual_a(Dinero.cero(self.subtotal.moneda))

    def con_nuevo_pago(self, monto_abonado: Dinero) -> MontoContractual:
        """Retorna una nueva instancia inmutable sumando un pago validado."""
        if not monto_abonado.es_mayor_que(Dinero.cero(self.subtotal.moneda)):
            raise OperacionFinancieraInvalidaException("El monto a abonar debe ser mayor a cero.")
        nuevos_pagos = self.pagos_realizados.sumar(monto_abonado)
        if nuevos_pagos.es_mayor_que(self.monto_total_actualizado):
            raise OperacionFinancieraInvalidaException(
                f"El pago de {monto_abonado.monto} excede el saldo pendiente actual "
                f"de {self.calcular_saldo_pendiente().monto}."
            )
        return MontoContractual(
            subtotal=self.subtotal,
            anticipo_pactado=self.anticipo_pactado,
            pagos_realizados=nuevos_pagos,
            total_incrementos=self.total_incrementos,
        )

    def con_incremento_alcance(
        self,
        costo_adicional: Dinero,
        porcentaje_anticipo_incremento: Decimal = Decimal("0.00"),
    ) -> MontoContractual:
        """Retorna una nueva instancia inmutable tras autorizar un incremento de alcance."""
        if not costo_adicional.es_mayor_que(Dinero.cero(self.subtotal.moneda)):
            raise OperacionFinancieraInvalidaException("El costo adicional del incremento debe ser mayor a cero.")
        nuevos_incrementos = self.total_incrementos.sumar(costo_adicional)
        anticipo_extra = costo_adicional.multiplicar_porcentaje(porcentaje_anticipo_incremento)
        nuevo_anticipo = self.anticipo_pactado.sumar(anticipo_extra)
        return MontoContractual(
            subtotal=self.subtotal,
            anticipo_pactado=nuevo_anticipo,
            pagos_realizados=self.pagos_realizados,
            total_incrementos=nuevos_incrementos,
        )
