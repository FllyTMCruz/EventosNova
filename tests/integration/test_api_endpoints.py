# tests/integration/test_api_endpoints.py
from uuid import uuid4
from fastapi.testclient import TestClient


class TestFastAPIEndpoints:
    """Pruebas de integración extremo a extremo (E2E) verificando respuestas claras con único campo `message`."""

    def test_health_check_endpoint(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert list(body.keys()) == ["message"]
        assert "en línea" in body["message"]

        resp_ui = client.get("/interfaz-prueba")
        assert resp_ui.status_code == 200
        assert "INTERFAZ DE PRUEBA" in resp_ui.text

    def test_flujo_completo_rest_creacion_pago_formalizacion_alcance_y_auditoria(self, client: TestClient) -> None:
        cliente_id = str(uuid4())
        proveedor_id = str(uuid4())
        usuario_id = str(uuid4())

        # 1. Crear evento preliminar (POST /eventos) -> único campo `message`
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
        assert list(datos_evento.keys()) == ["message"]
        assert "150 invitados" in datos_evento["message"]
        evento_id = resp_crear.headers["X-Evento-Id"]

        # 2. Intentar formalizar sin haber pagado el anticipo -> 409 con único campo `message`
        resp_form_fallida = client.post(
            f"/eventos/{evento_id}/formalizar",
            json={"usuario_id": usuario_id, "fecha_operacion": "2027-05-01T12:00:00Z"},
        )
        assert resp_form_fallida.status_code == 409
        assert list(resp_form_fallida.json().keys()) == ["message"]
        assert "anticipo" in resp_form_fallida.json()["message"].lower()

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
        assert list(datos_pago.keys()) == ["message"]
        assert "anticipo requerido ya se encuentra cubierto" in datos_pago["message"]
        assert "$84,000.00" in datos_pago["message"]

        # 4. Formalizar contrato exitosamente (POST /eventos/{id}/formalizar)
        resp_formalizar = client.post(
            f"/eventos/{evento_id}/formalizar",
            json={"usuario_id": usuario_id, "fecha_operacion": "2027-05-02T12:00:00Z"},
        )
        assert resp_formalizar.status_code == 200
        datos_form = resp_formalizar.json()
        assert list(datos_form.keys()) == ["message"]
        assert "formalizado" in datos_form["message"]

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
        assert list(datos_alcance.keys()) == ["message"]
        assert "175 personas" in datos_alcance["message"]
        assert "$140,000.00" in datos_alcance["message"]
        assert "$104,000.00" in datos_alcance["message"]

        # 6. Consultar saldo pendiente (GET /eventos/{id}/saldo)
        resp_saldo = client.get(f"/eventos/{evento_id}/saldo")
        assert resp_saldo.status_code == 200
        datos_saldo = resp_saldo.json()
        assert list(datos_saldo.keys()) == ["message"]
        assert "$104,000.00" in datos_saldo["message"]
        assert "confirmado" in datos_saldo["message"]

        # 7. Consultar historial completo de auditoría (GET /eventos/{id}/auditoria)
        resp_auditoria = client.get(f"/eventos/{evento_id}/auditoria")
        assert resp_auditoria.status_code == 200
        datos_aud = resp_auditoria.json()
        assert list(datos_aud.keys()) == ["message"]
        assert "4 movimiento(s)" in datos_aud["message"]

    def test_codigos_error_http_404_y_422_en_endpoints(self, client: TestClient) -> None:
        id_inexistente = str(uuid4())

        # 404 en consulta de saldo de evento inexistente -> único campo `message`
        resp_404 = client.get(f"/eventos/{id_inexistente}/saldo")
        assert resp_404.status_code == 404
        assert list(resp_404.json().keys()) == ["message"]
        assert "No se encontró" in resp_404.json()["message"]

        # 422 al intentar crear un evento con 450 invitados -> único campo `message`
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
        assert list(resp_422.json().keys()) == ["message"]
        assert "entre 20 y 300 invitados" in resp_422.json()["message"]

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
        evento_id = resp_crear.headers["X-Evento-Id"]

        resp_prov = client.post(
            f"/eventos/{evento_id}/proveedores",
            json={
                "proveedor_id": str(uuid4()),
                "nombre_servicio": "Grupo Musical Versátil",
                "confirmar_inmediatamente": False,
            },
        )
        assert resp_prov.status_code == 201
        assert list(resp_prov.json().keys()) == ["message"]
        assert "48 horas" in resp_prov.json()["message"]

        resp_sla = client.post(
            "/eventos/evaluar-sla-proveedores",
            json={"fecha_corte": "2028-01-01T00:00:00Z"},
        )
        assert resp_sla.status_code == 200
        assert list(resp_sla.json().keys()) == ["message"]
        assert "1 proveedor(es)" in resp_sla.json()["message"]

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
        evento_id = resp_crear.headers["X-Evento-Id"]

        # 2. Confirmar proveedor dentro del SLA
        resp_conf = client.post(
            f"/eventos/{evento_id}/proveedores/{prov_id}/confirmar",
            json={},
        )
        assert resp_conf.status_code == 200
        assert list(resp_conf.json().keys()) == ["message"]
        assert "ha confirmado su participación" in resp_conf.json()["message"]

        # 3. Pagar 100% del contrato y formalizar
        client.post(
            f"/eventos/{evento_id}/pagos",
            json={"monto": "100000.00", "moneda": "MXN", "referencia_pago": "PAGO-TOTAL"},
        )
        client.post(f"/eventos/{evento_id}/formalizar", json={"fecha_operacion": "2027-09-01T12:00:00Z"})

        # 4. Finalizar evento liquidado
        resp_fin = client.post(f"/eventos/{evento_id}/finalizar", json={})
        assert resp_fin.status_code == 200
        assert list(resp_fin.json().keys()) == ["message"]
        assert "cerrado exitosamente" in resp_fin.json()["message"]

        # 5. Crear segundo evento, pagar $50,000 y cancelar >30 días antes
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
        ev2_id = resp_crear2.headers["X-Evento-Id"]
        client.post(f"/eventos/{ev2_id}/pagos", json={"monto": "50000.00", "moneda": "MXN"})

        resp_canc = client.post(
            f"/eventos/{ev2_id}/cancelar",
            json={"fecha_cancelacion": "2027-10-01T12:00:00Z", "motivo": "Cambio de planes"},
        )
        assert resp_canc.status_code == 200
        assert list(resp_canc.json().keys()) == ["message"]
        assert "cancelado conforme a su solicitud" in resp_canc.json()["message"]
        assert "$20,000.00" in resp_canc.json()["message"]
