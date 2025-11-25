"""
Dependencias de autenticación para proteger endpoints.

Proporciona:
- get_current_user: Valida token JWT de Supabase y devuelve datos del usuario
- get_current_user_id: Devuelve solo el ID del usuario (UUID de Supabase)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional
from pydantic import BaseModel

from app.db.supabase import supabase

# =======================================================================
# === MODELOS AUXILIARES
# =======================================================================


class CurrentUser(BaseModel):
    """Datos básicos del usuario autenticado desde Supabase."""

    id: str  # UUID de Supabase
    email: str


# =======================================================================
# === SEGURIDAD: Bearer Token Scheme
# =======================================================================

security = HTTPBearer()


# =======================================================================
# === DEPENDENCIA: OBTENER USUARIO ACTUAL (Validado con Supabase)
# =======================================================================


async def get_current_user(
    credentials=Depends(security),
) -> CurrentUser:
    """
    Dependencia de FastAPI que valida el token de Supabase.

    Lógica:
    1. Extrae el token del header Authorization (Bearer token)
    2. Lo valida con supabase.auth.get_user(token)
    3. Devuelve los datos del usuario autenticado

    Raises:
        HTTPException: Si el token es inválido o expiró
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Validar token con Supabase
        user = supabase.client.auth.get_user(token)

        if not user or not user.user:
            raise credentials_exception

        # Extraer datos del usuario
        auth_user = user.user
        return CurrentUser(id=auth_user.id, email=auth_user.email or "")

    except Exception as e:
        print(f"[ERROR] Error validating token: {e}")
        raise credentials_exception


# =======================================================================
# === DEPENDENCIA: OBTENER ID DEL USUARIO ACTUAL
# =======================================================================


async def get_current_user_id(
    current_user: CurrentUser = Depends(get_current_user),
) -> str:
    """
    Dependencia simplificada que devuelve solo el ID del usuario (UUID).

    Uso en endpoints:
        @app.get("/my-data")
        async def get_data(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    return current_user.id


# =======================================================================
# === DEPENDENCIA: EMAIL DEL USUARIO ACTUAL
# =======================================================================


async def get_current_user_email(
    current_user: CurrentUser = Depends(get_current_user),
) -> str:
    """
    Dependencia para obtener solo el email del usuario autenticado.
    """
    return current_user.email
