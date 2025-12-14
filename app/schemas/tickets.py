from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


# --- Modelo BASE (Datos comunes) ---
class TicketBase(BaseModel):
    asunto: str
    mensaje: str


# --- Modelo para CREAR (Lo que envía el usuario) ---
class TicketCreate(TicketBase):
    pass
    # El usuario solo envía asunto y mensaje.


# --- Modelo para RESPUESTA (Lo que devuelve la API) ---
class TicketResponse(TicketBase):
    id_ticket: UUID
    id_usuario: UUID  # <--- ✅ CORREGIDO (Antes era user_id: str)
    prioridad: str
    estado: str
    fecha_creacion: datetime
    fecha_cierre: Optional[str] = None

    class Config:
        from_attributes = True  # En versiones nuevas de Pydantic v2
        # o orm_mode = True en v1, este proyecto parece usar v2 por el requirements.txt


# Alias para lectura (retrocompatibilidad)
TicketRead = TicketResponse
