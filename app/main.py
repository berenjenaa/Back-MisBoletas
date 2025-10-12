from fastapi import FastAPI
from app.api.v1 import user, product, documento, categorias
from app.core.middleware import setup_middleware
from app.core.error_handlers import setup_exception_handlers
from app.db.session import engine, Base
from app.core.config import settings
from sqlalchemy import text, inspect
import os

# Funcion Para Crear Tablas
def create_tables():
    """
    Función que crea todas las tablas de SQLAlchemy en la base de datos de PostgreSQL.
    Se ejecuta al iniciar el servidor (on_startup).
    """
    print("🔄 Intentando crear tablas en la base de datos...")

    # Importar TODOS los modelos para que Base.metadata los conozca
    from app.models import Usuario, Categoria, ProductoCategoria, Producto, Documento
    
    inspector = inspect(engine)
    
    # 1. Verificar y recrear tabla documentos si tiene estructura incorrecta
    try:
        if inspector.has_table("documentos"):
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'documentos' AND column_name = 'url_gcs'
                """))
                
                if not result.fetchone():
                    print("⚠️  Tabla documentos tiene estructura incorrecta. Recreando...")
                    conn.execute(text("DROP TABLE IF EXISTS documentos CASCADE;"))
                    conn.commit()
                    print("✅ Tabla documentos eliminada")
    except Exception as e:
        print(f"⚠️  Error al verificar tabla documentos: {e}")
    
    # 2. Verificar y recrear tablas de categorías si tienen estructura incorrecta
    try:
        # Verificar si existe tabla categorias con la columna 'color'
        if inspector.has_table("categorias"):
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'categorias' AND column_name = 'color'
                """))
                
                if not result.fetchone():
                    print("⚠️  Tabla categorias tiene estructura antigua. Recreando...")
                    conn.execute(text("DROP TABLE IF EXISTS productocategorias CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS categorias CASCADE;"))
                    conn.commit()
                    print("✅ Tablas de categorías eliminadas")
    except Exception as e:
        print(f"⚠️  Error al verificar tablas de categorías: {e}")
    
    # 3. Crear todas las tablas definidas en los modelos
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente o ya existentes.")
    
    # 4. Mostrar tablas existentes
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 Tablas en la base de datos: {', '.join(tables)}")
    except Exception as e:
        print(f"⚠️  No se pudieron listar las tablas: {e}")

# Crear aplicación FastAPI
app = FastAPI(
    title="MisBoletas API",
    description="API optimizada para gestión de productos, garantías y boletas con Google Cloud Storage.",
    version="2.0.0",
    on_startup=[create_tables]  # Crear tablas al iniciar el servidor
)

# Configurar middleware (CORS, logging, etc.)
setup_middleware(app)

# Configurar manejadores de errores globales
setup_exception_handlers(app)

# Registrar routers de endpoints
app.include_router(user.router, prefix="/api/v1", tags=["Usuarios"])
app.include_router(product.router, prefix="/api/v1", tags=["Productos"])
app.include_router(categorias.router, prefix="/api/v1", tags=["Categorías"])
app.include_router(documento.router, prefix="/api/v1", tags=["Documentos"])


@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está funcionando."""
    return {
        "message": "MisBoletas API",
        "version": "1.0.0",
        "docs": "/docs",
        "environment": settings.ENV,
        "gcs_enabled": settings.gcs_enabled
    }

@app.get("/health")
async def health_check():
    """Endpoint de health check para Render."""
    return {
        "status": "healthy",
        "environment": settings.ENV,
        "database": "connected",
        "gcs_enabled": settings.gcs_enabled,
        "gcs_bucket": settings.GCS_BUCKET_NAME if settings.gcs_enabled else None
    }

@app.get("/test-gcs")
async def test_gcs():
    """Endpoint para verificar la configuración de Google Cloud Storage."""
    try:
        from app.services.gcs_service import get_gcs_service
        
        if not settings.gcs_enabled:
            return {
                "status": "disabled",
                "message": "Google Cloud Storage no está habilitado",
                "gcs_enabled": False
            }
        
        gcs_service = get_gcs_service()
        
        if not gcs_service:
            return {
                "status": "error",
                "message": "No se pudo inicializar el servicio GCS",
                "gcs_credentials": settings.GOOGLE_APPLICATION_CREDENTIALS,
                "gcs_bucket": settings.GCS_BUCKET_NAME
            }
        
        # Intentar listar archivos del bucket (solo verifica conexión)
        bucket = gcs_service.client.bucket(settings.GCS_BUCKET_NAME)
        exists = bucket.exists()
        
        if not exists:
            return {
                "status": "error",
                "message": f"El bucket '{settings.GCS_BUCKET_NAME}' no existe o no tienes permisos"
            }
        
        # Contar archivos
        blobs = list(bucket.list_blobs(max_results=10))
        
        return {
            "status": "success",
            "message": "Google Cloud Storage funcionando correctamente",
            "bucket_name": settings.GCS_BUCKET_NAME,
            "bucket_exists": True,
            "files_count": len(blobs),
            "sample_files": [blob.name for blob in blobs[:5]]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al conectar con GCS: {str(e)}",
            "error_type": type(e).__name__
        }


# Para ejecutar con uvicorn desde la terminal
# El puerto se toma de la variable de entorno PORT (Render) o usa 8000 por defecto
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)