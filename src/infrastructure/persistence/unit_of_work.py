# src/infrastructure/persistence/unit_of_work.py
from types import TracebackType
from typing import Callable, Dict, List, Optional, Type
from sqlalchemy.orm import Session, sessionmaker
from src.domain.events import DomainEvent
from src.domain.repositories.interfaces import IUnitOfWork
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.persistence.repositories import (
    SqlAlchemyCuentaDePagosRepository,
    SqlAlchemyEventoRepository,
    SqlAlchemyRegistroAuditoriaRepository,
)

EventHandlerCallable = Callable[[DomainEvent], None]


class InMemoryDomainEventBus:
    """Despachador síncrono en memoria para eventos de dominio."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[DomainEvent], List[EventHandlerCallable]] = {}
        self._published_events_history: List[DomainEvent] = []

    def suscribir(
        self,
        event_type: Type[DomainEvent],
        handler: EventHandlerCallable,
    ) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publicar(self, evento: DomainEvent) -> None:
        self._published_events_history.append(evento)
        handlers = self._subscribers.get(type(evento), [])
        for handler in handlers:
            handler(evento)

    @property
    def historial_publicados(self) -> List[DomainEvent]:
        return list(self._published_events_history)


default_event_bus = InMemoryDomainEventBus()


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """
    Implementación concreta de IUnitOfWork basada en sesiones de SQLAlchemy.
    Garantiza atomicidad entre Evento, CuentaDePagos y LogAuditoria (ADR-003).
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        event_bus: Optional[InMemoryDomainEventBus] = None,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus or default_event_bus
        self._session: Optional[Session] = None
        self._eventos_pendientes: List[DomainEvent] = []

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.eventos = SqlAlchemyEventoRepository(self._session)
        self.cuentas_pagos = SqlAlchemyCuentaDePagosRepository(self._session)
        self.auditoria = SqlAlchemyRegistroAuditoriaRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("No existe una sesión activa en el Unit of Work.")
        self._session.commit()

        eventos_a_despachar = list(self._eventos_pendientes)
        self._eventos_pendientes.clear()
        for evento_dominio in eventos_a_despachar:
            self._event_bus.publicar(evento_dominio)

    def rollback(self) -> None:
        if self._session is not None:
            self._session.rollback()
        self._eventos_pendientes.clear()

    def recolectar_eventos_dominio(self, eventos: List[DomainEvent]) -> None:
        self._eventos_pendientes.extend(eventos)
