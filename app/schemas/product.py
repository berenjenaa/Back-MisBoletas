from pydantic import BaseModel, Field, ConfigDict  # <-- CAMBIO
from datetime import date
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal  # <-- CAMBIO

if TYPE_CHECKING:
    from app.schemas.categorias import Categoria


# ===== SCHEMA SIMPLIFICADO PARA CATEGORÍA EN PRODUCTO =====
class CategoriaSimple(BaseModel):
    """Schema simplificado de categoría para incluir en productos"""

    CategoriaID: int
    NombreCategoria: str
    Color: str

    # --- CAMBIO: Sintaxis de Pydantic v2 ---
    model_config = ConfigDict(from_attributes=True)


# ===== SCHEMAS CORREGIDOS - SIN CONFUSIÓN =====


# Schema para LEER productos (respuestas de API)
class ProductRead(BaseModel):
    ProductoID: int
    NombreProducto: str
    FechaCompra: Optional[date] = None
    DuracionGarantia: Optional[int] = None
    Marca: Optional[str] = None
    Modelo: Optional[str] = None
    Tienda: Optional[str] = None
    Notas: Optional[str] = None
    UsuarioID: int
    categorias: List[CategoriaSimple] = []

    # --- CAMBIO AÑADIDO ---
    Precio: Optional[Decimal] = None
    # --- FIN DEL CAMBIO ---

    # --- CAMBIO: Sintaxis de Pydantic v2 ---
    model_config = ConfigDict(from_attributes=True)


# Schema para CREAR productos (sin ID, campos obligatorios)
class ProductCreate(BaseModel):
    NombreProducto: str = Field(..., min_length=1, max_length=255)
    FechaCompra: Optional[date] = None
    DuracionGarantia: Optional[int] = Field(None, ge=0, le=120)
    Marca: Optional[str] = Field(None, max_length=100)
    Modelo: Optional[str] = Field(None, max_length=100)
    Tienda: Optional[str] = Field(None, max_length=255)
    Notas: Optional[str] = Field(None, max_length=5000)
    categoria_id: Optional[int] = None

    # --- CAMBIO AÑADIDO ---
    Precio: Optional[Decimal] = Field(
        None, ge=0, description="Precio del producto (para IA/Dashboard)"
    )
    # --- FIN DEL CAMBIO ---


# Schema para ACTUALIZAR productos (todos los campos opcionales)
class ProductUpdate(BaseModel):
    NombreProducto: Optional[str] = Field(None, min_length=1, max_length=255)
    FechaCompra: Optional[date] = None
    DuracionGarantia: Optional[int] = Field(None, ge=0, le=120)
    Marca: Optional[str] = Field(None, max_length=100)
    Modelo: Optional[str] = Field(None, max_length=100)
    Tienda: Optional[str] = Field(None, max_length=255)
    Notas: Optional[str] = Field(None, max_length=5000)

    # --- CAMBIO AÑADIDO ---
    Precio: Optional[Decimal] = Field(None, ge=0, description="Precio del producto")
    # --- FIN DEL CAMBIO ---


# Schema específico para actualizar solo notas (simplificado)
class ProductNotesUpdate(BaseModel):
    Notas: str = Field(..., max_length=5000)
