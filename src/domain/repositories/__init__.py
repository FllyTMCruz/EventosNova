# src/domain/repositories/__init__.py
from src.domain.repositories.interfaces import (
    IEventoRepository,
    ICuentaDePagosRepository,
    IRegistroAuditoriaRepository,
    IUnitOfWork,
)

__all__ = [
    "IEventoRepository",
    "ICuentaDePagosRepository",
    "IRegistroAuditoriaRepository",
    "IUnitOfWork",
]
