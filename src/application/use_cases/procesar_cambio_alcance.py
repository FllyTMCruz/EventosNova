# src/application/use_cases/procesar_cambio_alcance.py
from datetime import datetime, timezone
from src.application.dtos.comandos import (
    CambioAlcanceProcesadoDTO,
    ProcesarCambioAlcanceCommand,
)
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.models.auditoria import LogAuditoria
from src.domain.repositories.interfaces import IUnitOfWork
from src.domain.value_objects.dinero import Dinero


class ProcesarCambioAlcanceHandler:
    """
    Caso de Uso CU-04: Procesar Cambio de Alcance (Reglas BR-02, BR-05 y BR-12).
    Valida el plazo mínimo de 7 días naturales y el tope de 300 invitados en el Aggregate Evento,
    actualiza el monto contractual en el Aggregate CuentaDePagos y registra la auditoría (ADR-003).
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    def handle(self, command: ProcesarCambioAlcanceCommand) -> CambioAlcanceProcesadoDTO:
        ahora = command.fecha_solicitud or datetime.now(timezone.utc)
        costo_incremento = Dinero(monto=command.costo_adicional, moneda=command.moneda)

        with self._uow:
            evento = self._uow.eventos.obtener_por_id(command.evento_id)
            if evento is None:
                raise EntidadNoEncontradaException(
                    tipo_entidad="Evento",
                    identificador=str(command.evento_id),
                )

            cuenta_pagos = self._uow.cuentas_pagos.obtener_por_evento_id(command.evento_id)
            if cuenta_pagos is None:
                raise EntidadNoEncontradaException(
                    tipo_entidad="CuentaDePagos para Evento",
                    identificador=str(command.evento_id),
                )

            invitados_previos = evento.cantidad_invitados

            # 1. Aplicar cambio de alcance en el Aggregate Operativo (valida BR-02, BR-05, BR-12)
            cotizacion = evento.solicitar_cambio_alcance(
                descripcion=command.descripcion,
                invitados_adicionales=command.invitados_adicionales,
                costo_adicional=costo_incremento,
                fecha_solicitud=ahora,
                aprobar_inmediatamente=True,
            )

            # 2. Actualizar el Aggregate Financiero con el incremento aprobado
            nuevo_saldo = cuenta_pagos.registrar_incremento_alcance(
                costo_adicional=costo_incremento,
                porcentaje_anticipo_adicional=command.porcentaje_anticipo_adicional,
            )

            # 3. Registrar en el historial de auditoría inmutable (ADR-003)
            log_auditoria = LogAuditoria(
                entidad_id=evento.id,
                tipo_entidad="Evento",
                accion="CAMBIO_ALCANCE_BR02_BR12",
                estado_anterior=evento.estado.value,
                estado_nuevo=evento.estado.value,
                detalles={
                    "cotizacion_id": str(cotizacion.id),
                    "descripcion": cotizacion.descripcion,
                    "invitados_anteriores": invitados_previos,
                    "invitados_nuevos": evento.cantidad_invitados,
                    "costo_adicional": str(costo_incremento.monto),
                    "nuevo_total_contrato": str(cuenta_pagos.monto_contractual.monto_total_actualizado.monto),
                    "nuevo_saldo_pendiente": str(nuevo_saldo.monto),
                },
                usuario_id=command.usuario_id,
                fecha_registro=ahora,
            )

            self._uow.eventos.guardar(evento)
            self._uow.cuentas_pagos.guardar(cuenta_pagos)
            self._uow.auditoria.registrar(log_auditoria)
            self._uow.recolectar_eventos_dominio(evento.pull_domain_events())
            self._uow.recolectar_eventos_dominio(cuenta_pagos.pull_domain_events())
            self._uow.commit()

            return CambioAlcanceProcesadoDTO(
                evento_id=evento.id,
                cotizacion_id=cotizacion.id,
                invitados_anteriores=invitados_previos,
                invitados_actualizados=evento.cantidad_invitados,
                costo_adicional=costo_incremento.monto,
                nuevo_monto_total_contrato=cuenta_pagos.monto_contractual.monto_total_actualizado.monto,
                nuevo_saldo_pendiente=nuevo_saldo.monto,
                estado_pago_actualizado=cuenta_pagos.estado_pago.value,
                auditoria_id=log_auditoria.id,
            )
