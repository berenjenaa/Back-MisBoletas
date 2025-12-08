"""
Puentes de Email (Bridges)

Estos endpoints actúan como intermediarios entre los emails de Supabase y la app.
- Reciben tokens/OTP del email
- Devuelven HTML con deep links a la app
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
import logging

from app.db.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bridges")


@router.get("/confirm", summary="Puente: Confirmar email desde enlace")
async def confirm_email(
    access_token: str = Query(None),
    refresh_token: str = Query(None),
    user_id: str = Query(None),
    email: str = Query(None),
    type: str = Query(None),
):
    """
    Puente para confirmación de email.

    Supabase puede enviar el access_token directamente en el hash.
    Si viene con tokens, usamos esos. Si no, abrimos la app con el email.
    """
    try:
        logger.info(f"[PUENTE] Confirm endpoint - email={email}, type={type}")

        # Si Supabase envió el access_token, usarlo directamente
        if access_token and refresh_token and user_id:
            logger.info(f"[OK] Tokens recibidos de Supabase")
            deep_link = f"misboletas://auth-callback?access_token={access_token}&refresh_token={refresh_token}&user_id={user_id}"
        elif email:
            # Si solo tenemos email, abrir la app para que verifique
            deep_link = f"misboletas://confirm-email?email={email}"
        else:
            logger.error("[ERROR] No parámetros válidos")
            return HTMLResponse(
                content="<h1>❌ Parámetros inválidos</h1>",
                status_code=400,
            )

        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Confirmando...</title>
        </head>
        <body>
            <p>Abriendo MisBoletas...</p>
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


@router.get("/reset-password", summary="Puente: Restablecer contraseña")
async def reset_password_bridge(
    access_token: str = Query(None),
    refresh_token: str = Query(None),
    user_id: str = Query(None),
    email: str = Query(None),
    type: str = Query(None),
):
    """
    Puente para restablecer contraseña.
    Supabase puede enviar tokens en el hash, o podemos abrir la app con el email.
    """
    try:
        logger.info(f"[PUENTE] Reset password bridge - email={email}, type={type}")

        # Si Supabase envió tokens de recovery, usarlos
        if access_token and type == "recovery":
            logger.info(f"[OK] Recovery tokens recibidos de Supabase")
            # Pasar access_token como 'token' para que la app lo reciba correctamente
            deep_link = f"misboletas://reset-password?token={access_token}"
        elif email:
            # Si solo tenemos email, abrir la app para reset password
            deep_link = f"misboletas://reset-password?email={email}"
        else:
            logger.error("[ERROR] No parámetros válidos")
            return HTMLResponse(
                content="<h1>❌ Parámetros inválidos</h1>",
                status_code=400,
            )

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
