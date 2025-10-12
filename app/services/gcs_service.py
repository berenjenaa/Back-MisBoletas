"""
Servicio de Google Cloud Storage para gestión de archivos.
Maneja upload, delete y generación de URLs firmadas.
"""

from google.cloud import storage
from google.oauth2 import service_account
from app.core.config import settings
from fastapi import HTTPException, UploadFile
from typing import Optional
import uuid
import os
from datetime import timedelta

class GCSService:
    """Servicio para interactuar con Google Cloud Storage."""
    
    def __init__(self):
        """Inicializa el cliente de GCS con credenciales."""
        if not settings.gcs_enabled:
            raise ValueError("Google Cloud Storage no está configurado.")
        
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            import json
            import os
            
            creds_data = settings.GOOGLE_APPLICATION_CREDENTIALS
            
            # Si es un archivo local (desarrollo)
            if os.path.exists(creds_data):
                credentials = service_account.Credentials.from_service_account_file(creds_data)
            # Si es JSON string (Render/Producción)
            else:
                try:
                    creds_dict = json.loads(creds_data)
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                except json.JSONDecodeError:
                    raise ValueError(
                        "GOOGLE_APPLICATION_CREDENTIALS debe ser una ruta válida o JSON string"
                    )
            
            self.client = storage.Client(credentials=credentials, project=settings.GCS_PROJECT_ID)
        else:
            # Usar credenciales por defecto del entorno
            self.client = storage.Client(project=settings.GCS_PROJECT_ID)
        
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
    
    def _validate_file(self, file: UploadFile) -> None:
        """Valida el archivo antes de subirlo."""
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido")
        
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        max_size_bytes = settings.GCS_MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(status_code=400, detail=f"Archivo muy grande")
    
    def _generate_blob_name(self, user_id: int, product_id: int, filename: str) -> str:
        """Genera un nombre único para el blob en GCS."""
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.'))
        blob_name = f"user_{user_id}/product_{product_id}/{unique_id}_{safe_filename}"
        return blob_name
    
    async def upload_file(self, file: UploadFile, user_id: int, product_id: int) -> dict:
        """Sube un archivo a Google Cloud Storage."""
        try:
            self._validate_file(file)
            blob_name = self._generate_blob_name(user_id, product_id, file.filename)
            blob = self.bucket.blob(blob_name)
            file_content = await file.read()
            blob.upload_from_string(file_content, content_type=file.content_type or 'application/octet-stream')
            
            # No llamar a make_public() si el bucket tiene Uniform bucket-level access
            # En su lugar, usar la URL pública directamente
            public_url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{blob_name}"
            
            return {
                "blob_name": blob_name,
                "public_url": public_url,
                "content_type": file.content_type,
                "size_bytes": len(file_content),
                "filename": file.filename
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al subir archivo: {str(e)}")
    
    def delete_file(self, blob_name: str) -> bool:
        """Elimina un archivo de Google Cloud Storage."""
        try:
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
                return True
            else:
                raise HTTPException(status_code=404, detail="Archivo no encontrado")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al eliminar archivo: {str(e)}")
    
    def get_signed_url(self, blob_name: str, expiration_seconds: Optional[int] = None) -> str:
        """Genera una URL firmada temporal."""
        try:
            blob = self.bucket.blob(blob_name)
            if not blob.exists():
                raise HTTPException(status_code=404, detail="Archivo no encontrado")
            
            expiration = expiration_seconds or settings.GCS_SIGNED_URL_EXPIRATION
            url = blob.generate_signed_url(version="v4", expiration=timedelta(seconds=expiration), method="GET")
            return url
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al generar URL: {str(e)}")
    
    def file_exists(self, blob_name: str) -> bool:
        """Verifica si un archivo existe en GCS."""
        try:
            blob = self.bucket.blob(blob_name)
            return blob.exists()
        except Exception:
            return False

def get_gcs_service() -> Optional[GCSService]:
    """Obtiene una instancia del servicio de GCS."""
    if not settings.gcs_enabled:
        return None
    return GCSService()