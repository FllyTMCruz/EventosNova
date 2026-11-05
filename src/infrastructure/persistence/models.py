# src/infrastructure/persistence/models.py
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.domain.models.auditoria import LogAuditoria
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import (
    AsignacionProveedor,
    CotizacionIncremento,
    Evento,
)
from src.domain.state_machine.estado_asignacion_proveedor import (
    EstadoAsignacionProveedorEnum,
    EstadoCotizacionEnum,
    EstadoPagoEnum,
)
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.domain.value_objects.dinero import Dinero
from src.domain.value_objects.monto_contractual import MontoContractual
from src.infrastructure.config.database import Base


def _asegurar_utc(fecha: datetime) -> datetime:
    """Garantiza que las fechas recuperadas de motores como SQLite conserven tzinfo UTC."""
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


class EventoModel(Base):
    """Modelo relacional para el Aggregate Root Evento."""

    __tablename__ = "eventos"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    fecha_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cantidad_invitados: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    asignaciones: Mapped[List["AsignacionProveedorModel"]] = relationship(
        "AsignacionProveedorModel",
        back_populates="evento",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    cotizaciones: Mapped[List["CotizacionIncrementoModel"]] = relationship(
        "CotizacionIncrementoModel",
        back_populates="evento",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_domain(self) -> Evento:
        """Reconstruye el Aggregate Root Evento desde la representación relacional."""
        asignaciones_dominio = [a.to_domain() for a in self.asignaciones]
        cotizaciones_dominio = [c.to_domain() for c in self.cotizaciones]
        return Evento(
            id=self.id,
            cliente_id=self.cliente_id,
            fecha_evento=_asegurar_utc(self.fecha_evento),
            cantidad_invitados=self.cantidad_invitados,
            estado=EstadoEventoEnum(self.estado),
            fecha_creacion=_asegurar_utc(self.fecha_creacion),
            asignaciones_proveedores=asignaciones_dominio,
            cotizaciones_incremento=cotizaciones_dominio,
        )


class AsignacionProveedorModel(Base):
    """Modelo relacional para la entidad interna AsignacionProveedor."""

    __tablename__ = "asignaciones_proveedores"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    evento_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proveedor_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    nombre_servicio: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_limite_confirmacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    evento: Mapped["EventoModel"] = relationship("EventoModel", back_populates="asignaciones")

    def to_domain(self) -> AsignacionProveedor:
        return AsignacionProveedor(
            id=self.id,
            proveedor_id=self.proveedor_id,
            nombre_servicio=self.nombre_servicio,
            fecha_asignacion=_asegurar_utc(self.fecha_asignacion),
            fecha_limite_confirmacion=_asegurar_utc(self.fecha_limite_confirmacion),
            estado=EstadoAsignacionProveedorEnum(self.estado),
        )

    @classmethod
    def from_domain(cls, evento_id: UUID, entidad: AsignacionProveedor) -> "AsignacionProveedorModel":
        return cls(
            id=entidad.id,
            evento_id=evento_id,
            proveedor_id=entidad.proveedor_id,
            nombre_servicio=entidad.nombre_servicio,
            fecha_asignacion=entidad.fecha_asignacion,
            fecha_limite_confirmacion=entidad.fecha_limite_confirmacion,
            estado=entidad.estado.value,
        )


class CotizacionIncrementoModel(Base):
    """Modelo relacional para la entidad interna CotizacionIncremento."""

    __tablename__ = "cotizaciones_incremento"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    evento_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    invitados_adicionales: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_adicional_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN")
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)

    evento: Mapped["EventoModel"] = relationship("EventoModel", back_populates="cotizaciones")

    def to_domain(self) -> CotizacionIncremento:
        return CotizacionIncremento(
            id=self.id,
            descripcion=self.descripcion,
            invitados_adicionales=self.invitados_adicionales,
            costo_adicional=Dinero(monto=Decimal(str(self.costo_adicional_monto)), moneda=self.moneda),
            fecha_solicitud=_asegurar_utc(self.fecha_solicitud),
            estado=EstadoCotizacionEnum(self.estado),
        )

    @classmethod
    def from_domain(cls, evento_id: UUID, entidad: CotizacionIncremento) -> "CotizacionIncrementoModel":
        return cls(
            id=entidad.id,
            evento_id=evento_id,
            descripcion=entidad.descripcion,
            invitados_adicionales=entidad.invitados_adicionales,
            costo_adicional_monto=entidad.costo_adicional.monto,
            moneda=entidad.costo_adicional.moneda,
            fecha_solicitud=entidad.fecha_solicitud,
            estado=entidad.estado.value,
        )


class CuentaDePagosModel(Base):
    """Modelo relacional para el Aggregate Root Financiero CuentaDePagos."""

    __tablename__ = "cuentas_pagos"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    evento_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    estado_pago: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    subtotal_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    anticipo_pactado_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pagos_realizados_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_incrementos_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN")

    def to_domain(self) -> CuentaDePagos:
        monto_vo = MontoContractual(
            subtotal=Dinero(monto=Decimal(str(self.subtotal_monto)), moneda=self.moneda),
            anticipo_pactado=Dinero(monto=Decimal(str(self.anticipo_pactado_monto)), moneda=self.moneda),
            pagos_realizados=Dinero(monto=Decimal(str(self.pagos_realizados_monto)), moneda=self.moneda),
            total_incrementos=Dinero(monto=Decimal(str(self.total_incrementos_monto)), moneda=self.moneda),
        )
        return CuentaDePagos(
            id=self.id,
            evento_id=self.evento_id,
            monto_contractual=monto_vo,
            estado_pago=EstadoPagoEnum(self.estado_pago),
        )


class LogAuditoriaModel(Base):
    """
    Modelo relacional inmutable para el Historial de Auditoría (ADR-003).
    Diseñado exclusivamente para operaciones de inserción (append-only).
    """

    __tablename__ = "logs_auditoria"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    entidad_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    tipo_entidad: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(50), nullable=False)
    detalles: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    usuario_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    def to_domain(self) -> LogAuditoria:
        return LogAuditoria(
            id=self.id,
            entidad_id=self.entidad_id,
            tipo_entidad=self.tipo_entidad,
            accion=self.accion,
            estado_anterior=self.estado_anterior,
            estado_nuevo=self.estado_nuevo,
            detalles=dict(self.detalles) if self.detalles else {},
            usuario_id=self.usuario_id,
            fecha_registro=_asegurar_utc(self.fecha_registro),
        )

    @classmethod
    def from_domain(cls, log: LogAuditoria) -> "LogAuditoriaModel":
        return cls(
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
