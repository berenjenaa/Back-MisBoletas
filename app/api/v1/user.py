from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
import logging

from app.db.supabase import supabase_admin, supabase
from app.core.dependencies import get_current_user_id, get_active_user_id
from app.core.limiter import limiter
from app.core.email_config import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users")

# --- SCHEMAS ACTUALIZADOS ---


class UserRegisterRequest(BaseModel):
    correo: EmailStr
    contrasena: str
    nombre: Optional[str] = None
    redirect_to: Optional[str] = None


class UserLoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    token: str
    type: str


# ✅ ACTUALIZADO: Incluye refresh_token
class UserAuthResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: dict


# ✅ NUEVO: Request para refrescar token
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserUpdateRequest(BaseModel):
    nombre_usuario: Optional[str] = None
    avatar_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    nombre_usuario: Optional[str] = None
    avatar_url: Optional[str] = None
    fecha_registro: Optional[str] = None
    id_rol: Optional[int] = None


# --- ENDPOINTS ---


@router.post(
    "/register", response_model=UserAuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(data: UserRegisterRequest):
    try:
        logger.info("[AUTH] Registro iniciado")
        puente_url = "https://api.misboletas.tech/api/v1/auth/confirm"
        auth_options = {
            "data": {"full_name": data.nombre or data.correo.split("@")[0]},
            "email_redirect_to": puente_url,
        }

        res = supabase.client.auth.sign_up(
            {
                "email": data.correo,
                "password": data.contrasena,
                "options": auth_options,
            }
        )

        if not res.user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Registration failed")

        user_id = UUID(res.user.id)

        # Devolver tokens si la sesión existe (auto-confirmación o similar)
        access_token = res.session.access_token if res.session else ""
        refresh_token = res.session.refresh_token if res.session else None

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id_usuario": str(user_id),
                "email": data.correo,
                "nombre_completo": data.nombre or data.correo.split("@")[0],
                "fecha_registro": datetime.now().isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"[AUTH] Error en registro: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Error al registrarse.")


@router.post("/login", response_model=UserAuthResponse)
async def login(data: UserLoginRequest):
    try:
        res = supabase.client.auth.sign_in_with_password(
            {"email": data.correo, "password": data.contrasena}
        )

        if not res.user or not res.session:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

        user_id = UUID(res.user.id)
        logger.info(f"[OK] User logged in: {data.correo}")

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,  # ✅ Devolvemos refresh token
            "token_type": "bearer",
            "user": {
                "id_usuario": str(user_id),
                "email": data.correo,
                "nombre_completo": data.correo.split("@")[0],
                "fecha_registro": datetime.now().isoformat(),
                "avatar_url": (
                    res.user.user_metadata.get("avatar_url")
                    if res.user.user_metadata
                    else None
                ),
            },
        }
    except Exception as e:
        logger.error(f"[ERROR] Login failed: {e}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas.")


@router.post("/verify-otp", response_model=UserAuthResponse)
async def verify_otp(data: VerifyOTPRequest):
    try:
        res = supabase.client.auth.verify_otp(
            {
                "email": data.email,
                "token": data.token,
                "type": data.type,
            }
        )

        if not res.user or not res.session:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

        user_id = UUID(res.user.id)

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,  # ✅ Devolvemos refresh token
            "token_type": "bearer",
            "user": {
                "id_usuario": str(user_id),
                "email": data.email,
                "nombre_completo": data.email.split("@")[0],
                "fecha_registro": datetime.now().isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"[ERROR] OTP verification failed: {e}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Error al verificar token.")


# ✅ NUEVO ENDPOINT: Refrescar Token
@router.post("/refresh-token", response_model=UserAuthResponse)
async def refresh_token(data: RefreshTokenRequest):
    """Renueva el access token usando un refresh token válido"""
    try:
        res = supabase.client.auth.refresh_session(data.refresh_token)

        if not res.user or not res.session:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id_usuario": str(res.user.id),
                "email": res.user.email,
                "nombre_completo": res.user.user_metadata.get(
                    "full_name", res.user.email.split("@")[0]
                ),
                "avatar_url": res.user.user_metadata.get("avatar_url"),
            },
        }
    except Exception as e:
        logger.error(f"[AUTH] Refresh failed: {e}")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "No se pudo renovar la sesión"
        )


# ... (Mantener resto de endpoints: confirm, me, update, forgot-password, etc.)


@router.get(
    "/confirm",
    summary="Puente para confirmar email desde enlaces",
)
async def confirm_email(
    token: Optional[str] = None,
    email: Optional[str] = None,
    type: str = "signup",
    code: Optional[str] = None,
):
    """
    🌉 PUENTE: Endpoint que actúa como intermediario entre el email y la app.

    FLUJO:
    1. Supabase envía email con link a este endpoint
    2. Usuario hace click → Llama este endpoint
    3. Este endpoint:
        - Verifica la sesión con Supabase (token en cookies)
        - Si es válido → Devuelve HTML con JS que abre la app
        - Si es inválido → Muestra error amigable
    """
    try:
        logger.info(
            f"[🌉 PUENTE] Confirm endpoint called: email={email}, type={type}, code={code}"
        )

        # Supabase redirige después de verificar el token
        # Usamos code o token, ambos pueden venir
        verification_token = code or token

        if not email:
            logger.error("[ERROR] Email no proporcionado")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Error de Confirmación</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                    h1 {{ color: #d32f2f; margin: 0 0 10px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⏰ Error: Email no proporcionado</h1>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)

        # Si tenemos token, verificar el OTP con Supabase
        if verification_token:
            try:
                logger.info(f"[🌉 PUENTE] Verificando OTP con Supabase")
                res = supabase.client.auth.verify_otp(
                    {
                        "email": email,
                        "token": verification_token,
                        "type": type,
                    }
                )
            except Exception as e:
                logger.error(f"[ERROR] Error verificando OTP: {e}")
                res = None
        else:
            # Si no hay token, intentar obtener la sesión actual de Supabase
            try:
                logger.info(f"[🌉 PUENTE] Obteniendo sesión actual de Supabase")
                res = supabase.client.auth.get_session()
            except Exception as e:
                logger.error(f"[ERROR] Error obteniendo sesión: {e}")
                res = None

        if not res or not res.user or not res.session:
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
                    <h1>⏰ Token Inválido o Expirado</h1>
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

        # ✅ CONSTRUIR DEEP LINK CON ACCESS_TOKEN (NO el OTP token)
        # El access_token es lo que necesita la app para autenticarse
        access_token = res.session.access_token if res.session else ""
        refresh_token = res.session.refresh_token if res.session else ""

        deep_link = f"misboletas://auth-callback?access_token={access_token}&refresh_token={refresh_token}&user_id={user_id}&type={type}"
        logger.info(f"[🌐 PUENTE] Opening deep link with access_token")

        # HTML con JavaScript que intenta abrir el deep link
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>¡Bienvenido a MisBoletas!</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px 20px;
                    text-align: center;
                    color: white;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .content h2 {{
                    color: #333333;
                    font-size: 20px;
                    margin: 0 0 15px 0;
                }}
                .content p {{
                    color: #666666;
                    font-size: 14px;
                    line-height: 1.6;
                    margin: 10px 0;
                }}
                .button {{
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 16px 40px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 25px 0;
                    border: 2px solid #667eea;
                    cursor: pointer;
                }}
                .button:hover {{
                    background-color: #764ba2;
                    border-color: #764ba2;
                }}
                .footer {{
                    background-color: #f9f9f9;
                    padding: 20px 30px;
                    text-align: center;
                    border-top: 1px solid #eeeeee;
                }}
                .footer p {{
                    color: #999999;
                    font-size: 12px;
                    margin: 5px 0;
                }}
                .footer a {{
                    color: #667eea;
                    text-decoration: none;
                }}
                .spinner {{
                    display: inline-block;
                    width: 40px;
                    height: 40px;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 20px 0;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .error {{
                    display: none;
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 12px 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                    font-size: 13px;
                    color: #721c24;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Bienvenido a MisBoletas!</h1>
                </div>
                
                <div class="content">
                    <h2>✅ ¡Email Confirmado!</h2>
                    
                    <p>Tu correo ha sido confirmado exitosamente. Ahora estamos abriendo tu app...</p>
                    
                    <div style="text-align: center;">
                        <div class="spinner"></div>
                        <p id="message" style="color: #667eea; font-weight: 600;">Abriendo tu app...</p>
                    </div>
                    
                    <div id="error" class="error"></div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <strong>Si la app no se abre automáticamente, presiona el botón:</strong>
                    </p>
                    
                    <div style="text-align: center;">
                        <button class="button" onclick="openApp()">📱 Abrir App</button>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 MisBoletas. Todos los derechos reservados.</p>
                    <p><a href="https://misboletas.tech">Visita nuestro sitio web</a></p>
                </div>
            </div>

            <script>
                const deepLink = '{deep_link}';

                function openApp() {{
                    window.location.href = deepLink;
                    setTimeout(() => {{
                        document.getElementById('message').style.display = 'none';
                        document.getElementById('error').style.display = 'block';
                        document.getElementById('error').textContent = '❌ No se pudo abrir la app. Por favor, asegúrate de tenerla instalada.';
                    }}, 3000);
                }}

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
                <h1>⏰ Error Procesando Confirmación</h1>
                <p>Por favor, intenta nuevamente o contacta a soporte.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)


@router.get(
    "/reset-password",
    summary="Puente para restablecer contraseña desde email",
)
async def reset_password_bridge(
    token: Optional[str] = None,
    email: Optional[str] = None,
    code: Optional[str] = None,
):
    """
    🌉 PUENTE: Endpoint para restablecer contraseña desde email.

    FLUJO:
    1. Usuario solicita forgot-password
    2. Recibe email con link a este puente
    3. Usuario hace click → Este endpoint valida el token
    4. Si es válido → Abre la app con deep link a reset-password screen
    5. App redirige a reset-password screen con token

    Maneja tokens de tipo 'recovery' desde Supabase.
    """
    try:
        logger.info(
            f"[🌉 PUENTE RESET] Reset password bridge called: email={email}, code={code}"
        )

        recovery_token = code or token

        if not email:
            logger.error("[ERROR] Email no proporcionado en reset-password")
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Error</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                    .container { max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                    h1 { color: #d32f2f; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⏰ Error: Email no proporcionado</h1>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)

        # ✅ CONSTRUIR DEEP LINK PARA RESET-PASSWORD SCREEN
        # La pantalla reset-password necesita el token y email
        deep_link = f"misboletas://reset-password?token={recovery_token}&email={email}&type=recovery"
        logger.info(f"[🌐 PUENTE RESET] Deep link constructed: {deep_link}")

        # HTML con JS para abrir el deep link
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Restablecer Contraseña</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px 20px;
                    text-align: center;
                    color: white;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .content h2 {{
                    color: #333333;
                    font-size: 20px;
                    margin: 0 0 15px 0;
                }}
                .content p {{
                    color: #666666;
                    font-size: 14px;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 16px 40px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 25px 0;
                    border: 2px solid #667eea;
                    cursor: pointer;
                }}
                .button:hover {{
                    background-color: #764ba2;
                    border-color: #764ba2;
                }}
                .spinner {{
                    display: inline-block;
                    width: 40px;
                    height: 40px;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 20px 0;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .footer {{
                    background-color: #f9f9f9;
                    padding: 20px 30px;
                    text-align: center;
                    border-top: 1px solid #eeeeee;
                }}
                .footer p {{
                    color: #999999;
                    font-size: 12px;
                    margin: 5px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Restablecer Contraseña</h1>
                </div>
                
                <div class="content">
                    <h2>✅ Link Válido</h2>
                    
                    <p>Tu enlace de recuperación es válido. Abriendo la app para que restablezcas tu contraseña...</p>
                    
                    <div style="text-align: center;">
                        <div class="spinner"></div>
                        <p id="message" style="color: #667eea; font-weight: 600;">Abriendo MisBoletas...</p>
                    </div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <strong>Si la app no se abre automáticamente:</strong>
                    </p>
                    
                    <div style="text-align: center;">
                        <button class="button" onclick="openApp()">📱 Abrir MisBoletas</button>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 MisBoletas. Todos los derechos reservados.</p>
                </div>
            </div>

            <script>
                const deepLink = '{deep_link}';

                function openApp() {{
                    window.location.href = deepLink;
                    setTimeout(() => {{
                        document.getElementById('message').innerText = '❌ No se pudo abrir la app. Asegúrate de tenerla instalada.';
                    }}, 3000);
                }}

                window.addEventListener('load', () => {{
                    setTimeout(openApp, 500);
                }});
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html, status_code=200)

    except Exception as e:
        logger.error(f"[ERROR] Reset password bridge failed: {str(e)}")
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Error</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                h1 { color: #d32f2f; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⏰ Error en el Procesamiento</h1>
                <p>Hubo un error procesando tu solicitud. Por favor intenta nuevamente.</p>
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
        # Consultar tabla 'perfiles' en Supabase usando el user_id
        response = (
            supabase_admin.get_table("perfiles")
            .select("*")
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        perfil = response.data

        return {
            "id": user_id,
            "email": perfil.get("email", ""),
            "nombre_usuario": perfil.get("nombre_completo"),
            "avatar_url": perfil.get("avatar_url"),
            "fecha_registro": perfil.get("fecha_registro"),
            "id_rol": perfil.get("id_rol"),
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
            update_data["nombre_completo"] = data.nombre_usuario

        if data.avatar_url:
            update_data["avatar_url"] = data.avatar_url

        if not update_data:
            raise ValueError("No fields to update")

        # Actualizar en Supabase
        response = (
            supabase_admin.get_table("perfiles")
            .update(update_data)
            .eq("id_usuario", str(user_id))
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
        supabase_admin.get_table("perfiles").delete().eq(
            "id_usuario", str(user_id)
        ).execute()

        logger.info(f"[OK] User {user_id} account deleted")
        return None

    except Exception as e:
        logger.error(f"[ERROR] Error deleting account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la cuenta. Por favor intenta más tarde.",
        )


# =======================================================================
# === ENDPOINTS DE SOLICITUD DE RESET PASSWORD
# =======================================================================
# Los puentes (GET) están en bridges.py para reducir el tamaño de este archivo


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Solicitar restablecimiento de contraseña",
)
@limiter.limit("3/hour")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    """
    Envía un email con un link para restablecer la contraseña usando Resend.

    - Acepta el email del usuario
    - Genera un recovery token en Supabase
    - Envía email personalizado via Resend con link al puente
    - El usuario hace click en el link → Puente abre la app
    - App muestra pantalla de reset-password

    No requiere autenticación.
    """
    try:
        logger.info(f"[AUTH] Solicitud de reset password para: {data.email}")

        # ✅ Solicitar recovery token en Supabase
        # Esto genera el token pero NO envía email automáticamente
        try:
            recovery_response = supabase.client.auth.reset_password_for_email(
                data.email,
                {
                    "redirect_to": "https://api.misboletas.tech/api/v1/bridges/reset-password"
                },
            )
            logger.info(f"[AUTH] Recovery token generado para {data.email}")
            logger.debug(f"[DEBUG] Recovery response: {recovery_response}")
        except Exception as e:
            logger.error(f"[ERROR] Error generando recovery token: {e}")
            # No revelar si el correo existe o no (seguridad)
            return {
                "status": "success",
                "message": "Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña.",
            }

        # ✅ Construir el link de reset con el token
        # Supabase enviará el token via email, pero nosotros construiremos el link manualmente
        # para Resend usando los parámetros apropiados
        reset_bridge_url = "https://api.misboletas.tech/api/v1/bridges/reset-password"
        # El token será incluido por Supabase en su email, pero para nuestro email con Resend:
        reset_link = f"{reset_bridge_url}?email={data.email}&type=recovery"
        logger.info(f"[AUTH] Reset link construido: {reset_link}")

        # ✅ HTML del email profesional
        email_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Restablecer Contraseña - MisBoletas</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px 20px;
                    text-align: center;
                    color: white;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .content h2 {{
                    color: #333333;
                    font-size: 20px;
                    margin: 0 0 15px 0;
                }}
                .content p {{
                    color: #666666;
                    font-size: 14px;
                    margin: 10px 0;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    background-color: #667eea;
                    color: white !important;
                    padding: 14px 32px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                    border: 2px solid #667eea;
                }}
                .button:hover {{
                    background-color: #764ba2;
                    border-color: #764ba2;
                }}
                .code-box {{
                    background-color: #f9f9f9;
                    border-left: 4px solid #667eea;
                    padding: 12px 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    word-break: break-all;
                    color: #333333;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 12px 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                    font-size: 13px;
                    color: #856404;
                }}
                .footer {{
                    background-color: #f9f9f9;
                    padding: 20px 30px;
                    text-align: center;
                    border-top: 1px solid #eeeeee;
                }}
                .footer p {{
                    color: #999999;
                    font-size: 12px;
                    margin: 5px 0;
                }}
                .footer a {{
                    color: #667eea;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Restablecer Contraseña</h1>
                </div>
                
                <div class="content">
                    <h2>Hola,</h2>
                    
                    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>MisBoletas</strong>.</p>
                    
                    <p>Haz clic en el botón a continuación para proceder con el restablecimiento:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">
                            🔄 Restablecer Contraseña
                        </a>
                    </div>
                    
                    <p style="text-align: center; color: #999; font-size: 13px;">
                        O copia este enlace en tu navegador:
                    </p>
                    <div class="code-box">{reset_link}</div>
                    
                    <div class="warning">
                        <strong>⏰ Tiempo límite:</strong> Este link es válido por <strong>15 minutos</strong>. Si no lo utilizas en ese tiempo, deberás solicitar uno nuevo.
                    </div>
                    
                    <div class="warning">
                        <strong>🔒 Seguridad:</strong> Si no solicitaste este cambio, puedes ignorar este correo. Tu contraseña no cambiará.
                    </div>
                    
                    <p style="color: #999; font-size: 13px; margin-top: 30px;">
                        ¿Preguntas? Contáctanos en <a href="mailto:soporte@misboletas.tech">soporte@misboletas.tech</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2025 MisBoletas. Todos los derechos reservados.</p>
                    <p><a href="https://misboletas.tech">Visita nuestro sitio web</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        # ✅ Enviar email usando el helper unificado (httpx)
        # Esto usa la configuración central en app/core/email_config.py
        # ✅ CAMBIO REALIZADO AQUÍ: SE ELIMINÓ LÓGICA MANUAL DE RESEND
        try:
            email_sent = await send_email(
                recipient_email=data.email,
                subject="🔐 Restablecer tu contraseña en MisBoletas",
                html_content=email_html,
            )

            if email_sent:
                logger.info(f"[OK] Email de reset enviado a {data.email}")
            else:
                logger.error(
                    f"[ERROR] No se pudo enviar el email de recuperación a {data.email}"
                )
                # No lanzar error 500 para no dar pistas al usuario, solo loguear

        except Exception as e:
            logger.error(f"[ERROR] Error enviando email via helper: {str(e)}")
            # No revelar errores internos al frontend
            return {
                "status": "success",
                "message": "Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña.",
            }

        # ✅ Retornar respuesta exitosa (sin revelar si el correo existe)
        return {
            "status": "success",
            "message": "Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Reset password request failed: {e}")
        return {
            "status": "success",
            "message": "Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña.",
        }


@router.post(
    "/reset-password",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Restablecer contraseña con token",
)
async def reset_password(data: dict):
    """
    Restablecer contraseña usando el token del email.

    - El usuario recibe un email con un token
    - Envía el token + nueva contraseña a este endpoint
    - Supabase actualiza la contraseña
    - Retorna nuevo access_token

    Body:
    {
        "token": "abc123...",
        "password": "nueva_contraseña_segura"
    }
    """
    try:
        token = data.get("token")
        new_password = data.get("password")

        if not token or not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token y contraseña son requeridos",
            )

        logger.info("[AUTH] Restableciendo contraseña")

        # Usar el token para restablecer la contraseña
        response = supabase.client.auth.update_user(
            {"password": new_password}, jwt=token
        )

        # Obtener el usuario actualizado
        if response.user:
            logger.info("[AUTH] Contraseña restablecida exitosamente")
            return {
                "access_token": (
                    response.session.access_token if response.session else ""
                ),
                "token_type": "bearer",
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                },
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Reset password failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado. Por favor solicita un nuevo email de recuperación.",
        )


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
