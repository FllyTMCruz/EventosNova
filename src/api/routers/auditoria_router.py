# src/api/routers/auditoria_router.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from src.api.dependencies import get_uow
from src.api.schemas import (
    ErrorResponseSchema,
    HistorialAuditoriaResponseSchema,
    LogAuditoriaResponseSchema,
)
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.models.auditoria import LogAuditoria
from src.domain.repositories.interfaces import IUnitOfWork
from src.infrastructure.persistence.repositories import (
    SqlAlchemyRegistroAuditoriaRepository,
)

router = APIRouter(prefix="/eventos", tags=["Historial de Auditoría (ADR-003)"])


@router.get(
    "/{evento_id}/auditoria",
    response_model=HistorialAuditoriaResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar historial inmutable de cambios y auditoría del evento (ADR-003)",
    responses={
        404: {"model": ErrorResponseSchema},
    },
)
def consultar_historial_auditoria(
    evento_id: UUID,
    uow: IUnitOfWork = Depends(get_uow),
) -> HistorialAuditoriaResponseSchema:
    """
    Recupera todos los registros inmutables (`LogAuditoria`) asociados al ciclo de vida
    del evento, incluyendo cambios de estado, formalización, modificaciones de alcance,
    pagos y vencimientos de SLA.
    """
    with uow:
        evento = uow.eventos.obtener_por_id(evento_id)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id))

        if isinstance(uow.auditoria, SqlAlchemyRegistroAuditoriaRepository):
            logs: List[LogAuditoria] = uow.auditoria.listar_historial_completo_evento(evento_id)
        else:
            logs = uow.auditoria.listar_por_entidad(evento_id)

        registros_schema = [
            LogAuditoriaResponseSchema(
                id=log.id,
                entidad_id=log.entidad_id,
                tipo_entidad=log.tipo_entidad,
                accion=log.accion,
                estado_anterior=log.estado_anterior,
                estado_nuevo=log.estado_nuevo,
                detalles=log.detalles,
                usuario_id=log.usuario_id,
                fecha_registro=log.fecha_registro,
            )
            for log in logs
        ]

        return HistorialAuditoriaResponseSchema(
            evento_id=evento_id,
            total_registros=len(registros_schema),
            registros=registros_schema,
        )
