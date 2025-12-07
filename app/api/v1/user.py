from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
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
    redirect_to: Optional[str] = None


class UserLoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    token: str
    type: str  # 'signup' o 'recovery'


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
        # Log para auditoría (sin exponer datos sensibles)
        logger.info("[AUTH] Registro iniciado")

        # ✅ URL DEL PUENTE (DEFINITIVA Y PROFESIONAL)
        # Este es el endpoint que verifica el OTP y abre la app
        puente_url = "https://api.misboletas.tech/api/v1/users/confirm"

        # Preparar opciones de autenticación para Supabase
        auth_options = {
            "data": {"full_name": data.nombre or data.correo.split("@")[0]},
            "email_redirect_to": puente_url,  # ✅ SIEMPRE USAR EL PUENTE
        }

        logger.info("[AUTH] Email de confirmación configurado")

        # Registrar en Supabase Auth con opciones
        # El trigger on_auth_user_created se ejecutará automáticamente
        res = supabase.client.auth.sign_up(
            {
                "email": data.correo,
                "password": data.contrasena,
                "options": auth_options,  # ✅ ESTO ES LO CRUCIAL
            }
        )

        if not res.user:
            error_msg = str(res) if res else "Unknown error"
            logger.error("[AUTH] Fallo en registro de usuario")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {error_msg}",
            )

        user_id = UUID(res.user.id)
        logger.info("[AUTH] ✅ Usuario registrado exitosamente")

        # Si hay session (usuario confirmado), usarla
        # Si no hay session (pendiente confirmación), generar token temporal
        access_token = ""
        if res.session:
            access_token = res.session.access_token
            logger.info("[AUTH] Sesión activa proporcionada")
        else:
            # Usuario registrado pero pendiente confirmación de email
            # El frontend deberá usar el token OTP cuando confirme el email
            logger.info("[AUTH] ⏳ Registro pendiente de confirmación de email")
            access_token = ""

        return {
            "access_token": access_token,
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
        logger.error("[AUTH] Error en registro de usuario")
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


@router.post(
    "/verify-otp",
    response_model=UserAuthResponse,
    summary="Verificar OTP desde deep link de email",
)
async def verify_otp(data: VerifyOTPRequest):
    """
    Verifica un token OTP recibido desde un deep link en email.

    - Valida el token OTP con Supabase
    - Retorna access_token si es válido
    - Crea la sesión del usuario
    """
    try:
        logger.info(f"[DEBUG] Verificando OTP para: {data.email}, type={data.type}")

        # Verificar el OTP con Supabase
        res = supabase.client.auth.verify_otp(
            {
                "email": data.email,
                "token": data.token,
                "type": data.type,  # 'signup' o 'recovery'
            }
        )

        if not res.user or not res.session:
            logger.error(f"[ERROR] OTP verification failed for {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )

        user_id = UUID(res.user.id)
        logger.info(f"[OK] OTP verified for {data.email}, user: {user_id}")

        return {
            "access_token": res.session.access_token,
            "token_type": "bearer",
            "user": {
                "id_usuario": str(user_id),
                "email": data.email,
                "nombre_completo": data.email.split("@")[0],
                "fecha_registro": datetime.now().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] OTP verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al verificar el token. Por favor intenta nuevamente.",
        )


@router.get(
    "/confirm",
    summary="Puente para confirmar email desde enlaces",
)
async def confirm_email(token: str, email: str, type: str = "signup"):
    """
    🌉 PUENTE: Endpoint que actúa como intermediario entre el email y la app.

    FLUJO:
    1. Email contiene: https://api.misboletas.tech/users/confirm?token=XXX&email=YYY&type=signup
    2. Usuario hace click → Llama este endpoint
    3. Este endpoint:
       - Verifica el OTP con Supabase
       - Si es válido → Devuelve HTML con JS que abre la app
       - Si es inválido → Muestra error amigable

    VENTAJAS:
    - El link siempre funciona (usa https, no deep link)
    - Si la app no está instalada, muestra error legible
    - Si la app está instalada, abre automáticamente
    - Funciona en emails, SMS, cualquier lado
    """
    try:
        logger.info(f"[🌉 PUENTE] Confirm endpoint called: email={email}, type={type}")

        # Verificar el OTP con Supabase
        res = supabase.client.auth.verify_otp(
            {
                "email": email,
                "token": token,
                "type": type,
            }
        )

        if not res.user or not res.session:
            logger.error(f"[ERROR] OTP verification failed for {email}")
            # Retornar HTML de error
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Error de Confirmación</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                    h1 {{ color: #d32f2f; margin: 0 0 10px 0; }}
                    p {{ color: #666; font-size: 16px; line-height: 1.6; }}
                    a {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; margin-top: 20px; }}
                    a:hover {{ background: #764ba2; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Token Inválido o Expirado</h1>
                    <p>El link de confirmación ya no es válido. Puede que haya expirado (tienen validez de 24 horas).</p>
                    <p><strong>¿Qué hacer?</strong></p>
                    <p>Por favor, solicita un nuevo correo de confirmación desde la app.</p>
                    <a href="https://misboletas.tech">Volver al inicio</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)

        user_id = UUID(res.user.id)
        logger.info(f"[✅ PUENTE] OTP verified, user: {user_id}")

        # ✅ CONSTRUIR DEEP LINK Y DEVOLVER HTML CON JAVASCRIPT QUE LO ABRE
        deep_link = (
            f"misboletas://auth-callback?token={token}&email={email}&type={type}"
        )
        logger.info(f"[🔗 PUENTE] Opening deep link: {deep_link}")

        # HTML con JavaScript que intenta abrir el deep link
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Confirmando...</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
                .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); text-align: center; max-width: 500px; }}
                h1 {{ color: #333; margin: 0 0 10px 0; }}
                p {{ color: #666; font-size: 16px; line-height: 1.6; margin: 10px 0; }}
                .spinner {{ display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px 0; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; margin-top: 20px; border: none; cursor: pointer; font-size: 16px; }}
                .button:hover {{ background: #764ba2; }}
                .error {{ display: none; color: #d32f2f; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ ¡Email Confirmado!</h1>
                <div class="spinner"></div>
                <p>Abriendo tu app...</p>
                <p id="error" class="error"></p>
                <p style="font-size: 14px; color: #999; margin-top: 30px;">Si la app no se abre automáticamente, presiona el botón:</p>
                <button class="button" onclick="openApp()">Abrir App</button>
            </div>

            <script>
                const deepLink = '{deep_link}';
                
                // Intentar abrir el deep link
                function openApp() {{
                    window.location.href = deepLink;
                    // Si no se abre en 3 segundos, mostrar error
                    setTimeout(() => {{
                        document.getElementById('error').style.display = 'block';
                        document.getElementById('error').textContent = 'No se pudo abrir la app. Asegúrate de tenerla instalada.';
                    }}, 3000);
                }}
                
                // Intentar abrir automáticamente al cargar
                window.addEventListener('load', () => {{
                    setTimeout(openApp, 500);
                }});
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html, status_code=200)

    except Exception as e:
        logger.error(f"[ERROR] Confirm endpoint failed: {str(e)}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Error</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                h1 {{ color: #d32f2f; }}
                p {{ color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Error Procesando Confirmación</h1>
                <p>{str(e)}</p>
                <p>Por favor, intenta nuevamente o contacta a soporte.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)


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
