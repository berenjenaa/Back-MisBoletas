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
    # ❌ ELIMINAMOS 'prioridad' de aquí.
    # El usuario solo envía asunto y mensaje.


# --- Modelo para RESPUESTA (Lo que devuelve la API) ---
class TicketResponse(TicketBase):
    id_ticket: UUID
    user_id: str
    prioridad: str  # Aquí sí se muestra (la asigna el sistema)
    estado: str
    fecha_creacion: datetime
    fecha_cierre: Optional[str] = None

    class Config:
        orm_mode = True


# Alias para lectura (retrocompatibilidad)
TicketRead = TicketResponse
