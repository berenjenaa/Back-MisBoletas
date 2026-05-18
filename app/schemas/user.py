from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from typing import Optional


# Schema para CREAR un usuario (Entrada)
class UserCreate(BaseModel):
    """Schema para registrar un nuevo usuario con Supabase Auth."""

    nombre: str
    correo: EmailStr
    contrasena: str


# Schema para LEER un usuario (Respuesta)
class UserRead(BaseModel):
    """Schema para devolver datos del usuario autenticado."""

    id: str  # UUID de Supabase
    email: str
    nombre: Optional[str] = None
    id_rol: Optional[int] = None  # Nuevo: 1=admin, 2=usuario_normal, 3=empresa
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Schema para ACTUALIZAR un usuario (Entrada)
class UserUpdate(BaseModel):
    """Schema para actualizar datos del usuario."""

    nombre: Optional[str] = None
    email: Optional[EmailStr] = None


# Schema para ACTUALIZAR contraseña
class UserUpdatePassword(BaseModel):
    """Schema para cambiar la contraseña."""

    contrasena_actual: str
    contrasena_nueva: str


# Schema para Login
class UserLogin(BaseModel):
    """Schema para iniciar sesión."""

    correo: EmailStr
    contrasena: str
