# tests/unit/test_specifications.py
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from src.domain.exceptions import LimiteProveedoresExcedidoException
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import Evento
from src.domain.specifications.evento_specifications import (
    CapacidadInvitadosSpecification,
    ContextoFormalizacionContrato,
    FormalizacionContratoSpecification,
    LimiteProveedoresSpecification,
    VentanaCambioAlcanceSpecification,
)
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.domain.value_objects.dinero import Dinero
from src.domain.value_objects.monto_contractual import MontoContractual


class TestCapacidadInvitadosSpecification:
    """Validación de la regla de negocio BR-05 (20 a 300 invitados)."""

    @pytest.mark.parametrize("cantidad", [20, 21, 150, 299, 300])
    def test_capacidad_dentro_de_rango_es_valida(self, cantidad: int) -> None:
        spec = CapacidadInvitadosSpecification()
        assert spec.is_satisfied_by(cantidad) is True

    @pytest.mark.parametrize("cantidad", [-10, 0, 1, 19, 301, 500])
    def test_capacidad_fuera_de_rango_es_invalida(self, cantidad: int) -> None:
        spec = CapacidadInvitadosSpecification()
        assert spec.is_satisfied_by(cantidad) is False

    def test_operadores_booleanos_specification(self) -> None:
        spec = CapacidadInvitadosSpecification()
        invertida = spec.not_()
        assert invertida.is_satisfied_by(10) is True
        assert invertida.is_satisfied_by(100) is False

        compuesta_and = spec.and_(spec)
        compuesta_or = spec.or_(invertida)
        assert compuesta_and.is_satisfied_by(100) is True
        assert compuesta_or.is_satisfied_by(5) is True


class TestLimiteProveedoresSpecification:
    """Validación de la regla de negocio BR-15 (máximo 15 proveedores activos)."""

    def test_permite_hasta_15_proveedores_y_bloquea_el_16(self, fecha_base_utc: datetime) -> None:
        evento = Evento(
            cliente_id=uuid4(),
            fecha_evento=fecha_base_utc + timedelta(days=40),
            cantidad_invitados=200,
        )
        spec = LimiteProveedoresSpecification()

        for i in range(15):
            assert spec.puede_agregar_proveedor(evento) is True
            evento.asignar_proveedor(
                proveedor_id=uuid4(),
                nombre_servicio=f"Servicio Proveedor {i + 1}",
                fecha_asignacion=fecha_base_utc,
            )

        assert spec.is_satisfied_by(evento) is True
        assert spec.puede_agregar_proveedor(evento) is False

        with pytest.raises(LimiteProveedoresExcedidoException):
            evento.asignar_proveedor(
                proveedor_id=uuid4(),
                nombre_servicio="Proveedor Excedente 16",
                fecha_asignacion=fecha_base_utc,
            )


class TestVentanaCambioAlcanceSpecification:
    """Validación de las reglas BR-02 y BR-12 (mínimo 7 días naturales de anticipación)."""

    def test_ventana_7_dias_exactos_o_mas_es_valida(self, fecha_base_utc: datetime) -> None:
        fecha_evento = datetime(2026, 11, 20, 20, 0, tzinfo=timezone.utc)
        evento = Evento(
            cliente_id=uuid4(),
            fecha_evento=fecha_evento,
            cantidad_invitados=100,
            estado=EstadoEventoEnum.CONFIRMADO,
        )

        # Exactamente 7 días naturales antes
        fecha_solicitud_7d = datetime(2026, 11, 13, 18, 0, tzinfo=timezone.utc)
        spec_7d = VentanaCambioAlcanceSpecification(fecha_solicitud=fecha_solicitud_7d)
        assert spec_7d.is_satisfied_by(evento) is True

        # 6 días naturales antes -> inválido
        fecha_solicitud_6d = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)
        spec_6d = VentanaCambioAlcanceSpecification(fecha_solicitud=fecha_solicitud_6d)
        assert spec_6d.is_satisfied_by(evento) is False

    def test_ventana_cambio_alcance_rechaza_evento_no_confirmado(self, fecha_base_utc: datetime) -> None:
        evento_borrador = Evento(
            cliente_id=uuid4(),
            fecha_evento=fecha_base_utc + timedelta(days=30),
            cantidad_invitados=100,
            estado=EstadoEventoEnum.PENDIENTE_ANTICIPO,
        )
        spec = VentanaCambioAlcanceSpecification(fecha_solicitud=fecha_base_utc)
        assert spec.is_satisfied_by(evento_borrador) is False


class TestFormalizacionContratoSpecification:
    """Validación exhaustiva de las 4 condiciones de la regla BR-07."""

    def test_cumple_las_4_condiciones_br07(
        self,
        evento_preliminar_valido: Evento,
        cuenta_pagos_anticipo_cubierto: CuentaDePagos,
        fecha_base_utc: datetime,
    ) -> None:
        spec = FormalizacionContratoSpecification()
        contexto = ContextoFormalizacionContrato(
            evento=evento_preliminar_valido,
            cuenta_pagos=cuenta_pagos_anticipo_cubierto,
            fecha_actual=fecha_base_utc,
        )
        assert spec.is_satisfied_by(contexto) is True
        assert spec.obtener_motivos_incumplimiento(contexto) == []

    def test_falla_cuando_anticipo_no_esta_cubierto_o_hay_proveedores_pendientes(
        self,
        evento_preliminar_valido: Evento,
        fecha_base_utc: datetime,
    ) -> None:
        # Agregar un proveedor sin confirmar (ASIGNADO)
        evento_preliminar_valido.asignar_proveedor(
            proveedor_id=uuid4(),
            nombre_servicio="Fotografía Profesional",
            fecha_asignacion=fecha_base_utc,
        )
        # Cuenta sin pagos realizados
        monto_sin_pago = MontoContractual(
            subtotal=Dinero(Decimal("100000.00")),
            anticipo_pactado=Dinero(Decimal("30000.00")),
            pagos_realizados=Dinero(Decimal("10000.00")),
            total_incrementos=Dinero.cero(),
        )
        cuenta_incompleta = CuentaDePagos(
            evento_id=evento_preliminar_valido.id,
            monto_contractual=monto_sin_pago,
        )

        spec = FormalizacionContratoSpecification()
        contexto = ContextoFormalizacionContrato(
            evento=evento_preliminar_valido,
            cuenta_pagos=cuenta_incompleta,
            fecha_actual=fecha_base_utc,
        )
        assert spec.is_satisfied_by(contexto) is False
        motivos = spec.obtener_motivos_incumplimiento(contexto)
        assert len(motivos) == 2
        assert any("ASIGNADO pendientes de confirmar" in m for m in motivos)
        assert any("anticipo pactado no ha sido cubierto" in m for m in motivos)
