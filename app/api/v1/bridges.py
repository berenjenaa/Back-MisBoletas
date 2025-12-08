"""
Puentes de Email (Bridges)

Estos endpoints actúan como intermediarios entre los emails de Supabase y la app.
- Reciben tokens/OTP del email
- Devuelven HTML con deep links a la app
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import logging

from app.db.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bridges")


@router.get("/confirm", summary="Puente: Confirmar email desde enlace")
async def confirm_email(token: str, email: str, type: str = "signup"):
    """
    Endpoint que actúa como intermediario entre Supabase email y la app.

    Flujo:
    1. Email contiene: https://api.misboletas.tech/api/v1/bridges/confirm?token=XXX&email=YYY&type=signup
    2. Usuario hace click → Llama este endpoint
    3. Verifica OTP con Supabase y devuelve deep link a la app
    """
    try:
        logger.info(f"[PUENTE] Confirm endpoint - email={email}, type={type}")

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
            return HTMLResponse(
                content="<h1>❌ Token Inválido o Expirado</h1><p>Por favor intenta registrarte nuevamente.</p>",
                status_code=400,
            )

        access_token = res.session.access_token
        refresh_token = res.session.refresh_token
        user_id = res.user.id

        logger.info(f"[OK] OTP verified for {email}")

        # Construir deep link a la app
        deep_link = f"misboletas://auth-callback?access_token={access_token}&refresh_token={refresh_token}&user_id={user_id}"

        # HTML simple que abre el deep link
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Confirmando...</title>
        </head>
        <body>
            <p>Redirigiendo a tu app...</p>
            <script>
                window.location.href = '{deep_link}';
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html)

    except Exception as e:
        logger.error(f"[ERROR] Confirm endpoint failed: {str(e)}")
        return HTMLResponse(
            content="<h1>❌ Error</h1><p>Por favor intenta más tarde.</p>",
            status_code=500,
        )


@router.get(
    "/reset-password",
    summary="🌉 Puente: Restablecer contraseña desde email",
)
async def reset_password_bridge(token: str = None):
    """
    🌉 PUENTE: Endpoint para restablecer contraseña
    """
    try:
        logger.info(f"[🌉 PUENTE] Reset password bridge called")

        if not token:
            logger.error("[ERROR] No token provided")
            return HTMLResponse(content="<h1>Token inválido</h1>", status_code=400)

        # Construir deep link a la app
        deep_link = f"misboletas://reset-password?token={token}"
        logger.info(f"[🔗 PUENTE] Opening deep link: {deep_link}")

        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Restablecer Contraseña</title>
            <script>
                window.location.href = '{deep_link}';
            </script>
        </head>
        <body>
            <p>Redirigiendo...</p>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html)

    except Exception as e:
        logger.error(f"[ERROR] Reset password bridge failed: {str(e)}")
        return HTMLResponse(content="<h1>Error</h1>", status_code=500)
