# src/domain/value_objects/dinero.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from src.domain.exceptions import OperacionFinancieraInvalidaException


@dataclass(frozen=True)
class Dinero:
    """Value Object inmutable para representar valores monetarios exactos."""

    monto: Decimal
    moneda: str = "MXN"

    def __post_init__(self) -> None:
        if not isinstance(self.monto, Decimal):
            object.__setattr__(self, "monto", Decimal(str(self.monto)))

        monto_redondeado = self.monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "monto", monto_redondeado)

        if self.monto < Decimal("0.00"):
            raise OperacionFinancieraInvalidaException(
                f"El monto monetario no puede ser negativo: {self.monto} {self.moneda}."
            )
        if not self.moneda or len(self.moneda.strip()) != 3:
            raise OperacionFinancieraInvalidaException(f"Código de moneda ISO inválido: '{self.moneda}'.")
        object.__setattr__(self, "moneda", self.moneda.strip().upper())

    @classmethod
    def cero(cls, moneda: str = "MXN") -> Dinero:
        return cls(monto=Decimal("0.00"), moneda=moneda)

    def _validar_misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise OperacionFinancieraInvalidaException(
                f"No se pueden operar monedas distintas: {self.moneda} y {otro.moneda}."
            )

    def sumar(self, otro: Dinero) -> Dinero:
        self._validar_misma_moneda(otro)
        return Dinero(monto=self.monto + otro.monto, moneda=self.moneda)

    def restar(self, otro: Dinero) -> Dinero:
        self._validar_misma_moneda(otro)
        resultado = self.monto - otro.monto
        if resultado < Decimal("0.00"):
            raise OperacionFinancieraInvalidaException(
                f"La resta monetaria produce un saldo negativo inválido ({resultado} {self.moneda})."
            )
        return Dinero(monto=resultado, moneda=self.moneda)

    def multiplicar_porcentaje(self, porcentaje: Decimal) -> Dinero:
        if porcentaje < Decimal("0.00"):
            raise OperacionFinancieraInvalidaException("El porcentaje no puede ser negativo.")
        factor = Decimal(str(porcentaje)) / Decimal("100.00")
        return Dinero(monto=self.monto * factor, moneda=self.moneda)

    def es_mayor_o_igual_que(self, otro: Dinero) -> bool:
        self._validar_misma_moneda(otro)
        return self.monto >= otro.monto

    def es_mayor_que(self, otro: Dinero) -> bool:
        self._validar_misma_moneda(otro)
        return self.monto > otro.monto

    def es_igual_a(self, otro: Dinero) -> bool:
        self._validar_misma_moneda(otro)
        return self.monto == otro.monto
