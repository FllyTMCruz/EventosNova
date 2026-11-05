# tests/conftest.py
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from src.api.dependencies import get_uow
from src.api.main import app
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import Evento
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.domain.value_objects.dinero import Dinero
from src.domain.value_objects.monto_contractual import MontoContractual
from src.infrastructure.config.database import Base, construir_engine, init_db
from src.infrastructure.persistence.unit_of_work import (
    InMemoryDomainEventBus,
    SqlAlchemyUnitOfWork,
)


@pytest.fixture(scope="function")
def sqlite_memory_engine() -> Generator[Engine, None, None]:
    """Crea un motor SQLite en memoria aislado para cada función de prueba."""
    engine = construir_engine("sqlite:///:memory:")
    init_db(target_engine=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def session_factory(sqlite_memory_engine: Engine) -> sessionmaker[Session]:
    """Fábrica de sesiones SQLAlchemy vinculada al motor SQLite en memoria."""
    return sessionmaker(
        bind=sqlite_memory_engine,
        class_=Session,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture(scope="function")
def event_bus() -> InMemoryDomainEventBus:
    """Bus de eventos en memoria limpio por cada prueba."""
    return InMemoryDomainEventBus()


@pytest.fixture(scope="function")
def uow(
    session_factory: sessionmaker[Session],
    event_bus: InMemoryDomainEventBus,
) -> SqlAlchemyUnitOfWork:
    """Instancia de Unit of Work configurada con SQLite en memoria."""
    return SqlAlchemyUnitOfWork(session_factory=session_factory, event_bus=event_bus)


@pytest.fixture(scope="function")
def client(
    session_factory: sessionmaker[Session],
    event_bus: InMemoryDomainEventBus,
) -> Generator[TestClient, None, None]:
    """Cliente de pruebas FastAPI con sobreescritura de dependencia get_uow."""

    def _override_get_uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory=session_factory, event_bus=event_bus)

    app.dependency_overrides[get_uow] = _override_get_uow
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fecha_base_utc() -> datetime:
    """Fecha de referencia determinista en UTC."""
    return datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def evento_preliminar_valido(fecha_base_utc: datetime) -> Evento:
    """Retorna un Aggregate Evento en estado PENDIENTE_ANTICIPO con 1 proveedor confirmado."""
    evento = Evento(
        cliente_id=uuid4(),
        fecha_evento=fecha_base_utc + timedelta(days=30),
        cantidad_invitados=120,
        estado=EstadoEventoEnum.PENDIENTE_ANTICIPO,
        fecha_creacion=fecha_base_utc,
    )
    asignacion = evento.asignar_proveedor(
        proveedor_id=uuid4(),
        nombre_servicio="Banquete Ejecutivo Nova",
        fecha_asignacion=fecha_base_utc,
    )
    asignacion.confirmar(fecha_confirmacion=fecha_base_utc + timedelta(hours=12))
    return evento


@pytest.fixture
def cuenta_pagos_anticipo_cubierto(evento_preliminar_valido: Evento) -> CuentaDePagos:
    """Retorna un Aggregate CuentaDePagos con el anticipo mínimo ya cubierto."""
    monto = MontoContractual(
        subtotal=Dinero(Decimal("100000.00"), "MXN"),
        anticipo_pactado=Dinero(Decimal("30000.00"), "MXN"),
        pagos_realizados=Dinero(Decimal("30000.00"), "MXN"),
        total_incrementos=Dinero.cero("MXN"),
    )
    return CuentaDePagos(
        evento_id=evento_preliminar_valido.id,
        monto_contractual=monto,
    )
