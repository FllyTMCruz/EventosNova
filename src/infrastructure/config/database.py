# src/infrastructure/config/database.py
import os
from typing import Generator
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos ORM de SQLAlchemy."""


def obtener_database_url() -> str:
    """
    Obtiene la URL de conexión desde la variable de entorno DATABASE_URL.
    Por defecto utiliza SQLite local; admite PostgreSQL (postgresql+psycopg2://...)
    y SQLite en memoria (sqlite:///:memory:) para pruebas.
    """
    return os.getenv("DATABASE_URL", "sqlite:///./eventos_nova.db")


def construir_engine(database_url: str | None = None) -> Engine:
    """Construye el motor SQLAlchemy ajustando parámetros según el dialecto."""
    url = database_url or obtener_database_url()

    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if ":memory:" in url:
            return create_engine(
                url,
                connect_args=connect_args,
                poolclass=StaticPool,
                future=True,
            )
        return create_engine(url, connect_args=connect_args, future=True)

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        future=True,
    )


engine: Engine = construir_engine()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def init_db(target_engine: Engine | None = None) -> None:
    """Inicializa el esquema relacional creando todas las tablas registradas en Base."""
    from src.infrastructure.persistence import models  # noqa: F401

    motor = target_engine or engine
    Base.metadata.create_all(bind=motor)


def get_db_session() -> Generator[Session, None, None]:
    """Generador de sesiones de base de datos para inyección de dependencias."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
