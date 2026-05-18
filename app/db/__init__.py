"""
Paquete de configuración de base de datos.

Exports main functions and objects for database handling.
En la migración a Supabase, la mayoría de operaciones usan Supabase SDK.
"""

# Importaciones principales del paquete db
from .supabase import supabase

__all__ = ["supabase"]
