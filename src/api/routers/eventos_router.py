# src/api/routers/eventos_router.py
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Body, Depends, status
from src.api.dependencies import get_uow
from src.api.schemas import (
    AsignacionProveedorResponseSchema,
    AsignarProveedorRequest,
    CambioAlcanceResponseSchema,
    CancelarEventoRequest,
    CancelarEventoResponseSchema,
    ConfirmarProveedorRequest,
    CrearEventoPreliminarRequest,
    ErrorResponseSchema,
    EventoPreliminarResponseSchema,
    FinalizarEventoRequest,
    FinalizarEventoResponseSchema,
    FormalizarContratoRequest,
    FormalizarContratoResponseSchema,
    SolicitarCambioAlcanceRequest,
)
from src.application.dtos.comandos import (
    FormalizarContratoCommand,
    ProcesarCambioAlcanceCommand,
)
from src.application.dtos.consultas import ResultadoEvaluacionSLADTO
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


@router.post(
    "",
    response_model=EventoPreliminarResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear evento preliminar y cuenta de pagos inicial",
    responses={
        400: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def crear_evento_preliminar(
    payload: CrearEventoPreliminarRequest,
    uow: IUnitOfWork = Depends(get_uow),
) -> EventoPreliminarResponseSchema:
    """
    Crea un nuevo Aggregate Root `Evento` en estado `PENDIENTE_ANTICIPO`, valida la capacidad
    de invitados (BR-05: 20 a 300), asigna proveedores iniciales (BR-15: máx. 15),
    inicializa su `CuentaDePagos` y registra la creación en la bitácora de auditoría (ADR-003).
    """
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

        return EventoPreliminarResponseSchema(
            evento_id=evento.id,
            cuenta_pagos_id=cuenta_pagos.id,
            cliente_id=evento.cliente_id,
            fecha_evento=evento.fecha_evento,
            cantidad_invitados=evento.cantidad_invitados,
            estado_evento=evento.estado.value,
            estado_pago=cuenta_pagos.estado_pago.value,
            subtotal_contrato=monto_vo.subtotal.monto,
            anticipo_pactado=monto_vo.anticipo_pactado.monto,
            saldo_pendiente=monto_vo.calcular_saldo_pendiente().monto,
            moneda=moneda,
            proveedores=[
                AsignacionProveedorResponseSchema(
                    id=a.id,
                    proveedor_id=a.proveedor_id,
                    nombre_servicio=a.nombre_servicio,
                    estado=a.estado.value,
                    fecha_asignacion=a.fecha_asignacion,
                    fecha_limite_confirmacion=a.fecha_limite_confirmacion,
                )
                for a in evento.asignaciones_proveedores
            ],
            auditoria_id=log_auditoria.id,
        )


@router.post(
    "/{evento_id}/proveedores",
    response_model=AsignacionProveedorResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar un proveedor al evento (BR-04 / BR-15)",
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def asignar_proveedor_evento(
    evento_id: UUID,
    payload: AsignarProveedorRequest,
    uow: IUnitOfWork = Depends(get_uow),
) -> AsignacionProveedorResponseSchema:
    """Asigna un proveedor validando el límite de 15 proveedores activos (BR-15) y el SLA de 48h (BR-04)."""
    ahora = datetime.now(timezone.utc)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id))

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

        return AsignacionProveedorResponseSchema(
            id=asignacion.id,
            proveedor_id=asignacion.proveedor_id,
            nombre_servicio=asignacion.nombre_servicio,
            estado=asignacion.estado.value,
            fecha_asignacion=asignacion.fecha_asignacion,
            fecha_limite_confirmacion=asignacion.fecha_limite_confirmacion,
        )


@router.post(
    "/{evento_id}/formalizar",
    response_model=FormalizarContratoResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Formalizar contrato del evento (CU-03 / BR-07)",
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def formalizar_contrato(
    evento_id: UUID,
    payload: Optional[FormalizarContratoRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> FormalizarContratoResponseSchema:
    """
    Ejecuta el Caso de Uso CU-03 (`FormalizarContratoHandler`).
    Verifica las 4 condiciones de `FormalizacionContratoSpecification` (BR-07):
    1. Estado `BORRADOR` o `PENDIENTE_ANTICIPO` y fecha futura.
    2. Capacidad entre 20 y 300 invitados (BR-05).
    3. Al menos 1 proveedor `CONFIRMADO`, sin pendientes y máximo 15 activos (BR-15).
    4. Anticipo mínimo pactado cubierto en `CuentaDePagos`.
    """
    datos = payload or FormalizarContratoRequest()
    command = FormalizarContratoCommand(
        evento_id=evento_id,
        usuario_id=datos.usuario_id,
        fecha_operacion=datos.fecha_operacion,
    )
    handler = FormalizarContratoHandler(uow=uow)
    resultado = handler.handle(command)

    return FormalizarContratoResponseSchema(
        evento_id=resultado.evento_id,
        estado_anterior=resultado.estado_anterior,
        estado_actual=resultado.estado_actual,
        monto_total_contrato=resultado.monto_total_contrato,
        saldo_pendiente=resultado.saldo_pendiente,
        moneda=resultado.moneda,
        auditoria_id=resultado.auditoria_id,
    )


@router.post(
    "/{evento_id}/cambios-alcance",
    response_model=CambioAlcanceResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Solicitar y procesar cambio de alcance (CU-04 / BR-02, BR-05, BR-12)",
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def solicitar_cambio_alcance(
    evento_id: UUID,
    payload: SolicitarCambioAlcanceRequest,
    uow: IUnitOfWork = Depends(get_uow),
) -> CambioAlcanceResponseSchema:
    """
    Ejecuta el Caso de Uso CU-04 (`ProcesarCambioAlcanceHandler`).
    Valida que el evento esté `CONFIRMADO`, que falten al menos 7 días naturales para la fecha
    del evento (BR-02 / BR-12) y que el nuevo total de invitados no supere los 300 (BR-05).
    """
    command = ProcesarCambioAlcanceCommand(
        evento_id=evento_id,
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

    return CambioAlcanceResponseSchema(
        evento_id=resultado.evento_id,
        cotizacion_id=resultado.cotizacion_id,
        invitados_anteriores=resultado.invitados_anteriores,
        invitados_actualizados=resultado.invitados_actualizados,
        costo_adicional=resultado.costo_adicional,
        nuevo_monto_total_contrato=resultado.nuevo_monto_total_contrato,
        nuevo_saldo_pendiente=resultado.nuevo_saldo_pendiente,
        estado_pago_actualizado=resultado.estado_pago_actualizado,
        auditoria_id=resultado.auditoria_id,
    )


@router.post(
    "/evaluar-sla-proveedores",
    response_model=ResultadoEvaluacionSLADTO,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar evaluación de SLA de 48h para proveedores pendientes (BR-04)",
)
def evaluar_sla_proveedores(
    fecha_corte: Optional[datetime] = Body(default=None, embed=True),
    uow: IUnitOfWork = Depends(get_uow),
) -> ResultadoEvaluacionSLADTO:
    """Ejecuta el scheduler de dominio que vence asignaciones con más de 48h sin confirmar (BR-04)."""
    scheduler = EvaluarSLAProveedoresScheduler(uow=uow)
    return scheduler.ejecutar(fecha_corte=fecha_corte)


@router.post(
    "/{evento_id}/proveedores/{proveedor_id}/confirmar",
    response_model=AsignacionProveedorResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Confirmar participación de un proveedor dentro del SLA de 48h (US-04 / BR-04)",
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
        422: {"model": ErrorResponseSchema},
    },
)
def confirmar_proveedor_evento(
    evento_id: UUID,
    proveedor_id: UUID,
    payload: Optional[ConfirmarProveedorRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> AsignacionProveedorResponseSchema:
    """Confirma un proveedor asignado validando que no haya expirado la ventana SLA de 48 horas (BR-04)."""
    datos = payload or ConfirmarProveedorRequest()
    ahora = datos.fecha_confirmacion or datetime.now(timezone.utc)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id))

        asignacion = evento.confirmar_proveedor(proveedor_id=proveedor_id, fecha_confirmacion=ahora)

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

        return AsignacionProveedorResponseSchema(
            id=asignacion.id,
            proveedor_id=asignacion.proveedor_id,
            nombre_servicio=asignacion.nombre_servicio,
            estado=asignacion.estado.value,
            fecha_asignacion=asignacion.fecha_asignacion,
            fecha_limite_confirmacion=asignacion.fecha_limite_confirmacion,
        )


@router.post(
    "/{evento_id}/finalizar",
    response_model=FinalizarEventoResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar y finalizar evento verificando liquidación total (US-08, US-15 / BR-06)",
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def finalizar_evento(
    evento_id: UUID,
    payload: Optional[FinalizarEventoRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> FinalizarEventoResponseSchema:
    """
    Valida que la CuentaDePagos esté 100% liquidada (saldo 0.00 MXN, BR-06) y transiciona
    el evento a través de `EN_EJECUCION` hasta el estado terminal `FINALIZADO`.
    """
    datos = payload or FinalizarEventoRequest()
    ahora = datetime.now(timezone.utc)

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

        return FinalizarEventoResponseSchema(
            evento_id=evento.id,
            estado_anterior=estado_previo,
            estado_actual=evento.estado.value,
            estado_pago=cuenta.estado_pago.value,
            total_pagado=cuenta.monto_contractual.pagos_realizados.monto,
            moneda=cuenta.monto_contractual.subtotal.moneda,
            auditoria_id=log.id,
        )


@router.post(
    "/{evento_id}/cancelar",
    response_model=CancelarEventoResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Cancelar evento y calcular devolución por penalización (US-09 / BR-03)",
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def cancelar_evento(
    evento_id: UUID,
    payload: Optional[CancelarEventoRequest] = Body(default=None),
    uow: IUnitOfWork = Depends(get_uow),
) -> CancelarEventoResponseSchema:
    """
    Cancela un evento (BR-03 / US-09) y calcula automáticamente el monto de reembolso según
    los días naturales de anticipación (>30 días: 100% sobre excedente de anticipo;
    15 a 30 días: 50% sobre excedente de anticipo; <15 días: 0% sin reembolso).
    """
    datos = payload or CancelarEventoRequest()
    ahora = datos.fecha_cancelacion or datetime.now(timezone.utc)

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
        return CancelarEventoResponseSchema(
            evento_id=evento.id,
            estado_evento_anterior=estado_previo,
            estado_evento_actual=evento.estado.value,
            estado_pago_actual=cuenta.estado_pago.value,
            pagos_realizados=mc.pagos_realizados.monto,
            anticipo_retenido=mc.anticipo_pactado.monto,
            monto_devolucion=devolucion.monto,
            moneda=mc.subtotal.moneda,
            auditoria_id=log.id,
        )
