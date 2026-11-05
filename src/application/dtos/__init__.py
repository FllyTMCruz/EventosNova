# src/application/dtos/__init__.py
from src.application.dtos.comandos import (
    FormalizarContratoCommand,
    ContratoFormalizadoDTO,
    ProcesarCambioAlcanceCommand,
    CambioAlcanceProcesadoDTO,
)
from src.application.dtos.consultas import (
    ConsultarSaldoPendienteQuery,
    SaldoPendienteResponseDTO,
    ProveedorVencidoDTO,
    ResultadoEvaluacionSLADTO,
)

__all__ = [
    "FormalizarContratoCommand",
    "ContratoFormalizadoDTO",
    "ProcesarCambioAlcanceCommand",
    "CambioAlcanceProcesadoDTO",
    "ConsultarSaldoPendienteQuery",
    "SaldoPendienteResponseDTO",
    "ProveedorVencidoDTO",
    "ResultadoEvaluacionSLADTO",
]
