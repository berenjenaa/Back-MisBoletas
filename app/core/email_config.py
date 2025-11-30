"""
Configuración de FastAPI-Mail para envío de emails.

Inicializa el cliente de correo con las credenciales de Gmail.
"""

from fastapi_mail import FastMail, ConnectionConfig
from app.core.config import settings
from typing import Optional

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
