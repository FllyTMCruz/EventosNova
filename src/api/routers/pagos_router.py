# src/api/routers/pagos_router.py
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, status
from src.api.dependencies import get_uow
from src.api.schemas import (
    ErrorResponseSchema,
    PagoRegistradoResponseSchema,
    RegistrarPagoRequest,
    SaldoPendienteResponseSchema,
)
from src.application.dtos.consultas import ConsultarSaldoPendienteQuery
from src.application.use_cases.consultar_saldo_pendiente import (
    ConsultarSaldoPendienteHandler,
)
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.models.auditoria import LogAuditoria
from src.domain.repositories.interfaces import IUnitOfWork
from src.domain.value_objects.dinero import Dinero

router = APIRouter(prefix="/eventos", tags=["Pagos y Finanzas"])


@router.post(
    "/{evento_id}/pagos",
    response_model=PagoRegistradoResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Registrar abono o pago en la cuenta del evento",
    responses={
        404: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def registrar_pago_evento(
    evento_id: UUID,
    payload: RegistrarPagoRequest,
    uow: IUnitOfWork = Depends(get_uow),
) -> PagoRegistradoResponseSchema:
    """
    Registra un pago sobre el Aggregate Root `CuentaDePagos`, recalcula el saldo pendiente
    y el estado financiero (`ANTICIPO_CUBIERTO`, `PARCIALMENTE_PAGADO`, `LIQUIDADO`),
    y persiste la traza inmutable en `LogAuditoria` (ADR-003).
    """
    ahora = datetime.now(timezone.utc)
    abono = Dinero(monto=payload.monto, moneda=payload.moneda)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id))

        cuenta = uow.cuentas_pagos.obtener_por_evento_id(evento_id)
        if cuenta is None:
            raise EntidadNoEncontradaException(
                tipo_entidad="CuentaDePagos para Evento",
                identificador=str(evento_id),
            )

        estado_pago_previo = cuenta.estado_pago.value
        nuevo_saldo = cuenta.registrar_pago(abono)

        log_auditoria = LogAuditoria(
            entidad_id=cuenta.id,
            tipo_entidad="CuentaDePagos",
            accion="REGISTRO_PAGO",
            estado_anterior=estado_pago_previo,
            estado_nuevo=cuenta.estado_pago.value,
            detalles={
                "evento_id": str(evento.id),
                "monto_abonado": str(abono.monto),
                "pagos_acumulados": str(cuenta.monto_contractual.pagos_realizados.monto),
                "saldo_pendiente": str(nuevo_saldo.monto),
                "referencia_pago": payload.referencia_pago,
            },
            usuario_id=payload.usuario_id,
            fecha_registro=ahora,
        )

        uow.cuentas_pagos.guardar(cuenta)
        uow.auditoria.registrar(log_auditoria)
        uow.commit()

        return PagoRegistradoResponseSchema(
            evento_id=evento.id,
            cuenta_pagos_id=cuenta.id,
            monto_abonado=abono.monto,
            pagos_acumulados=cuenta.monto_contractual.pagos_realizados.monto,
            saldo_pendiente=nuevo_saldo.monto,
            estado_pago_anterior=estado_pago_previo,
            estado_pago_actual=cuenta.estado_pago.value,
            anticipo_cubierto=cuenta.esta_anticipo_cubierto(),
            esta_liquidado=cuenta.esta_liquidada(),
            moneda=abono.moneda,
            auditoria_id=log_auditoria.id,
        )


@router.get(
    "/{evento_id}/saldo",
    response_model=SaldoPendienteResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar saldo pendiente y desglose financiero del evento (CU-05)",
    responses={
        404: {"model": ErrorResponseSchema},
    },
)
def consultar_saldo_pendiente(
    evento_id: UUID,
    uow: IUnitOfWork = Depends(get_uow),
) -> SaldoPendienteResponseSchema:
    """Ejecuta el Caso de Uso CU-05 (`ConsultarSaldoPendienteHandler`)."""
    query = ConsultarSaldoPendienteQuery(evento_id=evento_id)
    handler = ConsultarSaldoPendienteHandler(uow=uow)
    dto = handler.handle(query)

    return SaldoPendienteResponseSchema(
        evento_id=dto.evento_id,
        cuenta_pagos_id=dto.cuenta_pagos_id,
        estado_evento=dto.estado_evento,
        estado_pago=dto.estado_pago,
        subtotal_base=dto.subtotal_base,
        total_incrementos=dto.total_incrementos,
        monto_total_actualizado=dto.monto_total_actualizado,
        anticipo_pactado=dto.anticipo_pactado,
        pagos_realizados=dto.pagos_realizados,
        saldo_pendiente=dto.saldo_pendiente,
        moneda=dto.moneda,
        anticipo_cubierto=dto.anticipo_cubierto,
        esta_liquidado=dto.esta_liquidado,
    )
