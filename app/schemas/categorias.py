from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from uuid import UUID
import re


# Schema base
class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#E77573")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color inválido")
        return v.upper()


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color inválido")
        return v.upper() if v else None


class CategoriaRead(CategoriaBase):
    id_categoria: UUID
    id_usuario: UUID
    fecha_creacion: Optional[str] = None
    fecha_eliminacion: Optional[str] = None
    numero_productos: int = 0

    model_config = ConfigDict(from_attributes=True)
