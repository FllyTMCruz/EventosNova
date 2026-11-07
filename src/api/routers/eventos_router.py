# src/api/routers/eventos_router.py
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Body, Depends, Path, Response, status
from src.api.dependencies import get_uow
from src.api.schemas import (
    AsignarProveedorRequest,
    CancelarEventoRequest,
    ConfirmarProveedorRequest,
    CrearEventoPreliminarRequest,
    ErrorResponseSchema,
    FinalizarEventoRequest,
    FormalizarContratoRequest,
    MensajeResponseSchema,
    SolicitarCambioAlcanceRequest,
)
from src.application.dtos.comandos import (
    FormalizarContratoCommand,
    ProcesarCambioAlcanceCommand,
)
from src.application.use_cases.evaluar_sla_proveedores import (
    EvaluarSLAProveedoresScheduler,
)
from src.application.use_cases.formalizar_contrato import FormalizarContratoHandler
from src.application.use_cases.procesar_cambio_alcance import (
    ProcesarCambioAlcanceHandler,
)
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.models.auditoria import LogAuditoria
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import Evento
from src.domain.repositories.interfaces import IUnitOfWork
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.domain.value_objects.dinero import Dinero
from src.domain.value_objects.monto_contractual import MontoContractual

router = APIRouter(prefix="/eventos", tags=["Eventos y Contratos"])

# Identificadores de ejemplo predeterminados en Swagger para que el usuario no tenga que copiar IDs manualmente
SWAGGER_EVENTO_EJEMPLO = UUID("11111111-1111-1111-1111-111111111111")
SWAGGER_PROVEEDOR_EJEMPLO = UUID("22222222-2222-2222-2222-222222222222")

_ULTIMO_EVENTO_ID: Optional[UUID] = None
_ULTIMO_PROVEEDOR_ID: Optional[UUID] = None


def resolver_evento_id(evento_id: UUID) -> UUID:
    """Si el usuario ejecuta desde Swagger con el ID de ejemplo, usa automáticamente el último evento creado."""
    if evento_id == SWAGGER_EVENTO_EJEMPLO and _ULTIMO_EVENTO_ID is not None:
        return _ULTIMO_EVENTO_ID
    return evento_id


def resolver_proveedor_id(proveedor_id: UUID) -> UUID:
    """Si el usuario ejecuta desde Swagger con el ID de ejemplo, usa el último proveedor asignado."""
    if proveedor_id == SWAGGER_PROVEEDOR_EJEMPLO and _ULTIMO_PROVEEDOR_ID is not None:
        return _ULTIMO_PROVEEDOR_ID
    return proveedor_id


@router.post(
    "",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo evento y generar su cotización inicial",
    responses={
        400: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def crear_evento_preliminar(
    payload: CrearEventoPreliminarRequest,
    response: Response,
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Registra un nuevo evento validando el número de invitados y los proveedores iniciales,
    y devuelve únicamente un mensaje claro y fácil de entender para el usuario.
    """
    global _ULTIMO_EVENTO_ID, _ULTIMO_PROVEEDOR_ID
    ahora = datetime.now(timezone.utc)
    moneda = payload.moneda.upper()

    with uow:
        evento = Evento(
            cliente_id=payload.cliente_id,
            fecha_evento=payload.fecha_evento,
            cantidad_invitados=payload.cantidad_invitados,
            estado=EstadoEventoEnum.PENDIENTE_ANTICIPO,
            fecha_creacion=ahora,
        )

        for prov in payload.proveedores_iniciales:
            asignacion = evento.asignar_proveedor(
                proveedor_id=prov.proveedor_id,
                nombre_servicio=prov.nombre_servicio,
                fecha_asignacion=ahora,
            )
            _ULTIMO_PROVEEDOR_ID = prov.proveedor_id
            if prov.confirmado:
                asignacion.confirmar(fecha_confirmacion=ahora)

        monto_vo = MontoContractual(
            subtotal=Dinero(monto=payload.subtotal_contrato, moneda=moneda),
            anticipo_pactado=Dinero(monto=payload.anticipo_pactado, moneda=moneda),
            pagos_realizados=Dinero.cero(moneda),
            total_incrementos=Dinero.cero(moneda),
        )
        cuenta_pagos = CuentaDePagos(
            evento_id=evento.id,
            monto_contractual=monto_vo,
        )

        log_auditoria = LogAuditoria(
            entidad_id=evento.id,
            tipo_entidad="Evento",
            accion="CREACION_EVENTO_PRELIMINAR",
            estado_anterior=None,
            estado_nuevo=evento.estado.value,
            detalles={
                "cliente_id": str(evento.cliente_id),
                "cantidad_invitados": evento.cantidad_invitados,
                "subtotal_contrato": str(payload.subtotal_contrato),
                "anticipo_pactado": str(payload.anticipo_pactado),
                "proveedores_asignados": len(evento.asignaciones_proveedores),
            },
            usuario_id=payload.usuario_id,
            fecha_registro=ahora,
        )

        uow.eventos.guardar(evento)
        uow.cuentas_pagos.guardar(cuenta_pagos)
        uow.auditoria.registrar(log_auditoria)
        uow.commit()

        _ULTIMO_EVENTO_ID = evento.id
        response.headers["X-Evento-Id"] = str(evento.id)

        # Mensaje informativo y claro para un usuario común, sin mostrar IDs ni códigos técnicos
        fecha_legible = evento.fecha_evento.strftime("%d/%m/%Y")
        total_prov = len(evento.asignaciones_proveedores)
        sub_txt = f"${monto_vo.subtotal.monto:,.2f} {moneda}"
        ant_txt = f"${monto_vo.anticipo_pactado.monto:,.2f} {moneda}"
        return MensajeResponseSchema(
            message=(
                f"¡Su evento para {evento.cantidad_invitados} invitados programado para el {fecha_legible} "
                f"ha sido registrado con éxito! Se incluyeron {total_prov} servicio(s) de proveedores y el "
                f"costo total es de {sub_txt}. Para confirmar y formalizar su contrato, solo falta "
                f"realizar el pago del anticipo por {ant_txt}."
            )
        )


@router.post(
    "/{evento_id}/proveedores",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un proveedor de servicios al evento",
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def asignar_proveedor_evento(
    response: Response,
    payload: AsignarProveedorRequest,
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """Asigna un proveedor al evento e informa al usuario en lenguaje sencillo sobre su estado."""
    global _ULTIMO_PROVEEDOR_ID
    evento_id_real = resolver_evento_id(evento_id)
    ahora = datetime.now(timezone.utc)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id_real)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id_real))

        asignacion = evento.asignar_proveedor(
            proveedor_id=payload.proveedor_id,
            nombre_servicio=payload.nombre_servicio,
            fecha_asignacion=ahora,
        )
        if payload.confirmar_inmediatamente:
            asignacion.confirmar(fecha_confirmacion=ahora)

        log = LogAuditoria(
            entidad_id=asignacion.id,
            tipo_entidad="AsignacionProveedor",
            accion="ASIGNACION_PROVEEDOR_BR15",
            estado_anterior=None,
            estado_nuevo=asignacion.estado.value,
            detalles={
                "evento_id": str(evento.id),
                "proveedor_id": str(asignacion.proveedor_id),
                "nombre_servicio": asignacion.nombre_servicio,
            },
            usuario_id=payload.usuario_id,
            fecha_registro=ahora,
        )

        uow.eventos.guardar(evento)
        uow.auditoria.registrar(log)
        uow.commit()

        _ULTIMO_PROVEEDOR_ID = asignacion.proveedor_id
        response.headers["X-Proveedor-Id"] = str(asignacion.proveedor_id)

        # Mensaje claro indicando si el proveedor ya quedó confirmado o tiene 48 horas para responder
        if payload.confirmar_inmediatamente:
            texto = (
                f"El servicio de '{asignacion.nombre_servicio}' fue agregado y confirmado "
                "exitosamente para su evento."
            )
        else:
            texto = (
                f"El proveedor del servicio '{asignacion.nombre_servicio}' ha sido agregado a su evento. "
                "A partir de este momento cuenta con un plazo máximo de 48 horas para confirmar su participación."
            )
        return MensajeResponseSchema(message=texto)


@router.post(
    "/{evento_id}/formalizar",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Confirmar y formalizar el contrato del evento",
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def formalizar_contrato(
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    payload: Optional[FormalizarContratoRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Verifica que el anticipo esté pagado y los proveedores confirmados,
    formalizando el contrato y devolviendo un mensaje claro de confirmación.
    """
    evento_id_real = resolver_evento_id(evento_id)
    datos = payload or FormalizarContratoRequest()
    command = FormalizarContratoCommand(
        evento_id=evento_id_real,
        usuario_id=datos.usuario_id,
        fecha_operacion=datos.fecha_operacion,
    )
    handler = FormalizarContratoHandler(uow=uow)
    resultado = handler.handle(command)

    # Mensaje amigable confirmando que el contrato quedó formalizado y mostrando el saldo restante
    tot_txt = f"${resultado.monto_total_contrato:,.2f} {resultado.moneda}"
    sal_txt = f"${resultado.saldo_pendiente:,.2f} {resultado.moneda}"
    return MensajeResponseSchema(
        message=(
            "¡Su contrato ha sido formalizado y su evento ha quedado oficialmente confirmado! "
            f"El costo total acordado es de {tot_txt} y su saldo pendiente por cubrir "
            f"antes del evento es de {sal_txt}."
        )
    )


@router.post(
    "/{evento_id}/cambios-alcance",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Solicitar ampliación de invitados o servicios adicionales",
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def solicitar_cambio_alcance(
    payload: SolicitarCambioAlcanceRequest,
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Registra un cambio de invitados o servicios adicionales validando el plazo mínimo
    de 7 días de anticipación, y explica el nuevo total en palabras sencillas.
    """
    evento_id_real = resolver_evento_id(evento_id)
    command = ProcesarCambioAlcanceCommand(
        evento_id=evento_id_real,
        descripcion=payload.descripcion,
        invitados_adicionales=payload.invitados_adicionales,
        costo_adicional=payload.costo_adicional,
        moneda=payload.moneda,
        porcentaje_anticipo_adicional=payload.porcentaje_anticipo_adicional,
        usuario_id=payload.usuario_id,
        fecha_solicitud=payload.fecha_solicitud,
    )
    handler = ProcesarCambioAlcanceHandler(uow=uow)
    resultado = handler.handle(command)

    # Mensaje claro detallando cuántos invitados quedaron y cómo se actualizó la cuenta
    inv_ant = resultado.invitados_anteriores
    inv_act = resultado.invitados_actualizados
    extra_txt = f"${resultado.costo_adicional:,.2f} {payload.moneda}"
    tot_txt = f"${resultado.nuevo_monto_total_contrato:,.2f} {payload.moneda}"
    sal_txt = f"${resultado.nuevo_saldo_pendiente:,.2f} {payload.moneda}"
    return MensajeResponseSchema(
        message=(
            f"El cambio solicitado ('{payload.descripcion}') se aplicó con éxito. "
            f"El número de invitados pasó de {inv_ant} a {inv_act} personas "
            f"con un cargo adicional de {extra_txt}. "
            f"El nuevo total de su contrato es de {tot_txt} "
            f"y su saldo pendiente actualizado es de {sal_txt}."
        )
    )


@router.post(
    "/evaluar-sla-proveedores",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Revisar proveedores con plazo de confirmación de 48 horas vencido",
)
def evaluar_sla_proveedores(
    fecha_corte: Optional[datetime] = Body(default=None, embed=True),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """Revisa si algún proveedor tardó más de 48 horas en confirmar e informa el resultado claramente."""
    scheduler = EvaluarSLAProveedoresScheduler(uow=uow)
    resultado = scheduler.ejecutar(fecha_corte=fecha_corte)

    # Mensaje comprensible para el usuario sin mostrar listas de UUIDs ni códigos
    if resultado.total_asignaciones_vencidas > 0:
        texto = (
            f"Se revisaron los tiempos de respuesta de los proveedores y se detectó que "
            f"{resultado.total_asignaciones_vencidas} proveedor(es) no confirmaron dentro del plazo "
            "de 48 horas, por lo que su asignación fue marcada como vencida para que pueda elegir un reemplazo."
        )
    else:
        texto = (
            "Se revisaron los tiempos de respuesta de todos los proveedores y ninguno tiene "
            "el plazo de confirmación vencido."
        )
    return MensajeResponseSchema(message=texto)


@router.post(
    "/{evento_id}/proveedores/{proveedor_id}/confirmar",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Confirmar la asistencia de un proveedor asignado",
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def confirmar_proveedor_evento(
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    proveedor_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_PROVEEDOR_EJEMPLO)],
        description="Identificador del proveedor (en Swagger puede dejar el valor de ejemplo)",
    ),
    payload: Optional[ConfirmarProveedorRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """Confirma la asistencia de un proveedor dentro de las 48 horas e informa al usuario claramente."""
    evento_id_real = resolver_evento_id(evento_id)
    proveedor_id_real = resolver_proveedor_id(proveedor_id)
    datos = payload or ConfirmarProveedorRequest()
    ahora = datos.fecha_confirmacion or datetime.now(timezone.utc)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id_real)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id_real))

        asignacion = evento.confirmar_proveedor(proveedor_id=proveedor_id_real, fecha_confirmacion=ahora)

        log = LogAuditoria(
            entidad_id=asignacion.id,
            tipo_entidad="AsignacionProveedor",
            accion="CONFIRMACION_PROVEEDOR_BR04",
            estado_anterior="ASIGNADO",
            estado_nuevo=asignacion.estado.value,
            detalles={
                "evento_id": str(evento.id),
                "proveedor_id": str(asignacion.proveedor_id),
                "nombre_servicio": asignacion.nombre_servicio,
            },
            usuario_id=datos.usuario_id,
            fecha_registro=ahora,
        )

        uow.eventos.guardar(evento)
        uow.auditoria.registrar(log)
        uow.commit()

        # Mensaje sencillo confirmando qué servicio quedó confirmado
        return MensajeResponseSchema(
            message=(
                f"¡Excelente! El proveedor del servicio '{asignacion.nombre_servicio}' ha confirmado "
                "su participación en el evento a tiempo."
            )
        )


@router.post(
    "/{evento_id}/finalizar",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Concluir y cerrar el evento una vez liquidado en su totalidad",
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def finalizar_evento(
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    payload: Optional[FinalizarEventoRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Verifica que no exista ningún saldo pendiente y marca el evento como concluido,
    entregando un mensaje de cierre claro para el usuario.
    """
    evento_id_real = resolver_evento_id(evento_id)
    datos = payload or FinalizarEventoRequest()
    ahora = datetime.now(timezone.utc)

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

        estado_previo = evento.estado.value
        if evento.estado == EstadoEventoEnum.CONFIRMADO:
            evento.iniciar_ejecucion()
        evento.marcar_liquidado(cuenta_pagos=cuenta)

        log = LogAuditoria(
            entidad_id=evento.id,
            tipo_entidad="Evento",
            accion="CIERRE_LIQUIDACION_EVENTO_BR06",
            estado_anterior=estado_previo,
            estado_nuevo=evento.estado.value,
            detalles={
                "estado_pago": cuenta.estado_pago.value,
                "total_pagado": str(cuenta.monto_contractual.pagos_realizados.monto),
            },
            usuario_id=datos.usuario_id,
            fecha_registro=ahora,
        )

        uow.eventos.guardar(evento)
        uow.auditoria.registrar(log)
        uow.recolectar_eventos_dominio(evento.pull_domain_events())
        uow.commit()

        total_pagado = cuenta.monto_contractual.pagos_realizados.monto
        moneda = cuenta.monto_contractual.subtotal.moneda

        # Mensaje final claro confirmando la liquidación y cierre del evento
        return MensajeResponseSchema(
            message=(
                "¡El evento ha concluido y se ha cerrado exitosamente! "
                f"Se verificó que el total del contrato por ${total_pagado:,.2f} {moneda} "
                "fue pagado por completo sin dejar ningún saldo pendiente."
            )
        )


@router.post(
    "/{evento_id}/cancelar",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Cancelar el evento y conocer el reembolso aplicable",
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def cancelar_evento(
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    payload: Optional[CancelarEventoRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Cancela el evento e informa claramente al usuario si le corresponde reembolso
    de acuerdo con los pagos realizados y los días de anticipación.
    """
    evento_id_real = resolver_evento_id(evento_id)
    datos = payload or CancelarEventoRequest()
    ahora = datos.fecha_cancelacion or datetime.now(timezone.utc)

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

        estado_previo = evento.estado.value
        evento.cancelar()
        devolucion = cuenta.calcular_devolucion_cancelacion(
            fecha_cancelacion=ahora,
            fecha_evento=evento.fecha_evento,
        )

        log = LogAuditoria(
            entidad_id=evento.id,
            tipo_entidad="Evento",
            accion="CANCELACION_EVENTO_BR03",
            estado_anterior=estado_previo,
            estado_nuevo=evento.estado.value,
            detalles={
                "motivo": datos.motivo,
                "estado_pago_resultante": cuenta.estado_pago.value,
                "monto_devolucion": str(devolucion.monto),
            },
            usuario_id=datos.usuario_id,
            fecha_registro=ahora,
        )

        uow.eventos.guardar(evento)
        uow.cuentas_pagos.guardar(cuenta)
        uow.auditoria.registrar(log)
        uow.commit()

        mc = cuenta.monto_contractual
        moneda = mc.subtotal.moneda

        # Mensaje comprensible explicando el resultado de la cancelación y la devolución
        if devolucion.monto > 0:
            texto = (
                "Su evento ha sido cancelado conforme a su solicitud. "
                f"De los ${mc.pagos_realizados.monto:,.2f} {moneda} abonados hasta la fecha, "
                f"se retiene el anticipo base de ${mc.anticipo_pactado.monto:,.2f} {moneda} y le "
                f"corresponde una devolución a su favor por ${devolucion.monto:,.2f} {moneda}."
            )
        else:
            texto = (
                "Su evento ha sido cancelado conforme a su solicitud. "
                "De acuerdo con la política de cancelación y los pagos registrados hasta el momento, "
                "no existe saldo adicional sujeto a reembolso."
            )
        return MensajeResponseSchema(message=texto)
