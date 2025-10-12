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
    nombre_categoria: str
    color: str = "#007BFF"
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Valida que el color sea un código hexadecimal válido"""
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color debe ser un código hexadecimal válido (ej: #FF0000)')
        return v.upper()

# Schema para crear categoría
class CategoriaCreate(CategoriaBase):
    pass

# Schema para actualizar categoría
class CategoriaUpdate(BaseModel):
    nombre_categoria: Optional[str] = None
    color: Optional[str] = None
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color debe ser un código hexadecimal válido (ej: #FF0000)')
        return v.upper() if v else None

# Schema para respuestas de Categoría
class Categoria(CategoriaBase):
    categoriaid: int
    usuarioid: int
    
    class Config:
        from_attributes = True

class CategoriaResponse(BaseModel):
    """Schema para las respuestas de operaciones con categorías."""
    message: str
    categoriaid: Optional[int] = None
    categoria: Optional[Categoria] = None

# Schema extendido con conteo de productos
class CategoriaWithProducts(Categoria):
    TotalProductos: int = Field(default=0, description="Cantidad de productos en esta categoría")
