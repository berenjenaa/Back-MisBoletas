"""
Configuración de FastAPI-Mail para envío de emails.

Inicializa el cliente de correo con las credenciales de Gmail.
"""

from fastapi_mail import FastMail, ConnectionConfig
from app.core.config import settings

# =======================================================================
# === CONFIGURACIÓN DE CONEXIÓN DE EMAIL
# =======================================================================

email_config = ConnectionConfig(
    mail_username=settings.MAIL_USERNAME,
    mail_password=settings.MAIL_PASSWORD,
    mail_from=settings.MAIL_FROM,
    mail_port=settings.MAIL_PORT,
    mail_server=settings.MAIL_SERVER,
    mail_starttls=settings.MAIL_STARTTLS,
    mail_ssl_tls=settings.MAIL_SSL_TLS,
    use_credentials=settings.MAIL_USE_CREDENTIALS,
)

# Instancia global de FastMail
fast_mail = FastMail(email_config)
