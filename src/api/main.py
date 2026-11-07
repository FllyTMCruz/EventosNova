# src/api/main.py
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from src.api.routers import auditoria_router, eventos_router, pagos_router
from src.api.schemas import MensajeResponseSchema
from src.domain.exceptions import (
    CapacidadInvitadosInvalidaException,
    DomainException,
    EntidadNoEncontradaException,
    LimiteProveedoresExcedidoException,
    OperacionFinancieraInvalidaException,
    PlazoVencidoException,
    ReglaNegocioException,
    RequisitoFormalizacionFaltanteException,
    TransicionInvalidaException,
)
from src.infrastructure.config.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa las tablas de la base de datos al arrancar el servidor."""
    init_db()
    yield


app = FastAPI(
    title="Eventos Nova API - Gestión de Eventos y Contratos (Equipo 16)",
    description=(
        "Sistema de gestión de eventos sociales con respuestas claras y amigables "
        "para el usuario final. Cada operación informa su resultado mediante un único "
        "campo `message` fácil de leer, sin exponer códigos técnicos ni identificadores internos."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Evento-Id", "X-Proveedor-Id"],
)


# ==============================================================================
# MANEJADORES DE EXCEPCIONES CON MENSAJES CLAROS PARA EL USUARIO COMÚN
# Todos los errores devuelven únicamente {"message": "..."} en lenguaje natural,
# ocultando IDs, códigos internos o nombres técnicos de estados.
# ==============================================================================


@app.exception_handler(EntidadNoEncontradaException)
async def entidad_no_encontrada_handler(_: Request, __: EntidadNoEncontradaException) -> JSONResponse:
    # Informa de manera sencilla que el evento o proveedor buscado no existe aún
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "message": (
                "No se encontró la información del evento o proveedor solicitado. "
                "Por favor verifique que el evento haya sido registrado previamente."
            )
        },
    )


@app.exception_handler(RequisitoFormalizacionFaltanteException)
async def requisito_formalizacion_handler(_: Request, __: RequisitoFormalizacionFaltanteException) -> JSONResponse:
    # Explica al usuario en lenguaje cotidiano qué falta para poder confirmar su contrato
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "message": (
                "Aún no es posible formalizar y confirmar su contrato. Para hacerlo, "
                "asegúrese de haber pagado primero el anticipo mínimo acordado y de que "
                "todos los proveedores asignados hayan confirmado su participación."
            )
        },
    )


@app.exception_handler(TransicionInvalidaException)
async def transicion_invalida_handler(_: Request, exc: TransicionInvalidaException) -> JSONResponse:
    # Traduce las transiciones de estado a una explicación comprensible para cualquier persona
    if exc.estado_destino == "FINALIZADO" or exc.estado_destino == "EN_EJECUCION":
        texto = (
            "No se puede finalizar el evento todavía porque el contrato aún no ha sido "
            "confirmado o el evento ya fue cerrado anteriormente."
        )
    elif exc.estado_actual == "CANCELADO":
        texto = "Esta acción no se puede realizar porque el evento ya fue cancelado previamente."
    elif exc.estado_actual == "FINALIZADO":
        texto = "Esta acción no se puede realizar porque el evento ya concluyó y se encuentra cerrado."
    else:
        texto = (
            "Esta acción no se puede realizar en la etapa actual del evento. "
            "Por favor revise que los pasos previos (como el pago del anticipo o la "
            "confirmación del contrato) ya se hayan completado."
        )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"message": texto},
    )


@app.exception_handler(LimiteProveedoresExcedidoException)
async def limite_proveedores_handler(_: Request, __: LimiteProveedoresExcedidoException) -> JSONResponse:
    # Informa claramente el tope máximo de 15 proveedores por evento
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "message": (
                "No es posible agregar más proveedores a su evento, ya que se alcanzó "
                "el máximo permitido de 15 servicios contratados."
            )
        },
    )


@app.exception_handler(PlazoVencidoException)
async def plazo_vencido_handler(_: Request, exc: PlazoVencidoException) -> JSONResponse:
    # Explica con claridad si venció el plazo de 7 días para cambios o el de 48 horas del proveedor
    if "48" in exc.detalle_plazo or "proveedor" in exc.operacion.lower():
        texto = (
            "El plazo de 48 horas para que este proveedor confirmara su asistencia ya venció. "
            "Por favor asigne un proveedor diferente para cubrir este servicio."
        )
    else:
        texto = (
            "No es posible realizar cambios en el evento porque faltan menos de 7 días "
            "para su celebración. Cualquier ajuste de invitados o servicios debe solicitarse "
            "con al menos una semana de anticipación."
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": texto},
    )


@app.exception_handler(CapacidadInvitadosInvalidaException)
async def capacidad_invitados_handler(_: Request, exc: CapacidadInvitadosInvalidaException) -> JSONResponse:
    # Indica al usuario el rango permitido de invitados sin mencionar códigos técnicos
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": (
                f"La cantidad de {exc.cantidad_solicitada} invitados no está permitida. "
                "Para ofrecerle un servicio adecuado, el evento debe tener entre 20 y 300 invitados."
            )
        },
    )


@app.exception_handler(OperacionFinancieraInvalidaException)
async def operacion_financiera_handler(_: Request, exc: OperacionFinancieraInvalidaException) -> JSONResponse:
    # Explica de forma amigable cualquier inconveniente con pagos o liquidación pendiente
    msg_lower = exc.mensaje.lower()
    if "liquidada" in msg_lower or "saldo" in msg_lower and "finalizar" in msg_lower:
        texto = (
            "No es posible finalizar y cerrar el evento porque aún existe un saldo pendiente "
            "por pagar. La cuenta debe estar liquidada al 100% para concluir el evento."
        )
    elif "excede" in msg_lower or "supera" in msg_lower:
        texto = (
            "El monto del pago ingresado supera el saldo pendiente actual del evento. "
            "Por favor ingrese un monto igual o menor al total restante por pagar."
        )
    else:
        texto = (
            "No se pudo completar la operación de pago porqueún existe un saldo pendiente "
            "por cubrir o el monto ingresado no es válido. Por favor verifique el importe."
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": texto},
    )


@app.exception_handler(ReglaNegocioException)
async def regla_negocio_general_handler(_: Request, exc: ReglaNegocioException) -> JSONResponse:
    # Mensaje claro ante cualquier otra validación del proceso del evento
    msg_lower = exc.mensaje.lower()
    if "liquid" in msg_lower or "saldo" in msg_lower:
        texto = (
            "No es posible finalizar y cerrar el evento todavía porque aún existe un saldo "
            "pendiente por pagar. La cuenta debe estar liquidada al 100% antes de concluir el evento."
        )
    else:
        texto = (
            "No se pudo realizar la operación porque el evento aún no cumple con "
            "todas las condiciones necesarias en esta etapa. Verifique que el contrato "
            "esté confirmado y al corriente."
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": texto},
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(_: Request, __: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "message": (
                "No fue posible procesar su solicitud con los datos proporcionados. "
                "Por favor revise la información e inténtelo nuevamente."
            )
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    # Reemplaza el error técnico de validación por un mensaje sencillo para el usuario
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": (
                "Algunos de los datos ingresados tienen un formato incorrecto o están incompletos. "
                "Por favor verifique las cantidades, fechas y montos antes de continuar."
            )
        },
    )


app.include_router(eventos_router)
app.include_router(pagos_router)
app.include_router(auditoria_router)


@app.get(
    "/health",
    response_model=MensajeResponseSchema,
    tags=["Estado del Sistema"],
    summary="Verificar que el sistema está en línea",
)
def health_check() -> MensajeResponseSchema:
    # Devuelve únicamente un mensaje claro confirmando que el servicio opera con normalidad
    return MensajeResponseSchema(
        message="El sistema de gestión de Eventos Nova se encuentra en línea y funcionando correctamente."
    )


@app.get("/", include_in_schema=False)
@app.get("/interfaz-prueba", include_in_schema=False)
def servir_interfaz_prueba() -> FileResponse:
    """Sirve la consola web de demostración con mensajes claros para el usuario."""
    ruta_html = Path(__file__).resolve().parent / "interfaz_prueba.html"
    return FileResponse(ruta_html, media_type="text/html")
