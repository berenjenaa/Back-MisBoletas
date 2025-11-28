"""
Este archivo lee las variables de entorno del archivo .env
y las hace disponibles para toda la aplicación.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic.
    Lee automáticamente del archivo .env
    """

    # === CONFIGURACIÓN DE BASE DE DATOS (SUPABASE) ===
    SUPABASE_URL: str  # DESDE .ENV - URL de Supabase
    SUPABASE_KEY: str  # DESDE .ENV - Clave de API de Supabase (anon key)
    SUPABASE_SERVICE_ROLE_KEY: (
        str  # DESDE .ENV - Service role key (sin restricciones RLS)
    )
    ENV: str = "local"  # local, development o production

    # === CONFIGURACIÓN DE SEGURIDAD ===
    SECRET_KEY: str  # DESDE .ENV
    JWT_ALGORITHM: str = "HS256"  # Algoritmo JWT
    JWT_EXPIRE_MINUTES: int = 30  # Minutos de expiración del token

    # === CONFIGURACIÓN DE LA APP ===
    DEBUG: bool = True  # Modo debug para desarrollo
    API_PREFIX: str = "/api"  # Prefijo para todas las rutas
    ALLOW_ORIGIN: str = "*"  # Orígenes permitidos para CORS
    PORT: int = 8080  # Puerto por defecto (Cloud Run estándar)

    # === CONFIGURACIÓN DE GOOGLE CLOUD STORAGE ===
    GCS_BUCKET_NAME: str = ""  # Nombre del bucket de GCS
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = (
        None  # Ruta al archivo de credenciales JSON
    )
    GCS_PROJECT_ID: Optional[str] = None  # ID del proyecto de GCP

    # === CONFIGURACIÓN AVANZADA DE GCS ===
    GCS_SIGNED_URL_EXPIRATION: int = 7 * 24 * 60 * 60  # 7 días en segundos
    GCS_MAX_FILE_SIZE_MB: int = 10  # Tamaño máximo de archivo (MB)

    # === CONFIGURACIÓN DE GOOGLE DOCUMENT AI ===
    DOCUMENTAI_PROJECT_ID: Optional[str] = None
    DOCUMENTAI_LOCATION: Optional[str] = None
    DOCUMENTAI_PROCESSOR_ID: Optional[str] = None

    @property
    def is_production(self) -> bool:
        """Verifica si estamos en producción"""
        return self.ENV == "production"

    @property
    def gcs_enabled(self) -> bool:
        """Verifica si GCS está habilitado"""
        return bool(self.GCS_BUCKET_NAME)

    class Config:
        # Archivo donde están las variables de entorno
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True  # Las variables deben tener exactamente el mismo nombre
        extra = "ignore"  # Ignorar variables extra del .env (como SQLSERVER_*)


# Instancia global de configuración
# Usar en toda la app como: from app.core.config import settings
settings = Settings()

# === INICIALIZAR CLIENTE SUPABASE ===
try:
    from supabase import create_client

    # Usar service_role_key para tener acceso completo sin restricciones RLS
    # Cambio: Era "settings.SUPABASE_KEY" (anon) → Ahora "settings.SUPABASE_SERVICE_ROLE_KEY" (service role)
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
except Exception as e:
    print(f"[ERROR] Failed to initialize Supabase client: {e}")
    supabase = None
