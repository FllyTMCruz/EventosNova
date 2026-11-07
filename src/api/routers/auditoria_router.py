# src/api/routers/auditoria_router.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Path, status
from src.api.dependencies import get_uow
from src.api.routers.eventos_router import SWAGGER_EVENTO_EJEMPLO, resolver_evento_id
from src.api.schemas import ErrorResponseSchema, MensajeResponseSchema
from src.domain.exceptions import EntidadNoEncontradaException
from src.domain.models.auditoria import LogAuditoria
from src.domain.repositories.interfaces import IUnitOfWork
from src.infrastructure.persistence.repositories import (
    SqlAlchemyRegistroAuditoriaRepository,
)

router = APIRouter(prefix="/eventos", tags=["Historial del Evento"])

# Descripción en lenguaje natural de cada movimiento registrado en la bitácora
_DESCRIPCIONES_ACCIONES = {
    "CREACION_EVENTO_PRELIMINAR": "Registro inicial del evento y cotización base",
    "REGISTRO_PAGO": "Pago o abono registrado en la cuenta del evento",
    "FORMALIZACION_CONTRATO_BR07": "Formalización y confirmación oficial del contrato",
    "CAMBIO_ALCANCE_BR02_BR12": "Ampliación de invitados o servicios adicionales",
    "ASIGNACION_PROVEEDOR_BR15": "Asignación de un nuevo proveedor de servicios",
    "CONFIRMACION_PROVEEDOR_BR04": "Confirmación de asistencia por parte de un proveedor",
    "VENCIMIENTO_SLA_PROVEEDOR_BR04": "Vencimiento del plazo de 48 horas de un proveedor sin respuesta",
    "VENCIMIENTO_SLA_48H_BR04": "Vencimiento del plazo de 48 horas de un proveedor sin respuesta",
    "CIERRE_LIQUIDACION_EVENTO_BR06": "Liquidación total y cierre exitoso del evento",
    "CANCELACION_EVENTO_BR03": "Cancelación del evento y cálculo de devolución",
}


@router.get(
    "/{evento_id}/auditoria",
    response_model=MensajeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar el historial de movimientos realizados en el evento",
    responses={
        404: {"model": ErrorResponseSchema},
    },
)
def consultar_historial_auditoria(
    evento_id: UUID = Path(
        ...,
        examples=[str(SWAGGER_EVENTO_EJEMPLO)],
        description="Identificador del evento (en Swagger puede dejar el valor de ejemplo)",
    ),
    uow: IUnitOfWork = Depends(get_uow),
) -> MensajeResponseSchema:
    """
    Entrega un resumen claro y cronológico de todos los movimientos realizados
    en el evento, sin mostrar identificadores internos ni códigos técnicos.
    """
    evento_id_real = resolver_evento_id(evento_id)

    with uow:
        evento = uow.eventos.obtener_por_id(evento_id_real)
        if evento is None:
            raise EntidadNoEncontradaException(tipo_entidad="Evento", identificador=str(evento_id_real))

        if isinstance(uow.auditoria, SqlAlchemyRegistroAuditoriaRepository):
            logs: List[LogAuditoria] = uow.auditoria.listar_historial_completo_evento(evento_id_real)
        else:
            logs = uow.auditoria.listar_por_entidad(evento_id_real)

        if not logs:
            return MensajeResponseSchema(message="Aún no se han registrado movimientos en el historial de este evento.")

        # Arma una lista numerada y fácil de leer para el usuario común
        pasos_legibles = []
        for idx, log in enumerate(logs, start=1):
            desc = _DESCRIPCIONES_ACCIONES.get(log.accion, "Actualización registrada en el evento")
            pasos_legibles.append(f"{idx}) {desc}")

        resumen_pasos = "; ".join(pasos_legibles)
        return MensajeResponseSchema(
            message=(
                f"Historial del evento ({len(logs)} movimiento(s) registrados en orden cronológico): "
                f"{resumen_pasos}."
            )
        )
