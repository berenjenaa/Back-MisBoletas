"""
estos manejadores atrapan el error y devuelven una respuesta HTTP amigable.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


def handle_database_error(error: Exception) -> HTTPException:
    """
    Maneja errores de base de datos (Supabase).
    """
    logger.error(f"Error de base de datos: {str(error)}")

    error_str = str(error).lower()

    if "unique" in error_str or "duplicate" in error_str:
        return HTTPException(status_code=409, detail="El recurso ya existe")
    elif "foreign key" in error_str or "referential" in error_str:
        return HTTPException(
            status_code=422, detail="Referencia inválida a otro recurso"
        )
    elif "not found" in error_str:
        return HTTPException(status_code=404, detail="Recurso no encontrado")
    else:
        return HTTPException(status_code=500, detail="Error interno de base de datos")


def setup_exception_handlers(app: FastAPI):
    """Configura todos los manejadores de errores globales."""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Maneja errores de validación de datos."""
        url = str(request.url.path)
        logger.error(f"Error de validación en {url}: {str(exc)}")

        # Extraer errores específicos para el frontend
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")

        return JSONResponse(
            status_code=422,
            content={
                "error": "Datos inválidos",
                "message": "Por favor revisa los datos enviados",
                "details": errors,
                "path": url,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        """Maneja errores HTTP estándar."""
        url = str(request.url.path)

        # Solo loguear errores 5xx como errores, 4xx como warnings
        if exc.status_code >= 500:
            logger.error(f"Error {exc.status_code} en {url}: {exc.detail}")
        else:
            logger.warning(f"HTTP {exc.status_code} en {url}: {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"Error {exc.status_code}",
                "message": exc.detail,
                "path": url,
            },
        )

    @app.exception_handler(Exception)
    async def catch_all_handler(request: Request, exc: Exception):
        """Maneja cualquier error no controlado."""
        url = str(request.url.path)
        error_type = type(exc).__name__

        logger.error(
            f"Error inesperado en {url}: {error_type} - {str(exc)}",
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Error interno del servidor",
                "message": "Algo salió mal.",
                "type": error_type,
                "path": url,
            },
        )

    logger.info("Manejadores de errores configurados")
