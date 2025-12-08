"""
Configuración de Resend para envío de emails.

Usa la API REST de Resend en lugar de SMTP.
Resend es más confiable y fácil de configurar.
"""

import httpx
from app.core.config import settings
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

# =======================================================================
# === CONFIGURACIÓN DE RESEND API
# =======================================================================

RESEND_API_KEY = settings.MAIL_PASSWORD  # Usamos MAIL_PASSWORD como la API key
RESEND_FROM_EMAIL = settings.MAIL_FROM or "onboarding@resend.dev"
RESEND_API_URL = "https://api.resend.com/emails"

if not RESEND_API_KEY:
    logger.warning(
        "[⚠️ WARNING] RESEND_API_KEY no configurada - email functionality disabled"
    )
    print("[WARNING] RESEND_API_KEY not configured")
else:
    logger.info("[✅ OK] Resend API configurada correctamente")
    print("[OK] Resend API configured successfully")


# =======================================================================
# === FUNCIÓN PARA ENVIAR EMAILS VÍA RESEND
# =======================================================================


async def send_email(
    recipient_email: str,
    subject: str,
    html_content: str,
    recipients: Optional[list] = None,
) -> bool:
    """
    Envía un email HTML usando la API de Resend.

    Args:
        recipient_email: Email del destinatario
        subject: Asunto del email
        html_content: Contenido HTML del email
        recipients: Lista opcional de destinatarios adicionales

    Returns:
        bool: True si se envió exitosamente, False si no
    """
    try:
        if not RESEND_API_KEY:
            logger.warning(
                "[WARNING] Email service not configured - skipping email send"
            )
            return False

        # Construir lista de destinatarios
        email_recipients = recipients or [recipient_email]
        if recipient_email not in email_recipients:
            email_recipients.insert(0, recipient_email)

        # Payload para Resend
        payload = {
            "from": RESEND_FROM_EMAIL,
            "to": email_recipients,
            "subject": subject,
            "html": html_content,
        }

        # Headers con autenticación Bearer
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.info(f"[EMAIL] Enviando email a {recipient_email} via Resend API")

        # Hacer request POST a Resend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
            )

            if response.status_code in [200, 201]:
                logger.info(
                    f"[✅ EMAIL] Email enviado exitosamente a {recipient_email}"
                )
                return True
            else:
                logger.error(f"[❌ EMAIL] Resend API error: {response.status_code}")
                logger.error(f"[❌ EMAIL] Response: {response.text}")
                return False

    except httpx.TimeoutException:
        logger.error(f"[❌ EMAIL] Timeout conectando a Resend API")
        return False
    except Exception as e:
        logger.error(
            f"[❌ EMAIL] Error enviando email a {recipient_email}: {e}", exc_info=True
        )
        return False


# =======================================================================
# === FUNCIÓN SÍNCRONA ALTERNATIVA (para background tasks)
# =======================================================================


def send_email_sync(
    recipient_email: str,
    subject: str,
    html_content: str,
    recipients: Optional[list] = None,
) -> bool:
    """
    Versión síncrona de send_email para usar en background tasks.
    (Crea un event loop interno)
    """
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            send_email(recipient_email, subject, html_content, recipients)
        )
        loop.close()
        return result
    except Exception as e:
        logger.error(f"[❌ EMAIL] Error en send_email_sync: {e}")
        return False


# =======================================================================
# === FUNCIÓN PARA ENVIAR EMAILS
# =======================================================================


async def send_email(
    recipient_email: str,
    subject: str,
    html_content: str,
    recipients: Optional[list] = None,
) -> bool:
    """
    Envía un email HTML a un destinatario.

    Args:
        recipient_email: Email del destinatario
        subject: Asunto del email
        html_content: Contenido HTML del email
        recipients: Lista opcional de destinatarios adicionales

    Returns:
        bool: True si se envió exitosamente, False si no
    """
    try:
        if not fast_mail:
            logger.warning(
                "[WARNING] Email service not configured - skipping email send"
            )
            return False

        # Construir lista de destinatarios
        email_recipients = recipients or [recipient_email]
        if recipient_email not in email_recipients:
            email_recipients.insert(0, recipient_email)

        # Crear mensaje
        message = MessageSchema(
            subject=subject,
            recipients=email_recipients,
            body=html_content,
            subtype=MessageType.html,
        )

        # Enviar email
        await fast_mail.send_message(message)
        logger.info(f"[OK] Email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to send email to {recipient_email}: {e}", exc_info=True
        )
        return False


# =======================================================================
# === FUNCIÓN SÍNCRONA ALTERNATIVA (para background tasks)
# =======================================================================


def send_email_sync(
    recipient_email: str,
    subject: str,
    html_content: str,
    recipients: Optional[list] = None,
) -> bool:
    """
    Versión síncrona de send_email para usar en background tasks.
    (Crea un event loop interno)
    """
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            send_email(recipient_email, subject, html_content, recipients)
        )
        loop.close()
        return result
    except Exception as e:
        logger.error(f"[ERROR] Failed in send_email_sync: {e}")
        return False
