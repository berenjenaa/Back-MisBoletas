from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from uuid import UUID


# ===== SCHEMA SIMPLIFICADO PARA CATEGORÍA EN PRODUCTO =====
class CategoriaSimple(BaseModel):
    """Schema simplificado de categoría para incluir en productos"""

    id_categoria: UUID
    nombre: str
    color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===== SCHEMAS PARA PRODUCTOS (SUPABASE) =====


class ProductRead(BaseModel):
    """Schema para leer un producto desde Supabase."""

    id_producto: UUID
    id_usuario: UUID
    nombre: str
    fecha_compra: Optional[date] = None
    duracion_garantia_meses: Optional[int] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    tienda: Optional[str] = None
    notas: Optional[str] = None
    precio: Optional[Decimal] = None
    fecha_creacion: Optional[str] = (
        None  # Cambio: datetime → Optional[str] para compatibilidad con Supabase
    )

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Schema para crear un nuevo producto."""

    nombre: str = Field(..., min_length=1, max_length=255)
    fecha_compra: Optional[date] = None
    duracion_garantia_meses: Optional[int] = Field(None, ge=0, le=120)
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    tienda: Optional[str] = Field(None, max_length=255)
    notas: Optional[str] = Field(None, max_length=5000)
    precio: Optional[Decimal] = Field(None, ge=0)
    categoria_ids: Optional[List[UUID]] = []


class ProductUpdate(BaseModel):
    """Schema para actualizar un producto."""

    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    fecha_compra: Optional[date] = None
    duracion_garantia_meses: Optional[int] = Field(None, ge=0, le=120)
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    tienda: Optional[str] = Field(None, max_length=255)
    notas: Optional[str] = Field(None, max_length=5000)
    precio: Optional[Decimal] = Field(None, ge=0)
