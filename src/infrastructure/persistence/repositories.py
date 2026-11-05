# src/infrastructure/persistence/repositories.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from src.domain.models.auditoria import LogAuditoria
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import Evento
from src.domain.repositories.interfaces import (
    ICuentaDePagosRepository,
    IEventoRepository,
    IRegistroAuditoriaRepository,
)
from src.domain.state_machine.estado_asignacion_proveedor import (
    EstadoAsignacionProveedorEnum,
)
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.infrastructure.persistence.models import (
    AsignacionProveedorModel,
    CotizacionIncrementoModel,
    CuentaDePagosModel,
    EventoModel,
    LogAuditoriaModel,
)


class SqlAlchemyEventoRepository(IEventoRepository):
    """Adaptador de persistencia SQLAlchemy para el Aggregate Root Evento."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener_por_id(self, evento_id: UUID) -> Optional[Evento]:
        stmt = select(EventoModel).where(EventoModel.id == evento_id)
        modelo = self._session.execute(stmt).scalar_one_or_none()
        if modelo is None:
            return None
        return modelo.to_domain()

    def guardar(self, evento: Evento) -> None:
        stmt = select(EventoModel).where(EventoModel.id == evento.id)
        modelo_existente = self._session.execute(stmt).scalar_one_or_none()

        if modelo_existente is None:
            nuevo_modelo = EventoModel(
                id=evento.id,
                cliente_id=evento.cliente_id,
                fecha_evento=evento.fecha_evento,
                cantidad_invitados=evento.cantidad_invitados,
                estado=evento.estado.value,
                fecha_creacion=evento.fecha_creacion,
                asignaciones=[
                    AsignacionProveedorModel.from_domain(evento.id, asig) for asig in evento.asignaciones_proveedores
                ],
                cotizaciones=[
                    CotizacionIncrementoModel.from_domain(evento.id, cot) for cot in evento.cotizaciones_incremento
                ],
            )
            self._session.add(nuevo_modelo)
        else:
            modelo_existente.cliente_id = evento.cliente_id
            modelo_existente.fecha_evento = evento.fecha_evento
            modelo_existente.cantidad_invitados = evento.cantidad_invitados
            modelo_existente.estado = evento.estado.value

            # Sincronizar colección de AsignacionProveedor
            mapa_asig_existentes = {a.id: a for a in modelo_existente.asignaciones}
            nuevas_asignaciones_orm: List[AsignacionProveedorModel] = []
            for asig_dom in evento.asignaciones_proveedores:
                if asig_dom.id in mapa_asig_existentes:
                    asig_orm = mapa_asig_existentes[asig_dom.id]
                    asig_orm.proveedor_id = asig_dom.proveedor_id
                    asig_orm.nombre_servicio = asig_dom.nombre_servicio
                    asig_orm.fecha_asignacion = asig_dom.fecha_asignacion
                    asig_orm.fecha_limite_confirmacion = asig_dom.fecha_limite_confirmacion
                    asig_orm.estado = asig_dom.estado.value
                    nuevas_asignaciones_orm.append(asig_orm)
                else:
                    nuevas_asignaciones_orm.append(AsignacionProveedorModel.from_domain(evento.id, asig_dom))
            modelo_existente.asignaciones = nuevas_asignaciones_orm

            # Sincronizar colección de CotizacionIncremento
            mapa_cot_existentes = {c.id: c for c in modelo_existente.cotizaciones}
            nuevas_cotizaciones_orm: List[CotizacionIncrementoModel] = []
            for cot_dom in evento.cotizaciones_incremento:
                if cot_dom.id in mapa_cot_existentes:
                    cot_orm = mapa_cot_existentes[cot_dom.id]
                    cot_orm.descripcion = cot_dom.descripcion
                    cot_orm.invitados_adicionales = cot_dom.invitados_adicionales
                    cot_orm.costo_adicional_monto = cot_dom.costo_adicional.monto
                    cot_orm.moneda = cot_dom.costo_adicional.moneda
                    cot_orm.fecha_solicitud = cot_dom.fecha_solicitud
                    cot_orm.estado = cot_dom.estado.value
                    nuevas_cotizaciones_orm.append(cot_orm)
                else:
                    nuevas_cotizaciones_orm.append(CotizacionIncrementoModel.from_domain(evento.id, cot_dom))
            modelo_existente.cotizaciones = nuevas_cotizaciones_orm

        self._session.flush()

    def listar_con_proveedores_pendientes_sla(self) -> List[Evento]:
        estados_evento_activos = [
            EstadoEventoEnum.BORRADOR.value,
            EstadoEventoEnum.PENDIENTE_ANTICIPO.value,
            EstadoEventoEnum.CONFIRMADO.value,
        ]
        stmt = (
            select(EventoModel)
            .join(AsignacionProveedorModel, EventoModel.id == AsignacionProveedorModel.evento_id)
            .where(
                EventoModel.estado.in_(estados_evento_activos),
                AsignacionProveedorModel.estado == EstadoAsignacionProveedorEnum.ASIGNADO.value,
            )
            .distinct()
        )
        modelos = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modelos]


class SqlAlchemyCuentaDePagosRepository(ICuentaDePagosRepository):
    """Adaptador de persistencia SQLAlchemy para el Aggregate Root CuentaDePagos."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener_por_id(self, cuenta_id: UUID) -> Optional[CuentaDePagos]:
        stmt = select(CuentaDePagosModel).where(CuentaDePagosModel.id == cuenta_id)
        modelo = self._session.execute(stmt).scalar_one_or_none()
        if modelo is None:
            return None
        return modelo.to_domain()

    def obtener_por_evento_id(self, evento_id: UUID) -> Optional[CuentaDePagos]:
        stmt = select(CuentaDePagosModel).where(CuentaDePagosModel.evento_id == evento_id)
        modelo = self._session.execute(stmt).scalar_one_or_none()
        if modelo is None:
            return None
        return modelo.to_domain()

    def guardar(self, cuenta: CuentaDePagos) -> None:
        stmt = select(CuentaDePagosModel).where(CuentaDePagosModel.id == cuenta.id)
        modelo_existente = self._session.execute(stmt).scalar_one_or_none()
        mc = cuenta.monto_contractual

        if modelo_existente is None:
            nuevo_modelo = CuentaDePagosModel(
                id=cuenta.id,
                evento_id=cuenta.evento_id,
                estado_pago=cuenta.estado_pago.value,
                subtotal_monto=mc.subtotal.monto,
                anticipo_pactado_monto=mc.anticipo_pactado.monto,
                pagos_realizados_monto=mc.pagos_realizados.monto,
                total_incrementos_monto=mc.total_incrementos.monto,
                moneda=mc.subtotal.moneda,
            )
            self._session.add(nuevo_modelo)
        else:
            modelo_existente.estado_pago = cuenta.estado_pago.value
            modelo_existente.subtotal_monto = mc.subtotal.monto
            modelo_existente.anticipo_pactado_monto = mc.anticipo_pactado.monto
            modelo_existente.pagos_realizados_monto = mc.pagos_realizados.monto
            modelo_existente.total_incrementos_monto = mc.total_incrementos.monto
            modelo_existente.moneda = mc.subtotal.moneda

        self._session.flush()


class SqlAlchemyRegistroAuditoriaRepository(IRegistroAuditoriaRepository):
    """
    Adaptador de persistencia SQLAlchemy para el Historial de Auditoría (ADR-003).
    Garantiza comportamiento estrictamente append-only.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, log: LogAuditoria) -> None:
        modelo = LogAuditoriaModel.from_domain(log)
        self._session.add(modelo)
        self._session.flush()

    def listar_por_entidad(self, entidad_id: UUID) -> List[LogAuditoria]:
        """
        Recupera cronológicamente todos los eventos de auditoría asociados
        directamente al entidad_id o cuyos detalles referencien al evento_id.
        """
        stmt = (
            select(LogAuditoriaModel)
            .where(LogAuditoriaModel.entidad_id == entidad_id)
            .order_by(LogAuditoriaModel.fecha_registro.asc())
        )
        modelos = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modelos]

    def listar_historial_completo_evento(self, evento_id: UUID) -> List[LogAuditoria]:
        """
        Recupera el historial de auditoría del Evento junto con los registros de su
        CuentaDePagos y sus Asignaciones de Proveedores asociadas.
        """
        ids_relacionados: List[UUID] = [evento_id]

        stmt_cuenta = select(CuentaDePagosModel.id).where(CuentaDePagosModel.evento_id == evento_id)
        cuenta_id = self._session.execute(stmt_cuenta).scalar_one_or_none()
        if cuenta_id is not None:
            ids_relacionados.append(cuenta_id)

        stmt_asig = select(AsignacionProveedorModel.id).where(AsignacionProveedorModel.evento_id == evento_id)
        asig_ids = self._session.execute(stmt_asig).scalars().all()
        ids_relacionados.extend(asig_ids)

        stmt_logs = (
            select(LogAuditoriaModel)
            .where(or_(LogAuditoriaModel.entidad_id.in_(ids_relacionados)))
            .order_by(LogAuditoriaModel.fecha_registro.asc())
        )
        modelos = self._session.execute(stmt_logs).scalars().all()
        return [m.to_domain() for m in modelos]
