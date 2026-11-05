# tests/integration/test_use_cases.py
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from src.application.dtos.comandos import (
    FormalizarContratoCommand,
    ProcesarCambioAlcanceCommand,
)
from src.application.dtos.consultas import ConsultarSaldoPendienteQuery
from src.application.use_cases.consultar_saldo_pendiente import (
    ConsultarSaldoPendienteHandler,
)
from src.application.use_cases.evaluar_sla_proveedores import (
    EvaluarSLAProveedoresScheduler,
)
from src.application.use_cases.formalizar_contrato import FormalizarContratoHandler
from src.application.use_cases.procesar_cambio_alcance import (
    ProcesarCambioAlcanceHandler,
)
from src.domain.events import (
    AlcanceModificadoEvent,
    ContratoFormalizadoEvent,
)
from src.domain.exceptions import (
    PlazoVencidoException,
)
from src.domain.models.cuenta_pagos import CuentaDePagos
from src.domain.models.evento import Evento
from src.infrastructure.persistence.unit_of_work import (
    InMemoryDomainEventBus,
    SqlAlchemyUnitOfWork,
)


class TestUseCasesIntegration:
    """Pruebas de integración de los Handlers de aplicación con SQLite en memoria y UnitOfWork."""

    def test_flujo_completo_formalizar_cambio_alcance_y_consulta_saldo(
        self,
        uow: SqlAlchemyUnitOfWork,
        event_bus: InMemoryDomainEventBus,
        evento_preliminar_valido: Evento,
        cuenta_pagos_anticipo_cubierto: CuentaDePagos,
        fecha_base_utc: datetime,
    ) -> None:
        # 1. Persistir estado inicial en base de datos SQLite en memoria
        with uow:
            uow.eventos.guardar(evento_preliminar_valido)
            uow.cuentas_pagos.guardar(cuenta_pagos_anticipo_cubierto)
            uow.commit()

        # 2. Ejecutar FormalizarContratoHandler (CU-03 / BR-07)
        formalizar_handler = FormalizarContratoHandler(uow=uow)
        usuario_operador = uuid4()
        dto_formalizado = formalizar_handler.handle(
            FormalizarContratoCommand(
                evento_id=evento_preliminar_valido.id,
                usuario_id=usuario_operador,
                fecha_operacion=fecha_base_utc,
            )
        )

        assert dto_formalizado.estado_anterior == "PENDIENTE_ANTICIPO"
        assert dto_formalizado.estado_actual == "CONFIRMADO"
        assert dto_formalizado.saldo_pendiente == Decimal("70000.00")
        assert any(isinstance(ev, ContratoFormalizadoEvent) for ev in event_bus.historial_publicados)

        # 3. Ejecutar ProcesarCambioAlcanceHandler (CU-04 / BR-02, BR-12)
        alcance_handler = ProcesarCambioAlcanceHandler(uow=uow)
        dto_alcance = alcance_handler.handle(
            ProcesarCambioAlcanceCommand(
                evento_id=evento_preliminar_valido.id,
                descripcion="Incremento de 40 invitados y estación de café",
                invitados_adicionales=40,
                costo_adicional=Decimal("24000.00"),
                moneda="MXN",
                usuario_id=usuario_operador,
                fecha_solicitud=fecha_base_utc + timedelta(days=2),
            )
        )

        assert dto_alcance.invitados_anteriores == 120
        assert dto_alcance.invitados_actualizados == 160
        assert dto_alcance.nuevo_monto_total_contrato == Decimal("124000.00")
        assert dto_alcance.nuevo_saldo_pendiente == Decimal("94000.00")
        assert any(isinstance(ev, AlcanceModificadoEvent) for ev in event_bus.historial_publicados)

        # 4. Ejecutar ConsultarSaldoPendienteHandler (CU-05)
        saldo_handler = ConsultarSaldoPendienteHandler(uow=uow)
        dto_saldo = saldo_handler.handle(ConsultarSaldoPendienteQuery(evento_id=evento_preliminar_valido.id))

        assert dto_saldo.subtotal_base == Decimal("100000.00")
        assert dto_saldo.total_incrementos == Decimal("24000.00")
        assert dto_saldo.monto_total_actualizado == Decimal("124000.00")
        assert dto_saldo.pagos_realizados == Decimal("30000.00")
        assert dto_saldo.saldo_pendiente == Decimal("94000.00")
        assert dto_saldo.anticipo_cubierto is True
        assert dto_saldo.esta_liquidado is False

        # 5. Verificar registros inmutables en LogAuditoria (ADR-003)
        with uow:
            logs = uow.auditoria.listar_por_entidad(evento_preliminar_valido.id)
            assert len(logs) == 2
            assert logs[0].accion == "FORMALIZACION_CONTRATO_BR07"
            assert logs[1].accion == "CAMBIO_ALCANCE_BR02_BR12"

    def test_rollback_atomico_cuando_falla_cambio_alcance_por_plazo(
        self,
        uow: SqlAlchemyUnitOfWork,
        evento_preliminar_valido: Evento,
        cuenta_pagos_anticipo_cubierto: CuentaDePagos,
        fecha_base_utc: datetime,
    ) -> None:
        with uow:
            uow.eventos.guardar(evento_preliminar_valido)
            uow.cuentas_pagos.guardar(cuenta_pagos_anticipo_cubierto)
            uow.commit()

        FormalizarContratoHandler(uow=uow).handle(
            FormalizarContratoCommand(
                evento_id=evento_preliminar_valido.id,
                fecha_operacion=fecha_base_utc,
            )
        )

        # Solicitar cambio de alcance 3 días antes del evento (viola BR-02 de 7 días)
        fecha_fuera_plazo = evento_preliminar_valido.fecha_evento - timedelta(days=3)
        with pytest.raises(PlazoVencidoException):
            ProcesarCambioAlcanceHandler(uow=uow).handle(
                ProcesarCambioAlcanceCommand(
                    evento_id=evento_preliminar_valido.id,
                    descripcion="Cambio extemporáneo",
                    invitados_adicionales=10,
                    costo_adicional=Decimal("5000.00"),
                    fecha_solicitud=fecha_fuera_plazo,
                )
            )

        # Verificar que el aforo y el saldo no sufrieron alteraciones
        dto_saldo = ConsultarSaldoPendienteHandler(uow=uow).handle(
            ConsultarSaldoPendienteQuery(evento_id=evento_preliminar_valido.id)
        )
        assert dto_saldo.total_incrementos == Decimal("0.00")

    def test_scheduler_evaluacion_sla_proveedores_integracion(
        self,
        uow: SqlAlchemyUnitOfWork,
        fecha_base_utc: datetime,
    ) -> None:
        evento = Evento(
            cliente_id=uuid4(),
            fecha_evento=fecha_base_utc + timedelta(days=45),
            cantidad_invitados=90,
            fecha_creacion=fecha_base_utc,
        )
        evento.asignar_proveedor(
            proveedor_id=uuid4(),
            nombre_servicio="Floristería Imperial",
            fecha_asignacion=fecha_base_utc,
        )
        with uow:
            uow.eventos.guardar(evento)
            uow.commit()

        scheduler = EvaluarSLAProveedoresScheduler(uow=uow)
        resultado = scheduler.ejecutar(fecha_corte=fecha_base_utc + timedelta(hours=52))

        assert resultado.eventos_evaluados == 1
        assert resultado.total_asignaciones_vencidas == 1
        assert resultado.proveedores_vencidos[0].nombre_servicio == "Floristería Imperial"
