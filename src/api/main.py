# src/api/main.py
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from src.api.routers import auditoria_router, eventos_router, pagos_router
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
    title="Eventos Nova API - Componentes de Lógica de Negocios (Equipo 16)",
    description=(
        "API REST con Arquitectura Limpia y Domain-Driven Design (DDD) para la gestión "
        "de contratos de eventos sociales, control de proveedores con SLA de 48h, "
        "modificaciones de alcance, cuentas de pago y auditoría inmutable (ADR-003)."
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
)


@app.exception_handler(EntidadNoEncontradaException)
async def entidad_no_encontrada_handler(_: Request, exc: EntidadNoEncontradaException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": None,
        },
    )


@app.exception_handler(RequisitoFormalizacionFaltanteException)
async def requisito_formalizacion_handler(_: Request, exc: RequisitoFormalizacionFaltanteException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": exc.motivos,
        },
    )


@app.exception_handler(TransicionInvalidaException)
async def transicion_invalida_handler(_: Request, exc: TransicionInvalidaException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": [
                f"Entidad: {exc.entidad}",
                f"Estado actual: {exc.estado_actual}",
                f"Estado solicitado: {exc.estado_destino}",
            ],
        },
    )


@app.exception_handler(LimiteProveedoresExcedidoException)
async def limite_proveedores_handler(_: Request, exc: LimiteProveedoresExcedidoException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": None,
        },
    )


@app.exception_handler(PlazoVencidoException)
async def plazo_vencido_handler(_: Request, exc: PlazoVencidoException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": [exc.detalle_plazo],
        },
    )


@app.exception_handler(CapacidadInvitadosInvalidaException)
async def capacidad_invitados_handler(_: Request, exc: CapacidadInvitadosInvalidaException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": None,
        },
    )


@app.exception_handler(OperacionFinancieraInvalidaException)
async def operacion_financiera_handler(_: Request, exc: OperacionFinancieraInvalidaException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": None,
        },
    )


@app.exception_handler(ReglaNegocioException)
async def regla_negocio_general_handler(_: Request, exc: ReglaNegocioException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": None,
        },
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(_: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": None,
        },
    )


app.include_router(eventos_router)
app.include_router(pagos_router)
app.include_router(auditoria_router)


@app.get("/health", tags=["Infraestructura"], summary="Verificar estado del servicio")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "eventos-nova-api", "equipo": "16"}


@app.get("/", include_in_schema=False)
@app.get("/interfaz-prueba", include_in_schema=False)
def servir_interfaz_prueba() -> FileResponse:
    """Sirve el archivo único HTML minimalista etiquetado como INTERFAZ DE PRUEBA para la demostración."""
    ruta_html = Path(__file__).resolve().parent / "interfaz_prueba.html"
    return FileResponse(ruta_html, media_type="text/html")
