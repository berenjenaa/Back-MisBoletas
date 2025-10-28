"""
Paquete de configuración de base de datos.

Exporta las funciones y objetos principales para manejo de BD

"""

# Importaciones principales del paquete db
from .session import Base, SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
