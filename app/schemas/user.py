from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from typing import Optional


# Schema Base (Configuración Común)
# ==========================================
class BaseSchema(BaseModel):
    """
    Configuración base para schemas que leen desde modelos ORM.
    """

    # 'from_attributes=True' permite a Pydantic leer
    # datos desde atributos de objeto (ej: user.NombreUsuario)
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


# ==========================================
# Schema para CREAR un usuario (Entrada)
# ==========================================
class UserCreate(BaseModel):
    """
    Schema para el JSON de ENTRADA al registrar un usuario.
    """

    nombre: str
    correo: EmailStr
    contrasena: str


# ==========================================
# Schema para LEER un usuario (Respuesta)
# ==========================================
class UserRead(BaseSchema):  # <-- Hereda la config ORM
    """
    Schema para LEER un usuario (lo que la API devuelve).
    Mapea los nombres de la BD (ej: 'UsuarioID') a los
    nombres del JSON (ej: 'idUsuario').
    """

    idUsuario: int = Field(alias="UsuarioID")
    nombre: str = Field(alias="NombreUsuario")
    correo: EmailStr = Field(alias="Email")
    fechaRegistro: datetime = Field(alias="FechaRegistro")


# ==========================================
# Schema para ACTUALIZAR un usuario (Entrada)
# ==========================================
class UserUpdate(BaseModel):
    """
    Schema para ACTUALIZAR un usuario (PATCH).
    Todos los campos son opcionales.
    Usa los nombres del modelo (ej: 'NombreUsuario') para
    facilitar el 'setattr' genérico en el CRUD.
    """

    NombreUsuario: Optional[str] = None
    Email: Optional[EmailStr] = None


# ==========================================
# Schema para ACTUALIZAR contraseña
# ==========================================
class UserUpdatePassword(BaseModel):
    """
    Schema para ACTUALIZAR la contraseña (Entrada).
    """

    contrasena_actual: str
    contrasena_nueva: str


# ==========================================
# ⬇️ ⬇️ ⬇️ CORRECCIÓN: CLASE FALTANTE ⬇️ ⬇️ ⬇️
# ==========================================
class UserLogin(BaseModel):
    """
    Schema para el JSON de ENTRADA al iniciar sesión.
    """

    correo: EmailStr
    contrasena: str
