# src/domain/models/evento.py
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from src.domain.events import (
    AlcanceModificadoEvent,
    ContratoFormalizadoEvent,
    DomainEvent,
    EventoLiquidadoEvent,
    ProveedorVencidoSLAEvent,
)
from src.domain.exceptions import (
    CapacidadInvitadosInvalidaException,
    EntidadNoEncontradaException,
    LimiteProveedoresExcedidoException,
    PlazoVencidoException,
    ReglaNegocioException,
    RequisitoFormalizacionFaltanteException,
)
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.specifications.evento_specifications import (
    CapacidadInvitadosSpecification,
    ContextoFormalizacionContrato,
    FormalizacionContratoSpecification,
    LimiteProveedoresSpecification,
    VentanaCambioAlcanceSpecification,
)
from src.domain.state_machine.estado_asignacion_proveedor import (
    AsignacionProveedorStateMachine,
    EstadoAsignacionProveedorEnum,
    EstadoCotizacionEnum,
)
from src.domain.state_machine.estado_evento import (
    EstadoEventoEnum,
    EstadoEventoStateMachine,
)
from src.domain.value_objects.dinero import Dinero


class AsignacionProveedor:
    """
    Entidad interna del Aggregate Evento que representa la asignación de un proveedor
    sujeta a un SLA de confirmación de 48 horas (BR-04).
    """

    HORAS_SLA_CONFIRMACION: int = 48

    def __init__(
        self,
        proveedor_id: UUID,
        nombre_servicio: str,
        fecha_asignacion: Optional[datetime] = None,
        fecha_limite_confirmacion: Optional[datetime] = None,
        estado: EstadoAsignacionProveedorEnum = EstadoAsignacionProveedorEnum.ASIGNADO,
        id: Optional[UUID] = None,
    ) -> None:
        if not nombre_servicio or not nombre_servicio.strip():
            raise ReglaNegocioException("El nombre del servicio del proveedor es obligatorio.")

        self._id: UUID = id or uuid4()
        self._proveedor_id: UUID = proveedor_id
        self._nombre_servicio: str = nombre_servicio.strip()
        self._fecha_asignacion: datetime = fecha_asignacion or datetime.now(timezone.utc)
        self._fecha_limite_confirmacion: datetime = fecha_limite_confirmacion or (
            self._fecha_asignacion + timedelta(hours=self.HORAS_SLA_CONFIRMACION)
        )
        self._estado: EstadoAsignacionProveedorEnum = estado

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def proveedor_id(self) -> UUID:
        return self._proveedor_id

    @property
    def nombre_servicio(self) -> str:
        return self._nombre_servicio

    @property
    def fecha_asignacion(self) -> datetime:
        return self._fecha_asignacion

    @property
    def fecha_limite_confirmacion(self) -> datetime:
        return self._fecha_limite_confirmacion

    @property
    def estado(self) -> EstadoAsignacionProveedorEnum:
        return self._estado

    def confirmar(self, fecha_confirmacion: datetime) -> None:
        """Confirma la participación del proveedor si está dentro de las 48h de SLA."""
        if fecha_confirmacion > self._fecha_limite_confirmacion:
            self._estado = AsignacionProveedorStateMachine.validar_transicion(
                self._estado, EstadoAsignacionProveedorEnum.VENCIDO
            )
            raise PlazoVencidoException(
                operacion="Confirmación de Proveedor (BR-04)",
                detalle_plazo=(f"El SLA de 48 horas venció el {self._fecha_limite_confirmacion.isoformat()}."),
            )
        self._estado = AsignacionProveedorStateMachine.validar_transicion(
            self._estado, EstadoAsignacionProveedorEnum.CONFIRMADO
        )

    def declinar(self) -> None:
        """Marca la asignación como declinada por el proveedor."""
        self._estado = AsignacionProveedorStateMachine.validar_transicion(
            self._estado, EstadoAsignacionProveedorEnum.DECLINADO
        )

    def evaluar_vencimiento_sla(self, fecha_corte: datetime) -> bool:
        """
        Verifica si la asignación en estado ASIGNADO ha superado su fecha límite de 48h.
        Si venció, transiciona a VENCIDO y retorna True.
        """
        if self._estado == EstadoAsignacionProveedorEnum.ASIGNADO and fecha_corte > self._fecha_limite_confirmacion:
            self._estado = AsignacionProveedorStateMachine.validar_transicion(
                self._estado, EstadoAsignacionProveedorEnum.VENCIDO
            )
            return True
        return False


class CotizacionIncremento:
    """
    Entidad interna del Aggregate Evento que modela una solicitud y cotización
    de incremento de alcance (invitados extra o servicios adicionales).
    """

    def __init__(
        self,
        descripcion: str,
        invitados_adicionales: int,
        costo_adicional: Dinero,
        fecha_solicitud: Optional[datetime] = None,
        estado: EstadoCotizacionEnum = EstadoCotizacionEnum.SOLICITADA,
        id: Optional[UUID] = None,
    ) -> None:
        if not descripcion or not descripcion.strip():
            raise ReglaNegocioException("La descripción de la cotización de incremento es obligatoria.")
        if invitados_adicionales < 0:
            raise ReglaNegocioException("La cantidad de invitados adicionales no puede ser negativa.")
        if not costo_adicional.es_mayor_que(Dinero.cero(costo_adicional.moneda)):
            raise ReglaNegocioException("El costo adicional de la cotización debe ser mayor a cero.")

        self._id: UUID = id or uuid4()
        self._descripcion: str = descripcion.strip()
        self._invitados_adicionales: int = invitados_adicionales
        self._costo_adicional: Dinero = costo_adicional
        self._fecha_solicitud: datetime = fecha_solicitud or datetime.now(timezone.utc)
        self._estado: EstadoCotizacionEnum = estado

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def invitados_adicionales(self) -> int:
        return self._invitados_adicionales

    @property
    def costo_adicional(self) -> Dinero:
        return self._costo_adicional

    @property
    def fecha_solicitud(self) -> datetime:
        return self._fecha_solicitud

    @property
    def estado(self) -> EstadoCotizacionEnum:
        return self._estado

    def aprobar(self) -> None:
        if self._estado != EstadoCotizacionEnum.SOLICITADA:
            raise ReglaNegocioException(
                f"Solo se pueden aprobar cotizaciones en estado SOLICITADA (actual: {self._estado.value})."
            )
        self._estado = EstadoCotizacionEnum.APROBADA

    def rechazar(self) -> None:
        if self._estado != EstadoCotizacionEnum.SOLICITADA:
            raise ReglaNegocioException(
                f"Solo se pueden rechazar cotizaciones en estado SOLICITADA (actual: {self._estado.value})."
            )
        self._estado = EstadoCotizacionEnum.RECHAZADA


class Evento:
    """
    Aggregate Root Operativo de Eventos Nova.
    Coordina el ciclo de vida del evento, las asignaciones de proveedores con SLA de 48h,
    las cotizaciones por cambio de alcance y la verificación de especificaciones.
    """

    def __init__(
        self,
        cliente_id: UUID,
        fecha_evento: datetime,
        cantidad_invitados: int,
        id: Optional[UUID] = None,
        estado: EstadoEventoEnum = EstadoEventoEnum.BORRADOR,
        fecha_creacion: Optional[datetime] = None,
        asignaciones_proveedores: Optional[List[AsignacionProveedor]] = None,
        cotizaciones_incremento: Optional[List[CotizacionIncremento]] = None,
    ) -> None:
        capacidad_spec = CapacidadInvitadosSpecification()
        if not capacidad_spec.is_satisfied_by(cantidad_invitados):
            raise CapacidadInvitadosInvalidaException(cantidad_solicitada=cantidad_invitados)

        self._id: UUID = id or uuid4()
        self._cliente_id: UUID = cliente_id
        self._fecha_evento: datetime = fecha_evento
        self._cantidad_invitados: int = cantidad_invitados
        self._estado: EstadoEventoEnum = estado
        self._fecha_creacion: datetime = fecha_creacion or datetime.now(timezone.utc)
        self._asignaciones_proveedores: List[AsignacionProveedor] = (
            list(asignaciones_proveedores) if asignaciones_proveedores else []
        )
        self._cotizaciones_incremento: List[CotizacionIncremento] = (
            list(cotizaciones_incremento) if cotizaciones_incremento else []
        )
        self._domain_events: List[DomainEvent] = []

        limite_spec = LimiteProveedoresSpecification()
        if not limite_spec.is_satisfied_by(self):
            raise LimiteProveedoresExcedidoException(cantidad_actual=len(self._asignaciones_proveedores))

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def cliente_id(self) -> UUID:
        return self._cliente_id

    @property
    def fecha_evento(self) -> datetime:
        return self._fecha_evento

    @property
    def cantidad_invitados(self) -> int:
        return self._cantidad_invitados

    @property
    def estado(self) -> EstadoEventoEnum:
        return self._estado

    @property
    def fecha_creacion(self) -> datetime:
        return self._fecha_creacion

    @property
    def asignaciones_proveedores(self) -> List[AsignacionProveedor]:
        return list(self._asignaciones_proveedores)

    @property
    def cotizaciones_incremento(self) -> List[CotizacionIncremento]:
        return list(self._cotizaciones_incremento)

    def registrar_pendiente_anticipo(self) -> None:
        """Transiciona el evento de BORRADOR a PENDIENTE_ANTICIPO."""
        self._estado = EstadoEventoStateMachine.validar_transicion(self._estado, EstadoEventoEnum.PENDIENTE_ANTICIPO)

    def asignar_proveedor(
        self,
        proveedor_id: UUID,
        nombre_servicio: str,
        fecha_asignacion: Optional[datetime] = None,
    ) -> AsignacionProveedor:
        """
        Asigna un proveedor al evento verificando la regla BR-15 (máximo 15 proveedores activos)
        y evitando duplicidad de proveedor activo.
        """
        if self._estado in (EstadoEventoEnum.FINALIZADO, EstadoEventoEnum.CANCELADO):
            raise ReglaNegocioException(
                f"No es posible asignar proveedores a un evento en estado '{self._estado.value}'."
            )

        for asig in self._asignaciones_proveedores:
            if asig.proveedor_id == proveedor_id and asig.estado in (
                EstadoAsignacionProveedorEnum.ASIGNADO,
                EstadoAsignacionProveedorEnum.CONFIRMADO,
            ):
                raise ReglaNegocioException(
                    f"El proveedor '{proveedor_id}' ya tiene una asignación activa en este evento."
                )

        limite_spec = LimiteProveedoresSpecification()
        if not limite_spec.puede_agregar_proveedor(self):
            activos = [
                a
                for a in self._asignaciones_proveedores
                if a.estado
                in (
                    EstadoAsignacionProveedorEnum.ASIGNADO,
                    EstadoAsignacionProveedorEnum.CONFIRMADO,
                )
            ]
            raise LimiteProveedoresExcedidoException(cantidad_actual=len(activos))

        nueva_asignacion = AsignacionProveedor(
            proveedor_id=proveedor_id,
            nombre_servicio=nombre_servicio,
            fecha_asignacion=fecha_asignacion,
        )
        self._asignaciones_proveedores.append(nueva_asignacion)
        return nueva_asignacion

    def confirmar_proveedor(self, proveedor_id: UUID, fecha_confirmacion: datetime) -> AsignacionProveedor:
        """Confirma la asignación de un proveedor específico validando su SLA de 48h."""
        for asig in self._asignaciones_proveedores:
            if asig.proveedor_id == proveedor_id and asig.estado == EstadoAsignacionProveedorEnum.ASIGNADO:
                asig.confirmar(fecha_confirmacion)
                return asig
        raise EntidadNoEncontradaException(
            tipo_entidad="AsignacionProveedor activa",
            identificador=str(proveedor_id),
        )

    def formalizar_contrato(
        self,
        cuenta_pagos: CuentaDePagos,
        fecha_actual: Optional[datetime] = None,
    ) -> None:
        """
        Caso de Uso CU-03 / Regla BR-07:
        Evalúa las 4 condiciones de FormalizacionContratoSpecification y transiciona
        el evento al estado CONFIRMADO emitiendo ContratoFormalizadoEvent.
        """
        ahora = fecha_actual or datetime.now(timezone.utc)
        contexto = ContextoFormalizacionContrato(
            evento=self,
            cuenta_pagos=cuenta_pagos,
            fecha_actual=ahora,
        )
        spec = FormalizacionContratoSpecification()
        if not spec.is_satisfied_by(contexto):
            motivos = spec.obtener_motivos_incumplimiento(contexto)
            raise RequisitoFormalizacionFaltanteException(motivos=motivos)

        self._estado = EstadoEventoStateMachine.validar_transicion(self._estado, EstadoEventoEnum.CONFIRMADO)

        self._domain_events.append(
            ContratoFormalizadoEvent(
                evento_id=self._id,
                cliente_id=self._cliente_id,
                fecha_evento=self._fecha_evento,
                monto_total_pactado=cuenta_pagos.monto_contractual.monto_total_actualizado.monto,
                anticipo_pagado=cuenta_pagos.monto_contractual.pagos_realizados.monto,
            )
        )

    def solicitar_cambio_alcance(
        self,
        descripcion: str,
        invitados_adicionales: int,
        costo_adicional: Dinero,
        fecha_solicitud: Optional[datetime] = None,
        aprobar_inmediatamente: bool = True,
    ) -> CotizacionIncremento:
        """
        Caso de Uso CU-04 / Reglas BR-02, BR-05 y BR-12:
        Valida que el evento esté CONFIRMADO, dentro de la ventana de al menos 7 días naturales
        previos al evento, y que el nuevo total de invitados no supere los 300 invitados (BR-05).
        """
        ahora = fecha_solicitud or datetime.now(timezone.utc)

        if self._estado != EstadoEventoEnum.CONFIRMADO:
            raise ReglaNegocioException(
                f"Solo se permiten cambios de alcance en eventos CONFIRMADOS (estado actual: {self._estado.value})."
            )

        ventana_spec = VentanaCambioAlcanceSpecification(fecha_solicitud=ahora)
        if not ventana_spec.is_satisfied_by(self):
            raise PlazoVencidoException(
                operacion="Cambio de Alcance (BR-02 / BR-12)",
                detalle_plazo=(
                    "Las modificaciones de alcance deben solicitarse con al menos 7 días naturales "
                    f"de anticipación a la fecha del evento ({self._fecha_evento.date().isoformat()})."
                ),
            )

        nueva_cantidad_invitados = self._cantidad_invitados + invitados_adicionales
        capacidad_spec = CapacidadInvitadosSpecification()
        if not capacidad_spec.is_satisfied_by(nueva_cantidad_invitados):
            raise CapacidadInvitadosInvalidaException(cantidad_solicitada=nueva_cantidad_invitados)

        cotizacion = CotizacionIncremento(
            descripcion=descripcion,
            invitados_adicionales=invitados_adicionales,
            costo_adicional=costo_adicional,
            fecha_solicitud=ahora,
        )
        self._cotizaciones_incremento.append(cotizacion)

        if aprobar_inmediatamente:
            self.aprobar_cotizacion_incremento(cotizacion.id)

        return cotizacion

    def aprobar_cotizacion_incremento(self, cotizacion_id: UUID) -> CotizacionIncremento:
        """Aprueba una cotización de incremento pendiente, actualiza el aforo y emite evento de dominio."""
        cotizacion = next(
            (c for c in self._cotizaciones_incremento if c.id == cotizacion_id),
            None,
        )
        if cotizacion is None:
            raise EntidadNoEncontradaException(
                tipo_entidad="CotizacionIncremento",
                identificador=str(cotizacion_id),
            )

        nueva_cantidad = self._cantidad_invitados + cotizacion.invitados_adicionales
        capacidad_spec = CapacidadInvitadosSpecification()
        if not capacidad_spec.is_satisfied_by(nueva_cantidad):
            raise CapacidadInvitadosInvalidaException(cantidad_solicitada=nueva_cantidad)

        invitados_anteriores = self._cantidad_invitados
        cotizacion.aprobar()
        self._cantidad_invitados = nueva_cantidad

        self._domain_events.append(
            AlcanceModificadoEvent(
                evento_id=self._id,
                cotizacion_id=cotizacion.id,
                invitados_anteriores=invitados_anteriores,
                invitados_nuevos=self._cantidad_invitados,
                costo_adicional=cotizacion.costo_adicional.monto,
            )
        )
        return cotizacion

    def evaluar_sla_proveedores(self, fecha_corte: Optional[datetime] = None) -> List[AsignacionProveedor]:
        """
        Regla de Negocio BR-04:
        Evalúa todas las asignaciones en estado ASIGNADO y marca como VENCIDO aquellas
        que superaron el límite de 48 horas. Emite ProveedorVencidoSLAEvent por cada vencimiento.
        """
        ahora = fecha_corte or datetime.now(timezone.utc)
        vencidos: List[AsignacionProveedor] = []

        for asignacion in self._asignaciones_proveedores:
            if asignacion.evaluar_vencimiento_sla(ahora):
                vencidos.append(asignacion)
                self._domain_events.append(
                    ProveedorVencidoSLAEvent(
                        evento_id=self._id,
                        asignacion_id=asignacion.id,
                        proveedor_id=asignacion.proveedor_id,
                        fecha_limite=asignacion.fecha_limite_confirmacion,
                    )
                )
        return vencidos

    def iniciar_ejecucion(self) -> None:
        """Transiciona el evento de CONFIRMADO a EN_EJECUCION."""
        self._estado = EstadoEventoStateMachine.validar_transicion(self._estado, EstadoEventoEnum.EN_EJECUCION)

    def marcar_liquidado(self, cuenta_pagos: CuentaDePagos) -> None:
        """
        Verifica que la CuentaDePagos esté 100% liquidada y finaliza el evento
        transicionando de EN_EJECUCION a FINALIZADO.
        """
        if cuenta_pagos.evento_id != self._id:
            raise ReglaNegocioException("La cuenta de pagos no corresponde a este evento.")
        if not cuenta_pagos.esta_liquidada():
            saldo = cuenta_pagos.monto_contractual.calcular_saldo_pendiente().monto
            raise ReglaNegocioException(
                f"No se puede finalizar y marcar como liquidado un evento con saldo pendiente ({saldo})."
            )

        self._estado = EstadoEventoStateMachine.validar_transicion(self._estado, EstadoEventoEnum.FINALIZADO)
        self._domain_events.append(
            EventoLiquidadoEvent(
                evento_id=self._id,
                cuenta_pagos_id=cuenta_pagos.id,
                total_pagado=cuenta_pagos.monto_contractual.pagos_realizados.monto,
            )
        )

    def cancelar(self) -> None:
        """Cancela el evento validando que no esté en ejecución ni finalizado."""
        self._estado = EstadoEventoStateMachine.validar_transicion(self._estado, EstadoEventoEnum.CANCELADO)

    def pull_domain_events(self) -> List[DomainEvent]:
        eventos = list(self._domain_events)
        self._domain_events.clear()
        return eventos
