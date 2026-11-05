# src/api/routers/__init__.py
from src.api.routers.auditoria_router import router as auditoria_router
from src.api.routers.eventos_router import router as eventos_router
from src.api.routers.pagos_router import router as pagos_router

__all__ = ["eventos_router", "pagos_router", "auditoria_router"]
