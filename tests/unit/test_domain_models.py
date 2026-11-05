# tests/unit/test_domain_models.py
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from src.domain.events import (
    AlcanceModificadoEvent,
    ContratoFormalizadoEvent,
    EventoLiquidadoEvent,
    ProveedorVencidoSLAEvent,
)
from src.domain.exceptions import (
    CapacidadInvitadosInvalidaException,
    EntidadNoEncontradaException,
    OperacionFinancieraInvalidaException,
    PlazoVencidoException,
    ReglaNegocioException,
)
from src.domain.models.auditoria import LogAuditoria
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import CotizacionIncremento, Evento
from src.domain.state_machine.estado_asignacion_proveedor import (
    EstadoAsignacionProveedorEnum,
    EstadoCotizacionEnum,
    EstadoPagoEnum,
)
from src.domain.state_machine.estado_evento import EstadoEventoEnum
from src.domain.value_objects.dinero import Dinero
from src.domain.value_objects.monto_contractual import MontoContractual
from src.domain.value_objects.rango_fechas import RangoFechas


class TestValueObjects:
    """Pruebas unitarias para los Value Objects Dinero, RangoFechas y MontoContractual."""

    def test_dinero_operaciones_aritmeticas_y_redondeo(self) -> None:
        d1 = Dinero(Decimal("1500.556"), "mxn")
        d2 = Dinero(Decimal("499.44"), "MXN")

        assert d1.monto == Decimal("1500.56")
        assert d1.moneda == "MXN"

        suma = d1.sumar(d2)
        assert suma.monto == Decimal("2000.00")

        resta = suma.restar(d2)
        assert resta.es_igual_a(d1)
        assert suma.es_mayor_que(d1)
        assert suma.es_mayor_o_igual_que(suma)

        porcentaje = suma.multiplicar_porcentaje(Decimal("15.00"))
        assert porcentaje.monto == Decimal("300.00")

    def test_dinero_invariantes_negativos_y_moneda(self) -> None:
        with pytest.raises(OperacionFinancieraInvalidaException):
            Dinero(Decimal("-0.01"), "MXN")

        with pytest.raises(OperacionFinancieraInvalidaException):
            Dinero(Decimal("100.00"), "PESOS")

        d_mxn = Dinero(Decimal("100.00"), "MXN")
        d_usd = Dinero(Decimal("100.00"), "USD")
        with pytest.raises(OperacionFinancieraInvalidaException):
            d_mxn.sumar(d_usd)

        with pytest.raises(OperacionFinancieraInvalidaException):
            d_mxn.restar(Dinero(Decimal("250.00"), "MXN"))

        with pytest.raises(OperacionFinancieraInvalidaException):
            d_mxn.multiplicar_porcentaje(Decimal("-5.00"))

    def test_rango_fechas_calculos_y_validacion(self) -> None:
        inicio = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
        fin = datetime(2026, 10, 11, 22, 0, tzinfo=timezone.utc)
        rango = RangoFechas(fecha_inicio=inicio, fecha_fin=fin)

        assert rango.diferencia_dias_naturales == 10
        assert rango.diferencia_horas == 252.0
        assert rango.contiene(datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)) is True

        with pytest.raises(ReglaNegocioException):
            RangoFechas(fecha_inicio=fin, fecha_fin=inicio)

    def test_monto_contractual_invariantes_y_transiciones_inmutables(self) -> None:
        mc = MontoContractual(
            subtotal=Dinero(Decimal("80000.00")),
            anticipo_pactado=Dinero(Decimal("20000.00")),
            pagos_realizados=Dinero.cero(),
            total_incrementos=Dinero.cero(),
        )
        assert mc.cubre_anticipo_requerido() is False
        assert mc.calcular_saldo_pendiente().monto == Decimal("80000.00")

        mc_con_anticipo = mc.con_nuevo_pago(Dinero(Decimal("25000.00")))
        assert mc_con_anticipo.cubre_anticipo_requerido() is True
        assert mc_con_anticipo.calcular_saldo_pendiente().monto == Decimal("55000.00")

        mc_con_incremento = mc_con_anticipo.con_incremento_alcance(
            costo_adicional=Dinero(Decimal("10000.00")),
            porcentaje_anticipo_incremento=Decimal("50.00"),
        )
        assert mc_con_incremento.monto_total_actualizado.monto == Decimal("90000.00")
        assert mc_con_incremento.anticipo_pactado.monto == Decimal("25000.00")
        assert mc_con_incremento.calcular_saldo_pendiente().monto == Decimal("65000.00")

        with pytest.raises(OperacionFinancieraInvalidaException):
            mc_con_incremento.con_nuevo_pago(Dinero(Decimal("70000.00")))


class TestCuentaDePagosAggregate:
    """Pruebas de invariantes del Aggregate Root Financiero CuentaDePagos."""

    def test_ciclo_completo_pagos_y_liquidacion(self) -> None:
        monto = MontoContractual(
            subtotal=Dinero(Decimal("50000.00")),
            anticipo_pactado=Dinero(Decimal("15000.00")),
            pagos_realizados=Dinero.cero(),
            total_incrementos=Dinero.cero(),
        )
        cuenta = CuentaDePagos(evento_id=uuid4(), monto_contractual=monto)
        assert cuenta.estado_pago == EstadoPagoEnum.PENDIENTE_ANTICIPO

        cuenta.registrar_pago(Dinero(Decimal("15000.00")))
        assert cuenta.estado_pago == EstadoPagoEnum.ANTICIPO_CUBIERTO
        assert cuenta.esta_anticipo_cubierto() is True

        cuenta.registrar_pago(Dinero(Decimal("10000.00")))
        assert cuenta.estado_pago == EstadoPagoEnum.PARCIALMENTE_PAGADO

        saldo_final = cuenta.registrar_pago(Dinero(Decimal("25000.00")))
        assert saldo_final.monto == Decimal("0.00")
        assert cuenta.estado_pago == EstadoPagoEnum.LIQUIDADO
        assert cuenta.esta_liquidada() is True

        with pytest.raises(OperacionFinancieraInvalidaException):
            cuenta.registrar_pago(Dinero(Decimal("100.00")))

    def test_calculo_devolucion_cancelacion_tres_escenarios(self, fecha_base_utc: datetime) -> None:
        fecha_evento = fecha_base_utc + timedelta(days=45)
        monto_base = MontoContractual(
            subtotal=Dinero(Decimal("100000.00")),
            anticipo_pactado=Dinero(Decimal("20000.00")),
            pagos_realizados=Dinero(Decimal("60000.00")),
            total_incrementos=Dinero.cero(),
        )

        # Escenario 1: Más de 30 días de anticipación -> 100% del excedente sobre el anticipo (40,000)
        cuenta_1 = CuentaDePagos(evento_id=uuid4(), monto_contractual=monto_base)
        dev_1 = cuenta_1.calcular_devolucion_cancelacion(
            fecha_cancelacion=fecha_evento - timedelta(days=35),
            fecha_evento=fecha_evento,
        )
        assert dev_1.monto == Decimal("40000.00")
        assert cuenta_1.estado_pago == EstadoPagoEnum.REEMBOLSADO_PARCIAL

        # Escenario 2: Entre 15 y 30 días -> 50% del excedente sobre el anticipo (20,000)
        cuenta_2 = CuentaDePagos(evento_id=uuid4(), monto_contractual=monto_base)
        dev_2 = cuenta_2.calcular_devolucion_cancelacion(
            fecha_cancelacion=fecha_evento - timedelta(days=20),
            fecha_evento=fecha_evento,
        )
        assert dev_2.monto == Decimal("20000.00")
        assert cuenta_2.estado_pago == EstadoPagoEnum.REEMBOLSADO_PARCIAL

        # Escenario 3: Menos de 15 días -> 0% de devolución
        cuenta_3 = CuentaDePagos(evento_id=uuid4(), monto_contractual=monto_base)
        dev_3 = cuenta_3.calcular_devolucion_cancelacion(
            fecha_cancelacion=fecha_evento - timedelta(days=10),
            fecha_evento=fecha_evento,
        )
        assert dev_3.monto == Decimal("0.00")
        assert cuenta_3.estado_pago == EstadoPagoEnum.CANCELADO_SIN_REEMBOLSO


class TestEventoAggregate:
    """Pruebas de invariantes del Aggregate Root Operativo Evento."""

    def test_creacion_evento_fuera_rango_invitados_lanza_excepcion(self, fecha_base_utc: datetime) -> None:
        with pytest.raises(CapacidadInvitadosInvalidaException):
            Evento(
                cliente_id=uuid4(),
                fecha_evento=fecha_base_utc + timedelta(days=20),
                cantidad_invitados=19,
            )

        with pytest.raises(CapacidadInvitadosInvalidaException):
            Evento(
                cliente_id=uuid4(),
                fecha_evento=fecha_base_utc + timedelta(days=20),
                cantidad_invitados=301,
            )

    def test_formalizar_contrato_exitoso_emite_evento_dominio(
        self,
        evento_preliminar_valido: Evento,
        cuenta_pagos_anticipo_cubierto: CuentaDePagos,
        fecha_base_utc: datetime,
    ) -> None:
        evento_preliminar_valido.formalizar_contrato(
            cuenta_pagos=cuenta_pagos_anticipo_cubierto,
            fecha_actual=fecha_base_utc,
        )
        assert evento_preliminar_valido.estado == EstadoEventoEnum.CONFIRMADO

        eventos_dominio = evento_preliminar_valido.pull_domain_events()
        assert len(eventos_dominio) == 1
        assert isinstance(eventos_dominio[0], ContratoFormalizadoEvent)
        assert eventos_dominio[0].evento_id == evento_preliminar_valido.id

    def test_solicitar_cambio_alcance_y_liquidacion_final(
        self,
        evento_preliminar_valido: Evento,
        cuenta_pagos_anticipo_cubierto: CuentaDePagos,
        fecha_base_utc: datetime,
    ) -> None:
        evento_preliminar_valido.formalizar_contrato(
            cuenta_pagos=cuenta_pagos_anticipo_cubierto,
            fecha_actual=fecha_base_utc,
        )
        evento_preliminar_valido.pull_domain_events()

        cotizacion = evento_preliminar_valido.solicitar_cambio_alcance(
            descripcion="30 platillos adicionales",
            invitados_adicionales=30,
            costo_adicional=Dinero(Decimal("18000.00")),
            fecha_solicitud=fecha_base_utc + timedelta(days=5),
        )
        assert cotizacion.estado == EstadoCotizacionEnum.APROBADA
        assert evento_preliminar_valido.cantidad_invitados == 150

        eventos_alcance = evento_preliminar_valido.pull_domain_events()
        assert len(eventos_alcance) == 1
        assert isinstance(eventos_alcance[0], AlcanceModificadoEvent)

        cuenta_pagos_anticipo_cubierto.registrar_incremento_alcance(Dinero(Decimal("18000.00")))
        evento_preliminar_valido.iniciar_ejecucion()
        assert evento_preliminar_valido.estado == EstadoEventoEnum.EN_EJECUCION

        # Intentar liquidar con saldo pendiente debe fallar
        with pytest.raises(ReglaNegocioException):
            evento_preliminar_valido.marcar_liquidado(cuenta_pagos_anticipo_cubierto)

        # Liquidar el saldo restante (70,000 + 18,000 = 88,000)
        cuenta_pagos_anticipo_cubierto.registrar_pago(Dinero(Decimal("88000.00")))
        evento_preliminar_valido.marcar_liquidado(cuenta_pagos_anticipo_cubierto)
        assert evento_preliminar_valido.estado == EstadoEventoEnum.FINALIZADO

        eventos_liq = evento_preliminar_valido.pull_domain_events()
        assert len(eventos_liq) == 1
        assert isinstance(eventos_liq[0], EventoLiquidadoEvent)

    def test_evaluacion_sla_48h_proveedores(self, fecha_base_utc: datetime) -> None:
        evento = Evento(
            cliente_id=uuid4(),
            fecha_evento=fecha_base_utc + timedelta(days=30),
            cantidad_invitados=100,
        )
        prov_id = uuid4()
        evento.asignar_proveedor(
            proveedor_id=prov_id,
            nombre_servicio="Iluminación Arquitectónica",
            fecha_asignacion=fecha_base_utc,
        )

        # A las 49 horas debe vencer por SLA (BR-04)
        vencidos = evento.evaluar_sla_proveedores(fecha_corte=fecha_base_utc + timedelta(hours=49))
        assert len(vencidos) == 1
        assert vencidos[0].estado == EstadoAsignacionProveedorEnum.VENCIDO

        eventos_sla = evento.pull_domain_events()
        assert len(eventos_sla) == 1
        assert isinstance(eventos_sla[0], ProveedorVencidoSLAEvent)

    def test_confirmar_proveedor_fuera_de_sla_lanza_plazo_vencido(self, fecha_base_utc: datetime) -> None:
        evento = Evento(
            cliente_id=uuid4(),
            fecha_evento=fecha_base_utc + timedelta(days=30),
            cantidad_invitados=80,
        )
        prov_id = uuid4()
        evento.asignar_proveedor(
            proveedor_id=prov_id,
            nombre_servicio="DJ y Audio",
            fecha_asignacion=fecha_base_utc,
        )
        with pytest.raises(PlazoVencidoException):
            evento.confirmar_proveedor(
                proveedor_id=prov_id,
                fecha_confirmacion=fecha_base_utc + timedelta(hours=50),
            )

        with pytest.raises(EntidadNoEncontradaException):
            evento.confirmar_proveedor(
                proveedor_id=uuid4(),
                fecha_confirmacion=fecha_base_utc + timedelta(hours=10),
            )

    def test_cotizacion_rechazo_y_auditoria_invariantes(self) -> None:
        cot = CotizacionIncremento(
            descripcion="Pista iluminada LED",
            invitados_adicionales=0,
            costo_adicional=Dinero(Decimal("12000.00")),
        )
        cot.rechazar()
        assert cot.estado == EstadoCotizacionEnum.RECHAZADA

        with pytest.raises(ReglaNegocioException):
            cot.aprobar()

        log = LogAuditoria(
            entidad_id=uuid4(),
            tipo_entidad="Evento",
            accion="CAMBIO_ESTADO",
            estado_anterior="BORRADOR",
            estado_nuevo="PENDIENTE_ANTICIPO",
        )
        assert log.tipo_entidad == "Evento"

        with pytest.raises(ReglaNegocioException):
            LogAuditoria(
                entidad_id=uuid4(),
                tipo_entidad="",
                accion="ACCION",
                estado_anterior=None,
                estado_nuevo="NUEVO",
            )
