"""
V1 API Routers - Importar todos los módulos de la API
"""

from . import (
    user,
    product,
    documento,
    categorias,
    tickets,
    organizations,
    alerts,
    admin_gcs,
    webhooks,
)

__all__ = [
    "user",
    "product",
    "documento",
    "categorias",
    "tickets",
    "organizations",
    "alerts",
    "admin_gcs",
    "webhooks",
]
