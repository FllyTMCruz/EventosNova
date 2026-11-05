# src/domain/value_objects/rango_fechas.py
from dataclasses import dataclass
from datetime import datetime
from src.domain.exceptions import ReglaNegocioException


@dataclass(frozen=True)
class RangoFechas:
    """Value Object inmutable que garantiza la coherencia temporal entre dos fechas."""

    fecha_inicio: datetime
    fecha_fin: datetime

    def __post_init__(self) -> None:
        if self.fecha_fin < self.fecha_inicio:
            raise ReglaNegocioException(
                f"La fecha fin ({self.fecha_fin.isoformat()}) no puede ser anterior "
                f"a la fecha inicio ({self.fecha_inicio.isoformat()})."
            )

    @property
    def diferencia_dias_naturales(self) -> int:
        """Retorna el número de días naturales completos entre inicio y fin."""
        delta = self.fecha_fin.date() - self.fecha_inicio.date()
        return delta.days

    @property
    def diferencia_horas(self) -> float:
        """Retorna el total de horas exactas entre la fecha de inicio y fin."""
        delta = self.fecha_fin - self.fecha_inicio
        return delta.total_seconds() / 3600.0

    def contiene(self, fecha_evaluar: datetime) -> bool:
        """Verifica si una fecha se encuentra dentro del rango inclusivo."""
        return self.fecha_inicio <= fecha_evaluar <= self.fecha_fin
