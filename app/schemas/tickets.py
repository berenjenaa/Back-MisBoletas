# En app/schemas/tickets.py

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


# ===== SCHEMAS PARA TICKETS DE SOPORTE (SUPABASE) =====


class TicketRead(BaseModel):
    """Schema para leer un ticket desde Supabase."""

    id_ticket: UUID
    id_usuario: UUID
    asunto: str
    mensaje: str
    estado: str  # 'abierto', 'en_proceso', 'resuelto', 'cerrado'
    prioridad: str  # 'baja', 'media', 'alta'
    respuesta_admin: Optional[str] = None
    fecha_creacion: Optional[str] = None
    fecha_actualizacion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    """Schema para crear un nuevo ticket."""

    asunto: str = Field(..., min_length=1, max_length=255)
    mensaje: str = Field(..., min_length=1, max_length=5000)
    prioridad: Optional[str] = Field("media", regex="^(baja|media|alta)$")
