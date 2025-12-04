"""
Configuración de FastAPI-Mail para envío de emails.

Inicializa el cliente de correo con las credenciales de Gmail.
"""

from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# =======================================================================
# === CONFIGURACIÓN DE CONEXIÓN DE EMAIL
# =======================================================================

# Solo inicializar si hay credenciales de email configuradas
email_config: Optional[ConnectionConfig] = None
fast_mail: Optional[FastMail] = None

if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
    try:
        email_config = ConnectionConfig(
            mail_username=settings.MAIL_USERNAME,
            mail_password=settings.MAIL_PASSWORD,
            mail_from=settings.MAIL_FROM or settings.MAIL_USERNAME,
            mail_port=settings.MAIL_PORT,
            mail_server=settings.MAIL_SERVER,
            mail_starttls=settings.MAIL_STARTTLS,
            mail_ssl_tls=settings.MAIL_SSL_TLS,
            use_credentials=settings.MAIL_USE_CREDENTIALS,
        )
        fast_mail = FastMail(email_config)
        print("[OK] Email configuration initialized successfully")
    except Exception as e:
        print(f"[WARNING] Email configuration failed: {e}")
else:
    print("[WARNING] Email credentials not configured - email functionality disabled")


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
        logger.error(f"[ERROR] Failed to send email synchronously: {e}", exc_info=True)
        return False
