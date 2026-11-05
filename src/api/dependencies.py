# src/api/dependencies.py
from src.domain.repositories.interfaces import IUnitOfWork
from src.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def get_uow() -> IUnitOfWork:
    """Proveedor de dependencia para inyectar el Unit of Work en los endpoints."""
    return SqlAlchemyUnitOfWork()
