# src/domain/models/auditoria.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from src.domain.exceptions import ReglaNegocioException


@dataclass(frozen=True)
class LogAuditoria:
    """
    Entidad inmutable para el Historial de Auditoría (ADR-003).
    Garantiza trazabilidad append-only en cada cambio de estado o modificación de alcance.
    """

    entidad_id: UUID
    tipo_entidad: str
    accion: str
    estado_anterior: Optional[str]
    estado_nuevo: str
    detalles: Dict[str, Any] = field(default_factory=dict)
    usuario_id: Optional[UUID] = None
    id: UUID = field(default_factory=uuid4)
    fecha_registro: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.tipo_entidad or not self.tipo_entidad.strip():
            raise ReglaNegocioException("El tipo de entidad en el registro de auditoría es obligatorio.")
        if not self.accion or not self.accion.strip():
            raise ReglaNegocioException("La acción en el registro de auditoría es obligatoria.")
        if not self.estado_nuevo or not self.estado_nuevo.strip():
            raise ReglaNegocioException("El estado nuevo en el registro de auditoría es obligatorio.")
