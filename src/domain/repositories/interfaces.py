# src/domain/repositories/interfaces.py
from abc import ABC, abstractmethod
from types import TracebackType
from typing import List, Optional, Type
from uuid import UUID
from src.domain.events import DomainEvent
from src.domain.models.auditoria import LogAuditoria
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import Evento


class IEventoRepository(ABC):
    """Puerto de repositorio para la persistencia del Aggregate Root Evento."""

    @abstractmethod
    def obtener_por_id(self, evento_id: UUID) -> Optional[Evento]:
        raise NotImplementedError("Debe implementarse obtener_por_id en el adaptador.")

    @abstractmethod
    def guardar(self, evento: Evento) -> None:
        raise NotImplementedError("Debe implementarse guardar en el adaptador.")

    @abstractmethod
    def listar_con_proveedores_pendientes_sla(self) -> List[Evento]:
        """Obtiene los eventos activos que tienen asignaciones en estado ASIGNADO."""
        raise NotImplementedError("Debe implementarse listar_con_proveedores_pendientes_sla.")


class ICuentaDePagosRepository(ABC):
    """Puerto de repositorio para la persistencia del Aggregate Root CuentaDePagos."""

    @abstractmethod
    def obtener_por_id(self, cuenta_id: UUID) -> Optional[CuentaDePagos]:
        raise NotImplementedError("Debe implementarse obtener_por_id en el adaptador.")

    @abstractmethod
    def obtener_por_evento_id(self, evento_id: UUID) -> Optional[CuentaDePagos]:
        raise NotImplementedError("Debe implementarse obtener_por_evento_id en el adaptador.")

    @abstractmethod
    def guardar(self, cuenta: CuentaDePagos) -> None:
        raise NotImplementedError("Debe implementarse guardar en el adaptador.")


class IRegistroAuditoriaRepository(ABC):
    """
    Puerto de repositorio para el historial de auditoría inmutable (ADR-003).
    Exclusivamente append-only (sin métodos de actualización ni borrado).
    """

    @abstractmethod
    def registrar(self, log: LogAuditoria) -> None:
        raise NotImplementedError("Debe implementarse registrar en el adaptador.")

    @abstractmethod
    def listar_por_entidad(self, entidad_id: UUID) -> List[LogAuditoria]:
        raise NotImplementedError("Debe implementarse listar_por_entidad en el adaptador.")


class IUnitOfWork(ABC):
    """
    Puerto de Unidad de Trabajo (Unit of Work) para garantizar atomicidad transaccional
    entre los Aggregates (Evento, CuentaDePagos), los registros de auditoría (ADR-003)
    y el despacho de eventos de dominio en memoria.
    """

    eventos: IEventoRepository
    cuentas_pagos: ICuentaDePagosRepository
    auditoria: IRegistroAuditoriaRepository

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork":
        raise NotImplementedError("Debe implementarse __enter__ en el Unit of Work.")

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        raise NotImplementedError("Debe implementarse __exit__ en el Unit of Work.")

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError("Debe implementarse commit en el Unit of Work.")

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError("Debe implementarse rollback en el Unit of Work.")

    @abstractmethod
    def recolectar_eventos_dominio(self, eventos: List[DomainEvent]) -> None:
        raise NotImplementedError("Debe implementarse recolectar_eventos_dominio.")
