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
    
    # === CONFIGURACIÓN DE BASE DE DATOS ===
    DATABASE_URL: str                     # DESDE .ENV (Render la proporciona)
    EXTERNAL_DATABASE_URL: Optional[str] = None  # DESDE .ENV (opcional, para conexiones externas)
    ENV: str = "local"                # local o render

    # === CONFIGURACIÓN DE SEGURIDAD ===
    SECRET_KEY: str                           # DESDE .ENV
    JWT_ALGORITHM: str = "HS256"              # Algoritmo JWT
    JWT_EXPIRE_MINUTES: int = 30              # Minutos de expiración del token
    
    # === CONFIGURACIÓN DE LA APP ===
    DEBUG: bool = True                    # Modo debug para desarrollo
    API_PREFIX: str = "/api"              # Prefijo para todas las rutas
    ALLOW_ORIGIN: str = "*"               # Orígenes permitidos para CORS
    PORT: int = 8000                      # Puerto por defecto (Render lo sobrescribe)
    
    # === CONFIGURACIÓN DE GOOGLE CLOUD STORAGE ===
    GCS_BUCKET_NAME: str = ""                              # Nombre del bucket de GCS
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None   # Ruta al archivo de credenciales JSON
    GCS_PROJECT_ID: Optional[str] = None                   # ID del proyecto de GCP
    
    # === CONFIGURACIÓN AVANZADA DE GCS ===
    GCS_SIGNED_URL_EXPIRATION: int = 7 * 24 * 60 * 60  # 7 días en segundos
    GCS_MAX_FILE_SIZE_MB: int = 10                       # Tamaño máximo de archivo (MB)

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """
        Devuelve la URL que debe usar SQLAlchemy según el entorno:
        - local -> EXTERNAL_DATABASE_URL
        - render -> DATABASE_URL
        """
        if self.ENV == "render":
            return self.DATABASE_URL
        return self.EXTERNAL_DATABASE_URL or self.DATABASE_URL
    
    @property
    def is_production(self) -> bool:
        """Verifica si estamos en producción"""
        return self.ENV == "render"
    
    @property
    def gcs_enabled(self) -> bool:
        """Verifica si GCS está habilitado"""
        return bool(self.GCS_BUCKET_NAME)
    
    class Config:
        # Archivo donde están las variables de entorno
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True  # Las variables deben tener exactamente el mismo nombre
        extra = "ignore"  # Ignorar variables extra del .env (como SQLSERVER_*)

# Instancia global de configuración
# Usar en toda la app como: from app.core.config import settings
settings = Settings()