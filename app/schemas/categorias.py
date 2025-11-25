"""
Esquemas Pydantic para validación de categorías (Supabase).
Soporta categorías personalizadas por usuario con colores.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID
import re


# Schema base de Categoría
class CategoriaBase(BaseModel):
    nombre_categoria: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la categoría"
    )
    color: str = Field(
        default="#007BFF", description="Color en formato hexadecimal (#RRGGBB)"
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Valida que el color sea un código hexadecimal válido"""
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError(
                "Color debe ser un código hexadecimal válido (ej: #FF0000)"
            )
        return v.upper()


# Schema para crear categoría (POST)
class CategoriaCreate(CategoriaBase):
    pass


# Schema para actualizar categoría (PUT/PATCH)
class CategoriaUpdate(BaseModel):
    nombre_categoria: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError(
                "Color debe ser un código hexadecimal válido (ej: #FF0000)"
            )
        return v.upper() if v else None


# Schema de respuesta de Categoría
class CategoriaRead(CategoriaBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Schema extendido con conteo de productos
class CategoriaWithProducts(CategoriaRead):
    total_productos: int = Field(
        default=0, description="Cantidad de productos en esta categoría"
    )
