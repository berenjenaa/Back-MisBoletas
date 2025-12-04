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

    Supabase envía:
    {
        "type": "INSERT",
        "record": { ... todo el documento ... },
        "schema": "public",
        "table": "documentos",
        "created_at": "2025-12-03T15:30:00Z"
    }
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
        gcs_uri = documento.get("url_gcs")

        if not id_documento or not blob_name:
            logger.error(f"[ERROR] Webhook incompleto: falta id_documento o blob_name")
            return {"received": True, "error": "Missing fields"}

        logger.info(f"[OK] Webhook recibido para documento: {id_documento}")

        # 3. Extraer id_usuario
        id_usuario = documento.get("id_usuario")

        # 4. Iniciar OCR en background (sin bloquear respuesta)
        asyncio.create_task(
            procesar_documento_ocr(id_documento, blob_name, gcs_uri, id_usuario)
        )

        # 4. Responder inmediatamente
        return {
            "received": True,
            "id_documento": str(id_documento),
            "status": "procesando en background",
        }

    except Exception as e:
        logger.error(f"[ERROR] Webhook error: {e}", exc_info=True)
        # Retornar 200 igual para que Supabase no lo marque como error
        return {"received": True, "error": str(e)}


async def procesar_documento_ocr(
    id_documento: str, blob_name: str, gcs_uri: str, id_usuario: str = None
):
    """
    Procesa OCR del documento en background.
    Se ejecuta sin bloquear la respuesta HTTP.
    """
    try:
        logger.info(f"[INFO] Iniciando OCR para: {id_documento}")

        # 1. Marcar como procesando
        supabase_admin.get_table("documentos").update({"estado_ocr": "procesando"}).eq(
            "id_documento", str(id_documento)
        ).execute()

        logger.info(f"[OK] Marcado como procesando: {id_documento}")

        # 2. Ejecutar OCR (aquí es donde tarda 30-120s)
        resultado_ocr = await process_boleta_from_gcs_uri(gcs_uri)

        logger.info(f"[OK] OCR completado para: {id_documento}")

        # 3. Actualizar documento con resultados
        supabase_admin.get_table("documentos").update(
            {
                "estado_ocr": "completado",
                "metadata_ocr": resultado_ocr.get("full_text"),
                "numero_boleta": resultado_ocr.get("numero_boleta"),
                "fecha_emision": resultado_ocr.get("fecha_emision"),
                "error_ocr": None,
                "id_usuario": id_usuario,
            }
        ).eq("id_documento", str(id_documento)).execute()

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
