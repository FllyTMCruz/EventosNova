# src/application/use_cases/evaluar_sla_proveedores.py
from datetime import datetime, timezone
from typing import List, Optional
from src.application.dtos.consultas import (
    ProveedorVencidoDTO,
    ResultadoEvaluacionSLADTO,
)
from src.domain.models.auditoria import LogAuditoria
from src.domain.repositories.interfaces import IUnitOfWork
from src.domain.state_machine.estado_asignacion_proveedor import (
    EstadoAsignacionProveedorEnum,
)


class EvaluarSLAProveedoresScheduler:
    """
    Servicio de Aplicación / Job Programado para la Regla de Negocio BR-04:
    Inspecciona los eventos con asignaciones pendientes y transiciona a VENCIDO
    aquellas que hayan superado las 48 horas desde su asignación, registrando
    cada transición en la bitácora inmutable de auditoría (ADR-003).
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    def ejecutar(self, fecha_corte: Optional[datetime] = None) -> ResultadoEvaluacionSLADTO:
        ahora = fecha_corte or datetime.now(timezone.utc)
        vencidos_dto: List[ProveedorVencidoDTO] = []

        with self._uow:
            eventos = self._uow.eventos.listar_con_proveedores_pendientes_sla()

            for evento in eventos:
                asignaciones_vencidas = evento.evaluar_sla_proveedores(fecha_corte=ahora)
                if asignaciones_vencidas:
                    self._uow.eventos.guardar(evento)
                    self._uow.recolectar_eventos_dominio(evento.pull_domain_events())

                    for asig in asignaciones_vencidas:
                        log = LogAuditoria(
                            entidad_id=asig.id,
                            tipo_entidad="AsignacionProveedor",
                            accion="VENCIMIENTO_SLA_48H_BR04",
                            estado_anterior=EstadoAsignacionProveedorEnum.ASIGNADO.value,
                            estado_nuevo=asig.estado.value,
                            detalles={
                                "evento_id": str(evento.id),
                                "proveedor_id": str(asig.proveedor_id),
                                "nombre_servicio": asig.nombre_servicio,
                                "fecha_limite_confirmacion": asig.fecha_limite_confirmacion.isoformat(),
                            },
                            usuario_id=None,
                            fecha_registro=ahora,
                        )
                        self._uow.auditoria.registrar(log)
                        vencidos_dto.append(
                            ProveedorVencidoDTO(
                                evento_id=evento.id,
                                asignacion_id=asig.id,
                                proveedor_id=asig.proveedor_id,
                                nombre_servicio=asig.nombre_servicio,
                                fecha_limite_confirmacion=asig.fecha_limite_confirmacion.isoformat(),
                            )
                        )

            self._uow.commit()

        return ResultadoEvaluacionSLADTO(
            fecha_corte=ahora.isoformat(),
            eventos_evaluados=len(eventos),
            total_asignaciones_vencidas=len(vencidos_dto),
            proveedores_vencidos=vencidos_dto,
        )
