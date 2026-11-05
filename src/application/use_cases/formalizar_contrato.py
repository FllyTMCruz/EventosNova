# src/application/use_cases/formalizar_contrato.py
from datetime import datetime, timezone
from src.application.dtos.comandos import (
    ContratoFormalizadoDTO,
    FormalizarContratoCommand,
)
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.models.auditoria import LogAuditoria
from src.domain.repositories.interfaces import IUnitOfWork


class FormalizarContratoHandler:
    """
    Caso de Uso CU-03: Formalizar Contrato (Regla de Negocio BR-07).
    Orquesta la validación de las 4 condiciones de formalización, ejecuta la transición
    de estado en el Aggregate Evento, persiste el registro inmutable de auditoría (ADR-003)
    y publica el evento ContratoFormalizadoEvent.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    def handle(self, command: FormalizarContratoCommand) -> ContratoFormalizadoDTO:
        ahora = command.fecha_operacion or datetime.now(timezone.utc)

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

            estado_previo = evento.estado.value

            # Ejecuta la lógica de dominio y verifica FormalizacionContratoSpecification (BR-07)
            evento.formalizar_contrato(cuenta_pagos=cuenta_pagos, fecha_actual=ahora)

            # Registro de auditoría inmutable (ADR-003)
            log_auditoria = LogAuditoria(
                entidad_id=evento.id,
                tipo_entidad="Evento",
                accion="FORMALIZACION_CONTRATO_BR07",
                estado_anterior=estado_previo,
                estado_nuevo=evento.estado.value,
                detalles={
                    "cliente_id": str(evento.cliente_id),
                    "cantidad_invitados": evento.cantidad_invitados,
                    "monto_total_pactado": str(cuenta_pagos.monto_contractual.monto_total_actualizado.monto),
                    "anticipo_cubierto": str(cuenta_pagos.monto_contractual.pagos_realizados.monto),
                },
                usuario_id=command.usuario_id,
                fecha_registro=ahora,
            )

            self._uow.eventos.guardar(evento)
            self._uow.auditoria.registrar(log_auditoria)
            self._uow.recolectar_eventos_dominio(evento.pull_domain_events())
            self._uow.commit()

            return ContratoFormalizadoDTO(
                evento_id=evento.id,
                estado_anterior=estado_previo,
                estado_actual=evento.estado.value,
                monto_total_contrato=cuenta_pagos.monto_contractual.monto_total_actualizado.monto,
                saldo_pendiente=cuenta_pagos.monto_contractual.calcular_saldo_pendiente().monto,
                moneda=cuenta_pagos.monto_contractual.subtotal.moneda,
                auditoria_id=log_auditoria.id,
            )
