# src/api/routers/pagos_router.py
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Path, status
from src.api.dependencies import get_uow
from src.api.routers.eventos_router import SWAGGER_EVENTO_EJEMPLO, resolver_evento_id
from src.api.schemas import (
    ErrorResponseSchema,
    MensajeResponseSchema,
    RegistrarPagoRequest,
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

# Traducción amigable de estados para no mostrar nombres técnicos al usuario
_ESTADOS_EVENTO_AMIGABLES = {
    "BORRADOR": "en borrador",
    "COTIZADO": "cotizado",
    "PENDIENTE_ANTICIPO": "en espera del pago de anticipo",
    "CONFIRMADO": "confirmado",
    "EN_EJECUCION": "en curso",
    "FINALIZADO": "finalizado y cerrado",
    "CANCELADO": "cancelado",
}


@router.post(
    "/{evento_id}/pagos",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Registrar un pago o abono en la cuenta del evento",
    responses={
        404: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def registrar_pago_evento(
    payload: RegistrarPagoRequest,
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Registra un pago o abono en la cuenta del evento y devuelve únicamente un mensaje
    claro informando cuánto se abonó y cuánto resta por pagar.
    """
    evento_id_real = resolver_evento_id(evento_id)
    ahora = datetime.now(timezone.utc)
    abono = Dinero(monto=payload.monto, moneda=payload.moneda)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id_real)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id_real))

        cuenta = uow.cuentas_pagos.obtener_por_evento_id(evento_id_real)
        if cuenta is None:
            raise EntidadNoEncontradaException(
                tipo_entidad="CuentaDePagos para Evento",
                identificador=str(evento_id_real),
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

        moneda = abono.moneda
        acumulado = cuenta.monto_contractual.pagos_realizados.monto

        # Mensaje claro según si la cuenta ya quedó liquidada, si ya cubrió el anticipo o si es abono parcial
        if cuenta.esta_liquidada():
            texto = (
                f"Su pago por ${abono.monto:,.2f} {moneda} se registró con éxito. "
                f"¡La cuenta de su evento ha quedado liquidada al 100% (total pagado: ${acumulado:,.2f} {moneda}) "
                "y ya no tiene ningún saldo pendiente!"
            )
        elif cuenta.esta_anticipo_cubierto():
            texto = (
                f"Su pago por ${abono.monto:,.2f} {moneda} se registró con éxito y el anticipo requerido "
                f"ya se encuentra cubierto. Su saldo restante por pagar es de ${nuevo_saldo.monto:,.2f} {moneda}. "
                "Si su contrato aún no estaba confirmado, ya puede formalizarlo."
            )
        else:
            texto = (
                f"Su abono por ${abono.monto:,.2f} {moneda} se registró correctamente. "
                f"Hasta el momento lleva abonados ${acumulado:,.2f} {moneda} y resta un saldo "
                f"pendiente de ${nuevo_saldo.monto:,.2f} {moneda}."
            )
        return MensajeResponseSchema(message=texto)


@router.get(
    "/{evento_id}/saldo",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar el resumen de pagos y saldo pendiente del evento",
    responses={
        404: {"model": ErrorResponseSchema},
    },
)
def consultar_saldo_pendiente(
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """Devuelve un resumen claro y fácil de leer del estado del evento y sus pagos."""
    evento_id_real = resolver_evento_id(evento_id)
    query = ConsultarSaldoPendienteQuery(evento_id=evento_id_real)
    handler = ConsultarSaldoPendienteHandler(uow=uow)
    dto = handler.handle(query)

    estado_ev = _ESTADOS_EVENTO_AMIGABLES.get(dto.estado_evento, dto.estado_evento.lower())
    moneda = dto.moneda

    # Construye una explicación clara del estado financiero sin mostrar códigos ni IDs
    if dto.esta_liquidado:
        situacion_pago = "la cuenta ya está liquidada en su totalidad sin adeudos pendientes"
    elif dto.anticipo_cubierto:
        situacion_pago = (
            f"el anticipo ya fue cubierto y resta un saldo pendiente de ${dto.saldo_pendiente:,.2f} {moneda}"
        )
    else:
        situacion_pago = (
            f"aún está pendiente cubrir el anticipo mínimo de ${dto.anticipo_pactado:,.2f} {moneda} "
            f"(saldo total por pagar: ${dto.saldo_pendiente:,.2f} {moneda})"
        )

    return MensajeResponseSchema(
        message=(
            f"Resumen de su evento: actualmente el evento se encuentra {estado_ev}. "
            f"El costo total del contrato es de ${dto.monto_total_actualizado:,.2f} {moneda} "
            f"(costo base de ${dto.subtotal_base:,.2f} {moneda} más ${dto.total_incrementos:,.2f} {moneda} "
            f"por servicios o invitados adicionales), se han pagado ${dto.pagos_realizados:,.2f} {moneda} "
            f"y {situacion_pago}."
        )
    )
