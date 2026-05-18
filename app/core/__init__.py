"""
Paquete core de la aplicación MisBoletas.

Contiene:
- config: Configuración centralizada desde .env
- security: Funciones de hash, JWT y autenticación
- middleware: CORS, logging y seguridad
- error_handlers: Manejo global de errores

"""

from .config import settings

__all__ = ["settings"]
