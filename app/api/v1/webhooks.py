"""
Webhooks de Supabase - Procesar eventos de BD automáticamente.
Se dispara cuando se crea un nuevo documento en la tabla documentos.
"""

from fastapi import APIRouter, Request, HTTPException, status
import logging
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from app.db.supabase import supabase_admin
from app.services.ocr_service import process_boleta_from_gcs_uri
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/documento-subido", summary="Webhook: Nuevo documento subido")
async def on_documento_created(request: Request):
    """
    Webhook de Supabase se dispara cuando:
    - Se inserta un nuevo registro en tabla "documentos"
    """
    try:
        # 1. Obtener payload
        payload = await request.json()

        if not payload or payload.get("type") != "INSERT":
            logger.warning(
                f"[WARNING] Webhook recibido pero no es INSERT: {payload.get('type')}"
            )
            return {"received": True}

        # 2. Extraer documento
        documento = payload.get("record", {})
        id_documento = documento.get("id_documento")
        blob_name = documento.get("blob_name")
        # El webhook recibe la URL pública, pero necesitamos reconstruir la URI gs://
        # gcs_uri_public = documento.get("url_gcs")
        id_usuario = documento.get("id_usuario")
        # IMPORTANTE: Necesitamos el mime_type (content_type)
        mime_type = documento.get("content_type", "application/pdf")

        if not id_documento or not blob_name:
            logger.error(f"[ERROR] Webhook incompleto: falta id_documento o blob_name")
            return {"received": True, "error": "Missing fields"}

        logger.info(f"[OK] Webhook recibido para documento: {id_documento}")

        # 4. Iniciar OCR en background (sin bloquear respuesta)
        # PASAMOS TODOS LOS DATOS NECESARIOS
        asyncio.create_task(
            procesar_documento_ocr(id_documento, blob_name, mime_type, id_usuario)
        )

        # 4. Responder inmediatamente
        return {
            "received": True,
            "id_documento": str(id_documento),
            "status": "procesando en background",
        }

    except Exception as e:
        logger.error(f"[ERROR] Webhook error: {e}", exc_info=True)
        return {"received": True, "error": str(e)}


async def procesar_documento_ocr(
    id_documento: str, blob_name: str, mime_type: str, id_usuario: str = None
):
    """
    Procesa OCR del documento en background.
    """
    try:
        logger.info(f"[INFO] Iniciando OCR para: {id_documento}")

        # 1. Marcar como procesando
        supabase_admin.get_table("documentos").update({"estado_ocr": "procesando"}).eq(
            "id_documento", str(id_documento)
        ).execute()

        # 2. Construir la URI gs:// correcta
        # Document AI necesita formato: gs://bucket-name/path/to/file
        gcs_uri = f"gs://{settings.GCS_BUCKET_NAME}/{blob_name}"

        # 3. Ejecutar OCR con los argumentos correctos
        resultado_ocr = await process_boleta_from_gcs_uri(
            gcs_uri=gcs_uri, mime_type=mime_type, user_id=str(id_usuario)
        )

        logger.info(f"[OK] OCR completado para: {id_documento}")

        # 4. Actualizar documento con resultados
        # Nota: Adaptamos la respuesta para que coincida con las columnas de tu BD
        datos_actualizar = {
            "estado_ocr": "completado",
            "metadata_ocr": resultado_ocr,  # Guardamos todo el objeto resultado
            "numero_boleta": resultado_ocr.get("parsed_data", {}).get(
                "numero"
            ),  # Si existe
            "fecha_emision": resultado_ocr.get("parsed_data", {}).get(
                "fecha"
            ),  # Si existe
            "error_ocr": None,
        }

        # Limpiamos claves con valor None para no romper el update
        datos_limpios = {k: v for k, v in datos_actualizar.items() if v is not None}

        supabase_admin.get_table("documentos").update(datos_limpios).eq(
            "id_documento", str(id_documento)
        ).execute()

        logger.info(f"[SUCCESS] Documento procesado: {id_documento}")

    except Exception as e:
        logger.error(f"[ERROR] OCR failed for {id_documento}: {e}", exc_info=True)

        # Marcar como error
        try:
            supabase_admin.get_table("documentos").update(
                {"estado_ocr": "error", "error_ocr": str(e)}
            ).eq("id_documento", str(id_documento)).execute()
        except Exception as update_error:
            logger.error(f"[ERROR] Failed to update error status: {update_error}")
