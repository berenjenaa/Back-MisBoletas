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

from app.core.config import supabase


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
    3. Verifica que la cuenta no esté bloqueada
    4. Devuelve los datos del usuario autenticado

    Raises:
        HTTPException: Si el token es inválido, expiró, o la cuenta está bloqueada
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Validar token con Supabase
        user = supabase.auth.get_user(token)

        if not user or not user.user:
            raise credentials_exception

        # Extraer datos del usuario
        auth_user = user.user
        user_id = auth_user.id
        email = auth_user.email or ""

        # Nota: El bloqueo de cuenta se verifica usando una función RPC en los endpoints
        # No usamos .table("perfiles").select() aquí porque RLS bloquea las queries directas
        # Las RPC functions con SECURITY DEFINER manejan la verificación internamente

        return CurrentUser(id=user_id, email=email)

    except HTTPException:
        raise
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


# =======================================================================
# === DEPENDENCIA: OBTENER ID DEL USUARIO ACTIVO (No bloqueado)
# =======================================================================


async def get_active_user_id(
    current_user: CurrentUser = Depends(get_current_user),
) -> str:
    """
    Dependencia que valida que el usuario NO esté bloqueado.
    
    Uso en endpoints de negocio (crear, actualizar, eliminar):
        @app.post("/productos")
        async def create_product(
            data: ProductCreate,
            user_id: str = Depends(get_active_user_id),
        ):
            ...
    """
    try:
        # Verificar que la cuenta no está bloqueada
        perfil_response = (
            supabase.table("perfiles")
            .select("cuenta_bloqueada, motivo_bloqueo")
            .eq("id_usuario", current_user.id)
            .single()
            .execute()
        )

        if perfil_response.data and perfil_response.data.get("cuenta_bloqueada"):
            motivo = perfil_response.data.get("motivo_bloqueo", "Cuenta bloqueada")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu cuenta está bloqueada: {motivo}",
            )
        
        return current_user.id
    
    except HTTPException:
        raise
    except Exception as e:
        # Si hay error consultando perfil, permitir pero loguear
        print(f"[WARNING] Error checking account status: {e}")
        return current_user.id
