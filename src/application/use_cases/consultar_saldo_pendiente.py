# src/application/use_cases/consultar_saldo_pendiente.py
from src.application.dtos.consultas import (
    ConsultarSaldoPendienteQuery,
    SaldoPendienteResponseDTO,
)
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.repositories.interfaces import IUnitOfWork


class ConsultarSaldoPendienteHandler:
    """
    Caso de Uso CU-05: Consultar Saldo Pendiente.
    Recupera el estado financiero exacto del contrato de un evento a partir de su
    Aggregate CuentaDePagos y su Value Object MontoContractual.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    def handle(self, query: ConsultarSaldoPendienteQuery) -> SaldoPendienteResponseDTO:
        with self._uow:
            evento = self._uow.eventos.obtener_por_id(query.evento_id)
            if evento is None:
                raise EntidadNoEncontradaException(
                    tipo_entidad="Evento",
                    identificador=str(query.evento_id),
                )

            cuenta_pagos = self._uow.cuentas_pagos.obtener_por_evento_id(query.evento_id)
            if cuenta_pagos is None:
                raise EntidadNoEncontradaException(
                    tipo_entidad="CuentaDePagos para Evento",
                    identificador=str(query.evento_id),
                )

            mc = cuenta_pagos.monto_contractual
            saldo = mc.calcular_saldo_pendiente()

            return SaldoPendienteResponseDTO(
                evento_id=evento.id,
                cuenta_pagos_id=cuenta_pagos.id,
                estado_evento=evento.estado.value,
                estado_pago=cuenta_pagos.estado_pago.value,
                subtotal_base=mc.subtotal.monto,
                total_incrementos=mc.total_incrementos.monto,
                monto_total_actualizado=mc.monto_total_actualizado.monto,
                anticipo_pactado=mc.anticipo_pactado.monto,
                pagos_realizados=mc.pagos_realizados.monto,
                saldo_pendiente=saldo.monto,
                moneda=mc.subtotal.moneda,
                anticipo_cubierto=cuenta_pagos.esta_anticipo_cubierto(),
                esta_liquidado=cuenta_pagos.esta_liquidada(),
            )
