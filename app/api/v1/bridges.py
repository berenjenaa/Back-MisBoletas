"""
Puentes de Email (Bridges)

Estos endpoints actúan como intermediarios entre los emails de Supabase y la app.
- Reciben tokens/OTP del email
- Devuelven HTML con deep links a la app
- Manejan fallbacks si la app no está instalada
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from uuid import UUID
import logging

from app.db.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bridges")


@router.get(
    "/confirm",
    summary="🌉 Puente: Confirmar email desde enlace",
)
async def confirm_email(token: str, email: str, type: str = "signup"):
    """
    🌉 PUENTE: Endpoint que actúa como intermediario entre el email y la app.

    FLUJO:
    1. Email contiene: https://api.misboletas.tech/api/v1/bridges/confirm?token=XXX&email=YYY&type=signup
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
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Error de Confirmación</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                    .container { max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                    h1 { color: #d32f2f; margin: 0 0 10px 0; }
                    p { color: #666; font-size: 16px; line-height: 1.6; }
                    a { display: inline-block; background: #667eea; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; margin-top: 20px; }
                    a:hover { background: #764ba2; }
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
                <h1>¡Email Confirmado!</h1>
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
                <h1>Error Procesando Confirmación</h1>
                <p>{str(e)}</p>
                <p>Por favor, intenta nuevamente o contacta a soporte.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)


@router.get(
    "/reset-password",
    summary="🌉 Puente: Restablecer contraseña desde email",
)
async def reset_password_bridge(token: str):
    """
    🌉 PUENTE: Endpoint que actúa como intermediario entre el email y la app.

    FLUJO:
    1. Email contiene: https://api.misboletas.tech/api/v1/bridges/reset-password?token=XXX
    2. Usuario hace click → Llama este endpoint
    3. Este endpoint:
       - Valida el token con Supabase
       - Si es válido → Devuelve HTML con JS que abre la app
       - Si es inválido → Muestra error amigable

    VENTAJAS:
    - El link siempre funciona (usa https, no deep link)
    - Si la app no está instalada, muestra error legible
    - Si la app está instalada, abre automáticamente
    - Funciona en emails, SMS, cualquier lado
    """
    try:
        logger.info(f"[🌉 PUENTE] Reset password bridge called with token")

        if not token:
            logger.error("[ERROR] No token provided")
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Error de Recuperación</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                    .container { max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                    h1 { color: #d32f2f; margin: 0 0 10px 0; }
                    p { color: #666; font-size: 16px; line-height: 1.6; }
                    a { display: inline-block; background: #667eea; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; margin-top: 20px; }
                    a:hover { background: #764ba2; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Token Inválido</h1>
                    <p>El link de recuperación no contiene un token válido.</p>
                    <p><strong>¿Qué hacer?</strong></p>
                    <p>Por favor, solicita un nuevo email de recuperación desde la app.</p>
                    <a href="https://misboletas.tech">Volver al inicio</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)

        # ✅ CONSTRUIR DEEP LINK Y DEVOLVER HTML CON JAVASCRIPT QUE LO ABRE
        deep_link = f"misboletas://reset-password?token={token}"
        logger.info(f"[🔗 PUENTE] Opening deep link: {deep_link}")

        # HTML con JavaScript que intenta abrir el deep link
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Restablecer Contraseña</title>
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
                <h1>🔐 Restablecer Contraseña</h1>
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
        logger.error(f"[ERROR] Reset password bridge failed: {str(e)}")
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
                <h1>Error Procesando Recuperación</h1>
                <p>{str(e)}</p>
                <p>Por favor, intenta nuevamente o contacta a soporte.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)
