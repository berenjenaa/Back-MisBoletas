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
import logging
import magic
from datetime import timedelta
from PIL import Image
import io

# ✅ IMPORTACIONES PARA FIRMA CLOUD RUN
import google.auth
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)


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
                credentials = service_account.Credentials.from_service_account_file(
                    creds_data
                )
            # Si es JSON string (Render/Producción)
            else:
                try:
                    creds_dict = json.loads(creds_data)
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_dict
                    )
                except json.JSONDecodeError:
                    raise ValueError(
                        "GOOGLE_APPLICATION_CREDENTIALS debe ser una ruta válida o JSON string"
                    )

            self.client = storage.Client(
                credentials=credentials, project=settings.GCS_PROJECT_ID
            )
        else:
            # Usar credenciales por defecto del entorno (Cloud Run)
            self.client = storage.Client(project=settings.GCS_PROJECT_ID)

        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)

    def _validate_file(self, file: UploadFile) -> None:
        """Valida el archivo usando detección MIME con python-magic."""
        allowed_mimetypes = {"image/jpeg", "image/png", "application/pdf"}

        file_header = file.file.read(2048)
        file.file.seek(0)

        if not file_header:
            raise HTTPException(status_code=400, detail="Archivo vacío no permitido")

        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(file_header)

            if mime_type not in allowed_mimetypes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de archivo no permitido. Solo JPEG, PNG y PDF. Detectado: {mime_type}",
                )
        except Exception as e:
            logger.error(f"Error detectando MIME type: {e}")
            raise HTTPException(
                status_code=400, detail="No se pudo validar el tipo de archivo"
            )

        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        max_size_bytes = settings.GCS_MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo muy grande. Máximo {settings.GCS_MAX_FILE_SIZE_MB}MB",
            )

    def _generate_blob_name(self, user_id: str, product_id: str, filename: str) -> str:
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = "".join(
            c for c in filename if c.isalnum() or c in ("-", "_", ".")
        )
        return f"user_{user_id}/product_{product_id}/{unique_id}_{safe_filename}"

    async def upload_file(
        self, file: UploadFile, user_id: str, product_id: str
    ) -> dict:
        try:
            self._validate_file(file)
            file_content = await file.read()
            file.file.seek(0)

            if file.content_type and file.content_type.startswith("image/"):
                try:
                    img = Image.open(io.BytesIO(file_content))
                    if img.size[0] > 2048 or img.size[1] > 2048:
                        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=85, optimize=True)
                    file_content = buffer.getvalue()
                    file.content_type = "image/jpeg"
                except Exception as e:
                    logger.warning(f"No se pudo comprimir imagen: {e}")

            blob_name = self._generate_blob_name(user_id, product_id, file.filename)
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(
                file_content,
                content_type=file.content_type or "application/octet-stream",
            )

            public_url = (
                f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{blob_name}"
            )
            gcs_uri = f"gs://{settings.GCS_BUCKET_NAME}/{blob_name}"

            return {
                "blob_name": blob_name,
                "public_url": public_url,
                "gcs_uri": gcs_uri,
                "content_type": file.content_type,
                "size_bytes": len(file_content),
                "filename": file.filename,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[ERROR] Failed to upload file: {e}")
            raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

    def delete_file(self, blob_name: str) -> bool:
        try:
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
                return True
            raise HTTPException(status_code=404, detail="File not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete file: {e}")
            raise HTTPException(
                status_code=500, detail=f"File deletion error: {str(e)}"
            )

    def get_signed_url(
        self, blob_name: str, expiration_seconds: Optional[int] = None
    ) -> str:
        """Genera una URL firmada temporal (FIX para Cloud Run)."""
        try:
            blob = self.bucket.blob(blob_name)

            # Nota: blob.exists() es una llamada de red extra.
            # Si confías en que el blob existe, podrías comentarlo para más velocidad.
            if not blob.exists():
                raise HTTPException(status_code=404, detail="File not found")

            expiration = expiration_seconds or settings.GCS_SIGNED_URL_EXPIRATION

            # ✅ LÓGICA ESPECIAL PARA CLOUD RUN (Firma remota IAM)
            signing_args = {}

            # Si NO hay archivo de credenciales local, asumimos Cloud Run/Environment Identity
            if not settings.GOOGLE_APPLICATION_CREDENTIALS:
                try:
                    # Obtener credenciales por defecto (la identidad de Cloud Run)
                    credentials, _ = google.auth.default()

                    # Refrescar para asegurar que tenemos el token y el email
                    if not credentials.token:
                        credentials.refresh(google_requests.Request())

                    # Inyectar credenciales explícitas para que la librería use la API de IAM
                    if hasattr(credentials, "service_account_email"):
                        signing_args["service_account_email"] = (
                            credentials.service_account_email
                        )
                    if hasattr(credentials, "token"):
                        signing_args["access_token"] = credentials.token

                    logger.info(
                        f"[AUTH] Firmando URL con identidad: {getattr(credentials, 'service_account_email', 'Desconocido')}"
                    )

                except Exception as auth_error:
                    logger.warning(
                        f"[AUTH] Error obteniendo identidad de Cloud Run: {auth_error}"
                    )

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="GET",
                **signing_args,  # Pasamos los argumentos de firma
            )

            logger.info(f"[OK] Signed URL generated for: {blob_name}")
            return url
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate signed URL: {e}")
            raise HTTPException(
                status_code=500, detail=f"URL generation error: {str(e)}"
            )

    def file_exists(self, blob_name: str) -> bool:
        try:
            blob = self.bucket.blob(blob_name)
            return blob.exists()
        except Exception:
            return False


def get_gcs_service() -> Optional[GCSService]:
    if not settings.gcs_enabled:
        return None
    return GCSService()
