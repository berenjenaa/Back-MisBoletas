"""
Schemas Pydantic para Organizaciones y Miembros.
Define la estructura de datos para gestionar organizaciones.
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional, List
from uuid import UUID


# ===== SCHEMA PARA MIEMBRO =====
class MiembroBase(BaseModel):
    """Base para miembros de una organización."""

    email: EmailStr
    estado: str = Field(default="invitado", pattern="^(invitado|activo|suspendido)$")


class MiembroCreate(MiembroBase):
    """Schema para crear un miembro."""

    pass


class MiembroRead(MiembroBase):
    """Schema para leer un miembro."""

    id_miembro: UUID
    id_organizacion: UUID
    fecha_union: Optional[datetime] = None
    fecha_salida: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ===== SCHEMA PARA ORGANIZACIÓN =====
class OrganizacionBase(BaseModel):
    """Base para organizaciones."""

    nombre: str = Field(..., min_length=1, max_length=255)
    id_tipo: int  # 1=familia, 2=empresa, 3=jjvv, 4=club_deportivo
    descripcion: Optional[str] = None
    ruc: Optional[str] = None


class OrganizacionCreate(OrganizacionBase):
    """Schema para crear una organización."""

    pass


class OrganizacionRead(OrganizacionBase):
    """Schema para leer una organización."""

    id_organizacion: UUID
    id_propietario: UUID
    fecha_creacion: Optional[datetime] = None
    fecha_eliminacion: Optional[datetime] = None
    miembros_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class OrganizacionWithMembers(OrganizacionRead):
    """Organización con lista de miembros."""

    miembros: List[MiembroRead] = []


class OrganizacionUpdate(BaseModel):
    """Schema para actualizar una organización."""

    nombre: Optional[str] = None
    id_tipo: Optional[int] = None
    descripcion: Optional[str] = None
    ruc: Optional[str] = None
