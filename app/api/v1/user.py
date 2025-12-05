from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
import logging

from app.db.supabase import supabase_admin, supabase
from app.core.dependencies import get_current_user_id, get_active_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["usuarios"])


# Schemas para request/response
class UserRegisterRequest(BaseModel):
    correo: EmailStr
    contrasena: str
    nombre: Optional[str] = None


class UserLoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str


class UserAuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict  # Contiene: id_usuario, email, nombre_completo, fecha_registro


class UserUpdateRequest(BaseModel):
    nombre_usuario: Optional[str] = None
    avatar_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    nombre_usuario: Optional[str] = None
    avatar_url: Optional[str] = None
    fecha_registro: Optional[str] = None


# =======================================================================
# === ENDPOINTS DE AUTENTICACIÓN (Sin requerir token)
# =======================================================================


@router.post(
    "/register",
    response_model=UserAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrarse (crear cuenta)",
)
async def register(data: UserRegisterRequest):
    """
    Registra un nuevo usuario en Supabase Auth.

    - Crea una cuenta en Supabase Auth
    - El trigger on_auth_user_created automáticamente:
      * Crea el perfil en la tabla 'perfiles'
      * Crea categorías predefinidas
    - Retorna access_token para usar en otros endpoints
    """
    try:
        # Registrar en Supabase Auth
        # El trigger on_auth_user_created se ejecutará automáticamente
        res = supabase.client.auth.sign_up(
            {"email": data.correo, "password": data.contrasena}
        )

        if not res.user:
            error_msg = str(res) if res else "Unknown error"
            logger.error(f"[ERROR] Supabase signup failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {error_msg}",
            )

        user_id = UUID(res.user.id)
        logger.info(f"[OK] User registered: {data.correo} (ID: {user_id})")

        return {
            "access_token": res.session.access_token if res.session else "",
            "token_type": "bearer",
            "user": {
                "id_usuario": str(user_id),
                "email": data.correo,
                "nombre_completo": data.nombre or data.correo.split("@")[0],
                "fecha_registro": datetime.now().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al registrarse. Por favor intenta más tarde.",
        )


@router.post(
    "/login",
    response_model=UserAuthResponse,
    summary="Iniciar sesión",
)
async def login(data: UserLoginRequest):
    """
    Inicia sesión con email y contraseña.

    - Valida credenciales en Supabase Auth
    - Retorna access_token para usar en otros endpoints
    """
    try:
        # Login en Supabase Auth
        res = supabase.client.auth.sign_in_with_password(
            {"email": data.correo, "password": data.contrasena}
        )

        if not res.user or not res.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        user_id = UUID(res.user.id)

        logger.info(f"[OK] User logged in: {data.correo}")

        # Nota: No consultamos table("perfiles") aquí porque RLS lo bloquea
        # El usuario será autenticado en cada request via JWT
        # Los datos del perfil se obtienen en endpoints específicos si es necesario

        return {
            "access_token": res.session.access_token,
            "token_type": "bearer",
            "user": {
                "id_usuario": str(user_id),
                "email": data.correo,
                "nombre_completo": data.correo.split("@")[0],
                "fecha_registro": datetime.now().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas."
        )


# =======================================================================
# === ENDPOINTS DE USUARIO AUTENTICADO
# =======================================================================


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Obtener mi perfil de usuario",
)
async def read_users_me(user_id: UUID = Depends(get_active_user_id)):
    """
    Devuelve los datos del usuario autenticado desde Supabase.

    - Valida el token JWT
    - Lee el perfil del usuario en la tabla 'profiles' de Supabase
    - Devuelve información del perfil
    """
    try:
        # Consultar tabla 'profiles' en Supabase usando el user_id
        response = (
            supabase_admin.get_table("profiles")
            .select("*")
            .eq("id", str(user_id))
            .single()
            .execute()
        )

        perfil = response.data

        return {
            "id": user_id,
            "email": perfil.get("email", ""),
            "nombre_usuario": perfil.get("nombre_usuario"),
            "avatar_url": perfil.get("avatar_url"),
            "fecha_registro": perfil.get("fecha_registro"),
        }

    except Exception as e:
        logger.error(f"[ERROR] Error reading profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el perfil. Por favor intenta más tarde.",
        )


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Actualizar mi perfil (nombre/avatar)",
)
async def update_my_profile(
    data: UserUpdateRequest,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Actualiza el perfil del usuario en Supabase.

    Campos soportados:
    - nombre_usuario (str)
    - avatar_url (str, opcional)
    """
    try:
        # Preparar datos de actualización
        update_data = {}

        if data.nombre_usuario:
            update_data["nombre_usuario"] = data.nombre_usuario

        if data.avatar_url:
            update_data["avatar_url"] = data.avatar_url

        if not update_data:
            raise ValueError("No fields to update")

        # Actualizar en Supabase
        response = (
            supabase_admin.get_table("profiles")
            .update(update_data)
            .eq("id", str(user_id))
            .execute()
        )

        perfil = response.data[0] if response.data else {}

        return {
            "id": user_id,
            "email": perfil.get("email", ""),
            "nombre_usuario": perfil.get("nombre_usuario"),
            "avatar_url": perfil.get("avatar_url"),
            "fecha_registro": perfil.get("fecha_registro"),
        }

    except Exception as e:
        logger.error(f"[ERROR] Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el perfil. Por favor intenta más tarde.",
        )


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mi cuenta",
)
async def delete_my_account(
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Elimina la cuenta del usuario actual.

    Nota: La eliminación del usuario en auth es manejada por Supabase.
    Este endpoint solo limpia datos del perfil.
    """
    try:
        # Eliminar perfil de Supabase
        supabase_admin.get_table("profiles").delete().eq("id", str(user_id)).execute()

        logger.info(f"[OK] User {user_id} account deleted")
        return None

    except Exception as e:
        logger.error(f"[ERROR] Error deleting account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la cuenta. Por favor intenta más tarde.",
        )


# =======================================================================
# === ENDPOINT DE SALUD (Para verificar API)
# =======================================================================


@router.get(
    "/debug/validate-token",
    summary="Debug: Validar token",
)
async def debug_validate_token(
    user_id: str = Depends(get_current_user_id),
):
    """
    DEBUG: Valida que el token es correcto.
    Si ves este endpoint, el token es válido.
    """
    try:
        logger.info(f"[DEBUG] Token validation successful for user: {user_id}")
        return {
            "status": "token_valid",
            "user_id": user_id,
            "message": "Token validado correctamente",
        }
    except Exception as e:
        logger.error(f"[ERROR] Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )


@router.get(
    "/health",
    summary="Health check",
)
async def health_check():
    """
    Verifica que el servidor y la autenticación están funcionando.
    No requiere autenticación.
    """
    try:
        logger.info("[OK] Health check passed")
        return {"status": "ok", "auth_provider": "supabase"}
    except Exception as e:
        logger.error(f"[ERROR] Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )
