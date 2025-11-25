import logging
from fastapi import FastAPI

# --- Importación de Routers ---
from app.api.v1 import user, product, documento, categorias, ocr

# --- Importaciones del Core ---
from app.core.middleware import setup_middleware
from app.core.error_handlers import setup_exception_handlers
from app.core.config import settings, supabase


# --- 1. Función de inicialización ---
def startup_event():
    """Verifica la conexión con Supabase al iniciar."""
    logging.info("[INFO] Starting MisBoletas API...")
    if supabase:
        logging.info("[OK] Supabase client initialized")
    else:
        logging.warning("[WARNING] Supabase client not initialized correctly")

    # Mensaje final con acceso a docs
    logging.info("[OK] Server ready - Access docs at: http://localhost:8080/docs")


# --- 2. Metadatos para ordenar los tags en /docs ---
tags_metadata = [
    {
        "name": "Usuarios",
        "description": "Autenticación y gestión de tu cuenta. [EMPEZAR AQUI]",
    },
    {
        "name": "OCR",
        "description": "Procesamiento y extracción de datos de documentos (boletas).",
    },
    {
        "name": "Productos",
        "description": "Gestión de tus productos.",
    },
    {
        "name": "Categorías",
        "description": "Organización de productos por categorías.",
    },
    {
        "name": "Documentos",
        "description": "Subida y gestión de archivos (boletas, garantías).",
    },
]

# --- 3. Descripción detallada para /docs ---
api_description = """
Bienvenido a la API de MisBoletas.

Esta API te permite gestionar usuarios, productos y sus documentos (boletas/garantías),
incluyendo la extracción automática de datos mediante OCR.

## Guía de Primeros Pasos

1.  [Regístrate] POST /api/v1/users/register
2.  [Inicia Sesión] POST /api/v1/users/login (Obtén tu token)
3.  [Autoriza] Usa el botón "Authorize" con tu Bearer token.
4.  [Prueba el OCR] POST /api/v1/ocr/procesar-boleta (Sube una imagen de boleta)
5.  [Gestiona] Usa los endpoints de /productos, /categorias, /documentos.
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

# --- 6. Configurar Manejadores de Errores Globales ---
setup_exception_handlers(app)

# --- 7. Registrar Routers de la API ---
api_v1_prefix = "/api/v1"

app.include_router(user.router, prefix=api_v1_prefix, tags=["Usuarios"])
app.include_router(ocr.router, prefix=api_v1_prefix, tags=["OCR"])
app.include_router(product.router, prefix=api_v1_prefix, tags=["Productos"])
app.include_router(categorias.router, prefix=api_v1_prefix, tags=["Categorías"])
app.include_router(documento.router, prefix=api_v1_prefix, tags=["Documentos"])


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
