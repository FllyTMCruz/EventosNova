# tests/integration/test_api_endpoints.py
from decimal import Decimal
from uuid import uuid4
from fastapi.testclient import TestClient


class TestFastAPIEndpoints:
    """Pruebas de integración extremo a extremo (E2E) sobre los routers REST con TestClient."""

    def test_health_check_endpoint(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "eventos-nova-api",
            "equipo": "16",
        }

        resp_ui = client.get("/interfaz-prueba")
        assert resp_ui.status_code == 200
        assert "INTERFAZ DE PRUEBA" in resp_ui.text

    def test_flujo_completo_rest_creacion_pago_formalizacion_alcance_y_auditoria(self, client: TestClient) -> None:
        cliente_id = str(uuid4())
        proveedor_id = str(uuid4())
        usuario_id = str(uuid4())

        # 1. Crear evento preliminar (POST /eventos)
        payload_creacion = {
            "cliente_id": cliente_id,
            "fecha_evento": "2027-06-20T19:00:00Z",
            "cantidad_invitados": 150,
            "subtotal_contrato": "120000.00",
            "anticipo_pactado": "36000.00",
            "moneda": "MXN",
            "proveedores_iniciales": [
                {
                    "proveedor_id": proveedor_id,
                    "nombre_servicio": "Banquete Real Nova",
                    "confirmado": True,
                }
            ],
            "usuario_id": usuario_id,
        }
        resp_crear = client.post("/eventos", json=payload_creacion)
        assert resp_crear.status_code == 201
        datos_evento = resp_crear.json()
        evento_id = datos_evento["evento_id"]
        assert datos_evento["estado_evento"] == "PENDIENTE_ANTICIPO"
        assert datos_evento["estado_pago"] == "PENDIENTE_ANTICIPO"

        # 2. Intentar formalizar sin haber pagado el anticipo -> Debe retornar 409 Conflict (BR-07)
        resp_form_fallida = client.post(
            f"/eventos/{evento_id}/formalizar",
            json={"usuario_id": usuario_id, "fecha_operacion": "2027-05-01T12:00:00Z"},
        )
        assert resp_form_fallida.status_code == 409
        assert resp_form_fallida.json()["codigo"] == "REQUISITO_FORMALIZACION_FALTANTE"

        # 3. Registrar pago del anticipo pactado (POST /eventos/{id}/pagos)
        resp_pago = client.post(
            f"/eventos/{evento_id}/pagos",
            json={
                "monto": "36000.00",
                "moneda": "MXN",
                "referencia_pago": "SPEI-ANTICIPO-001",
                "usuario_id": usuario_id,
            },
        )
        assert resp_pago.status_code == 200
        datos_pago = resp_pago.json()
        assert datos_pago["anticipo_cubierto"] is True
        assert datos_pago["estado_pago_actual"] == "ANTICIPO_CUBIERTO"
        assert Decimal(datos_pago["saldo_pendiente"]) == Decimal("84000.00")

        # 4. Formalizar contrato exitosamente (POST /eventos/{id}/formalizar)
        resp_formalizar = client.post(
            f"/eventos/{evento_id}/formalizar",
            json={"usuario_id": usuario_id, "fecha_operacion": "2027-05-02T12:00:00Z"},
        )
        assert resp_formalizar.status_code == 200
        datos_form = resp_formalizar.json()
        assert datos_form["estado_actual"] == "CONFIRMADO"

        # 5. Solicitar cambio de alcance válido (POST /eventos/{id}/cambios-alcance)
        resp_alcance = client.post(
            f"/eventos/{evento_id}/cambios-alcance",
            json={
                "descripcion": "25 invitados extra y barra de coctelería",
                "invitados_adicionales": 25,
                "costo_adicional": "20000.00",
                "moneda": "MXN",
                "porcentaje_anticipo_adicional": "0.00",
                "usuario_id": usuario_id,
                "fecha_solicitud": "2027-06-01T10:00:00Z",
            },
        )
        assert resp_alcance.status_code == 200
        datos_alcance = resp_alcance.json()
        assert datos_alcance["invitados_actualizados"] == 175
        assert Decimal(datos_alcance["nuevo_monto_total_contrato"]) == Decimal("140000.00")
        assert Decimal(datos_alcance["nuevo_saldo_pendiente"]) == Decimal("104000.00")

        # 6. Consultar saldo pendiente (GET /eventos/{id}/saldo)
        resp_saldo = client.get(f"/eventos/{evento_id}/saldo")
        assert resp_saldo.status_code == 200
        datos_saldo = resp_saldo.json()
        assert Decimal(datos_saldo["saldo_pendiente"]) == Decimal("104000.00")
        assert datos_saldo["estado_evento"] == "CONFIRMADO"

        # 7. Consultar historial completo de auditoría (GET /eventos/{id}/auditoria)
        resp_auditoria = client.get(f"/eventos/{evento_id}/auditoria")
        assert resp_auditoria.status_code == 200
        datos_aud = resp_auditoria.json()
        assert datos_aud["total_registros"] == 4
        acciones = [r["accion"] for r in datos_aud["registros"]]
        assert "CREACION_EVENTO_PRELIMINAR" in acciones
        assert "REGISTRO_PAGO" in acciones
        assert "FORMALIZACION_CONTRATO_BR07" in acciones
        assert "CAMBIO_ALCANCE_BR02_BR12" in acciones

    def test_codigos_error_http_404_y_422_en_endpoints(self, client: TestClient) -> None:
        id_inexistente = str(uuid4())

        # 404 en consulta de saldo de evento inexistente
        resp_404 = client.get(f"/eventos/{id_inexistente}/saldo")
        assert resp_404.status_code == 404
        assert resp_404.json()["codigo"] == "ENTIDAD_NO_ENCONTRADA"

        # 422 al intentar crear un evento con 450 invitados (viola BR-05: máx 300)
        resp_422 = client.post(
            "/eventos",
            json={
                "cliente_id": str(uuid4()),
                "fecha_evento": "2027-08-15T20:00:00Z",
                "cantidad_invitados": 450,
                "subtotal_contrato": "90000.00",
                "anticipo_pactado": "27000.00",
                "moneda": "MXN",
                "proveedores_iniciales": [],
            },
        )
        assert resp_422.status_code == 422
        assert resp_422.json()["codigo"] == "CAPACIDAD_INVITADOS_INVALIDA"

    def test_asignar_proveedor_y_evaluar_sla_endpoint(self, client: TestClient) -> None:
        resp_crear = client.post(
            "/eventos",
            json={
                "cliente_id": str(uuid4()),
                "fecha_evento": "2027-09-10T20:00:00Z",
                "cantidad_invitados": 80,
                "subtotal_contrato": "60000.00",
                "anticipo_pactado": "18000.00",
                "moneda": "MXN",
                "proveedores_iniciales": [],
            },
        )
        evento_id = resp_crear.json()["evento_id"]

        resp_prov = client.post(
            f"/eventos/{evento_id}/proveedores",
            json={
                "proveedor_id": str(uuid4()),
                "nombre_servicio": "Grupo Musical Versátil",
                "confirmar_inmediatamente": False,
            },
        )
        assert resp_prov.status_code == 201
        assert resp_prov.json()["estado"] == "ASIGNADO"

        resp_sla = client.post(
            "/eventos/evaluar-sla-proveedores",
            json={"fecha_corte": "2028-01-01T00:00:00Z"},
        )
        assert resp_sla.status_code == 200
        assert resp_sla.json()["total_asignaciones_vencidas"] == 1

    def test_confirmar_proveedor_finalizar_y_cancelar_endpoints(self, client: TestClient) -> None:
        # 1. Crear evento con 1 proveedor sin confirmar aún
        prov_id = str(uuid4())
        resp_crear = client.post(
            "/eventos",
            json={
                "cliente_id": str(uuid4()),
                "fecha_evento": "2027-10-20T20:00:00Z",
                "cantidad_invitados": 100,
                "subtotal_contrato": "100000.00",
                "anticipo_pactado": "30000.00",
                "moneda": "MXN",
                "proveedores_iniciales": [
                    {
                        "proveedor_id": prov_id,
                        "nombre_servicio": "Catering Ejecutivo",
                        "confirmado": False,
                    }
                ],
            },
        )
        assert resp_crear.status_code == 201
        evento_id = resp_crear.json()["evento_id"]

        # 2. Confirmar proveedor dentro del SLA (US-04 / BR-04)
        resp_conf = client.post(
            f"/eventos/{evento_id}/proveedores/{prov_id}/confirmar",
            json={},
        )
        assert resp_conf.status_code == 200
        assert resp_conf.json()["estado"] == "CONFIRMADO"

        # 3. Pagar 100% del contrato y formalizar
        client.post(
            f"/eventos/{evento_id}/pagos",
            json={"monto": "100000.00", "moneda": "MXN", "referencia_pago": "PAGO-TOTAL"},
        )
        client.post(f"/eventos/{evento_id}/formalizar", json={"fecha_operacion": "2027-09-01T12:00:00Z"})

        # 4. Finalizar evento liquidado (US-08, US-15 / BR-06)
        resp_fin = client.post(f"/eventos/{evento_id}/finalizar", json={})
        assert resp_fin.status_code == 200
        assert resp_fin.json()["estado_actual"] == "FINALIZADO"

        # 5. Crear segundo evento, pagar $50,000 y cancelar >30 días antes (BR-03)
        resp_crear2 = client.post(
            "/eventos",
            json={
                "cliente_id": str(uuid4()),
                "fecha_evento": "2027-11-20T20:00:00Z",
                "cantidad_invitados": 100,
                "subtotal_contrato": "100000.00",
                "anticipo_pactado": "30000.00",
                "moneda": "MXN",
                "proveedores_iniciales": [],
            },
        )
        ev2_id = resp_crear2.json()["evento_id"]
        client.post(f"/eventos/{ev2_id}/pagos", json={"monto": "50000.00", "moneda": "MXN"})

        resp_canc = client.post(
            f"/eventos/{ev2_id}/cancelar",
            json={"fecha_cancelacion": "2027-10-01T12:00:00Z", "motivo": "Cambio de planes"},
        )
        assert resp_canc.status_code == 200
        assert resp_canc.json()["estado_evento_actual"] == "CANCELADO"
        assert resp_canc.json()["estado_pago_actual"] == "REEMBOLSADO_PARCIAL"
        assert Decimal(resp_canc.json()["monto_devolucion"]) == Decimal("20000.00")
