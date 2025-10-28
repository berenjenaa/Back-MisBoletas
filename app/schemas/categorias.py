"""
Esquemas Pydantic para validación de categorías.
Soporta categorías personalizadas por usuario con colores.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import re


# Schema base de Categoría
class CategoriaBase(BaseModel):
    NombreCategoria: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la categoría"
    )
    Color: str = Field(
        default="#007BFF", description="Color en formato hexadecimal (#RRGGBB)"
    )

    @field_validator("Color")
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
    NombreCategoria: Optional[str] = Field(None, min_length=1, max_length=100)
    Color: Optional[str] = None

    @field_validator("Color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError(
                "Color debe ser un código hexadecimal válido (ej: #FF0000)"
            )
        return v.upper() if v else None


# Schema de respuesta de Categoría
class Categoria(CategoriaBase):
    CategoriaID: int
    UsuarioID: int
    FechaCreacion: datetime

    class Config:
        from_attributes = True


# Schema extendido con conteo de productos
class CategoriaWithProducts(Categoria):
    TotalProductos: int = Field(
        default=0, description="Cantidad de productos en esta categoría"
    )
