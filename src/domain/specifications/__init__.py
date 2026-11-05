# src/domain/specifications/__init__.py
from src.domain.specifications.base import (
    Specification,
    AndSpecification,
    OrSpecification,
    NotSpecification,
)
from src.domain.specifications.evento_specifications import (
    CapacidadInvitadosSpecification,
    LimiteProveedoresSpecification,
    VentanaCambioAlcanceSpecification,
    ContextoFormalizacionContrato,
    FormalizacionContratoSpecification,
)

__all__ = [
    "Specification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    "CapacidadInvitadosSpecification",
    "LimiteProveedoresSpecification",
    "VentanaCambioAlcanceSpecification",
    "ContextoFormalizacionContrato",
    "FormalizacionContratoSpecification",
]
