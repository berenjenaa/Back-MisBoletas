import logging
from fastapi import FastAPI

# --- Importación de Routers ---
from app.api.v1 import (
    user,
    product,
    documento,
    categorias,
    tickets,
    organizations,
    alerts,
    admin_gcs,
    webhooks,
    faqs,
)

# --- Importaciones del Core ---
from app.core.middleware import setup_middleware
from app.core.error_handlers import setup_exception_handlers
from app.core.config import settings, supabase
from app.db.supabase import supabase_admin


# --- 1. Función de inicialización ---
def startup_event():
    """Verifica la conexión con Supabase y la configuración de email al iniciar."""
    logging.info("[INFO] Starting MisBoletas API...")
    logging.info(f"[DEBUG] SUPABASE_URL configured: {bool(settings.SUPABASE_URL)}")
    logging.info(f"[DEBUG] SUPABASE_KEY configured: {bool(settings.SUPABASE_KEY)}")
    logging.info(
        f"[DEBUG] SUPABASE_SERVICE_ROLE_KEY configured: {bool(settings.SUPABASE_SERVICE_ROLE_KEY)}"
    )
    logging.info(f"[DEBUG] ENV mode: {settings.ENV}")

    if supabase:
        logging.info("[OK] Supabase client initialized")
    else:
        logging.warning("[WARNING] Supabase client not initialized correctly")

    # Verificar admin client
    if supabase_admin.is_connected():
        logging.info("[✅ OK] Supabase ADMIN client initialized with SERVICE_ROLE_KEY")
    else:
        logging.warning(
            "[⚠️ WARNING] Supabase ADMIN client NOT initialized - using anon key with RLS"
        )
        if settings.ENV == "render":
            logging.error(
                "[❌ CRITICAL] SERVICE_ROLE_KEY missing in Render! All DB operations will fail!"
            )

    # Verificar configuración de email (Resend)
    logging.info("\n" + "=" * 60)
    logging.info("EMAIL CONFIGURATION VERIFICATION")
    logging.info("=" * 60)

    if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
        logging.info(f"[OK] MAIL_USERNAME: {settings.MAIL_USERNAME}")
        logging.info(f"[OK] MAIL_FROM: {settings.MAIL_FROM}")
        logging.info(f"[OK] MAIL_SERVER: {settings.MAIL_SERVER}")
        logging.info(f"[OK] MAIL_PORT: {settings.MAIL_PORT}")
        logging.info(f"[OK] MAIL_SSL_TLS: {settings.MAIL_SSL_TLS}")

        # Validar que sea Resend + misboletas.tech
        if (
            settings.MAIL_USERNAME == "resend"
            and settings.MAIL_SERVER == "smtp.resend.com"
        ):
            if settings.MAIL_FROM and "misboletas.tech" in settings.MAIL_FROM:
                logging.info(
                    "[✅ OK] Email configuration is valid for Resend + misboletas.tech domain"
                )
            else:
                logging.warning(
                    f"[⚠️ WARNING] MAIL_FROM domain mismatch. Expected misboletas.tech, got {settings.MAIL_FROM}"
                )
        else:
            logging.warning("[⚠️ WARNING] Email provider might not be Resend")
    else:
        logging.warning(
            "[⚠️ WARNING] Email credentials not configured - transactional emails disabled"
        )

    logging.info("=" * 60 + "\n")

    # Mensaje final con acceso a docs
    logging.info("[OK] Server ready - Access docs at: http://localhost:8080/docs")


# --- 2. Metadatos para ordenar los tags en /docs ---
tags_metadata = [
    {
        "name": "Usuarios",
        "description": "Autenticación y gestión de tu cuenta. Comienza aquí.",
    },
    {
        "name": "Productos",
        "description": "Crear, listar y gestionar tus productos.",
    },
    {
        "name": "Categorías",
        "description": "Organizar productos por categorías personalizadas.",
    },
    {
        "name": "Organizaciones",
        "description": "Gestionar organizaciones (familia, empresa, jjvv, clubs).",
    },
    {
        "name": "Documentos",
        "description": "Subir archivos (boletas, garantías) con OCR automático.",
    },
    {
        "name": "Alertas",
        "description": "Alertas de vencimiento de garantías.",
    },
    {
        "name": "Tickets",
        "description": "Gestión de tickets de soporte técnico.",
    },
]

# --- 3. Descripción detallada para /docs ---
api_description = """
API MisBoletas - Gestión de Productos y Documentos

Esta API permite gestionar productos, documentos y realizar extracción automática de datos mediante OCR.

## Primeros Pasos

1. POST /api/v1/users/register - Crear cuenta
2. POST /api/v1/users/login - Obtener token
3. Usar el botón "Authorize" con tu Bearer token
4. Crear productos en /api/v1/productos
5. Subir documentos con OCR en /api/v1/documentos/upload/{producto_id}

## Modulos Principales

- Usuarios: Registro, login y gestión de perfiles
- Productos: Crear, listar, actualizar y eliminar productos
- Documentos: Subir archivos con OCR automático
- Categorías: Organizar productos
"""

# --- 4. Crear aplicación FastAPI ---
app = FastAPI(
    title="MisBoletas API",
    description=api_description,
    version="1.0.0",
    on_startup=[startup_event],
    openapi_tags=tags_metadata,
)

# --- 5. Configurar Middleware ---
setup_middleware(app)

# --- 6. Configurar Exception Handlers ---
setup_exception_handlers(app)

# --- 7. Registrar Routers de la API ---
api_v1_prefix = "/api/v1"

app.include_router(user.router, prefix=api_v1_prefix, tags=["Usuarios"])
app.include_router(product.router, prefix=api_v1_prefix, tags=["Productos"])
app.include_router(categorias.router, prefix=api_v1_prefix, tags=["Categorías"])
app.include_router(organizations.router, prefix=api_v1_prefix, tags=["Organizaciones"])
app.include_router(documento.router, prefix=api_v1_prefix, tags=["Documentos"])
app.include_router(alerts.router, prefix=api_v1_prefix, tags=["Alertas"])
app.include_router(tickets.router, prefix=api_v1_prefix, tags=["Tickets"])
app.include_router(faqs.router, prefix=api_v1_prefix, tags=["FAQs"])
app.include_router(admin_gcs.router, prefix=api_v1_prefix)
app.include_router(webhooks.router, prefix=api_v1_prefix)


# --- 8. Endpoints de la App Principal (Raíz y Salud) ---


@app.get("/", tags=["App Status"])
async def root():
    """Endpoint raíz para verificar que la API está funcionando."""
    return {
        "message": "MisBoletas API",
        "version": "1.0.0",
        "docs": "/docs",
        "environment": settings.ENV,
    }


@app.get("/health", tags=["App Status"])
async def health_check():
    """Endpoint de health check para servicios como Render."""
    return {
        "status": "healthy",
        "environment": settings.ENV,
        "database": "connected",
    }
