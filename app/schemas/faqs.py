from pydantic import BaseModel
from typing import Optional


class FAQBase(BaseModel):
    """Base model para preguntas frecuentes"""

    pregunta: str
    respuesta: str
    categoria: str  # Ej: "General", "Productos", "Garantía", "Técnico"
    orden: Optional[int] = None  # Para ordenar las preguntas


class FAQCreate(FAQBase):
    """Schema para crear una nueva FAQ"""

    pass


class FAQRead(FAQBase):
    """Schema para leer una FAQ"""

    id: int

    class Config:
        from_attributes = True
