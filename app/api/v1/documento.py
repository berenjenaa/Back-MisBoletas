from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List, Optional
from uuid import UUID
import json
import logging
import asyncio

from app.schemas.documento import (
    DocumentoRead,
    DocumentoUploadResponse,
    DocumentoListItem,
    SignedUrlResponse,
    DocumentoAssociateRequest,
    DocumentoAssociateResponse,
)
from app.db.supabase import supabase_admin
from app.core.dependencies import get_current_user_id, get_active_user_id
from app.services.gcs_service import get_gcs_service
from app.services.ocr_service import (
    background_process_ocr,
    process_boleta_from_gcs_uri,
    parse_receipt_data,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documentos")


@router.post(
    "/upload/{producto_id}",
    response_model=DocumentoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir documento a un producto",
)
async def upload_documento(
    producto_id: UUID,
    file: UploadFile = File(...),
    tipo_documento: str = "boleta",
    user_id: UUID = Depends(get_active_user_id),
):
    if not settings.gcs_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Cloud Storage no configurado",
        )

    gcs_service = get_gcs_service()
    if not gcs_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio GCS no disponible",
        )

    try:
        # 1. Verificar que el producto pertenece al usuario
        prod_response = (
            supabase_admin.get_table("productos")
            .select("id_producto")
            .eq("id_producto", str(producto_id))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        if not prod_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado",
            )

        # 2. Subir archivo a GCS
        upload_result = await gcs_service.upload_file(
            file=file, user_id=str(user_id), product_id=str(producto_id)
        )

        # 3. Guardar documento en Supabase
        insert_data = {
            "id_usuario": str(user_id),
            "nombre_archivo": upload_result["filename"],  # ✅ Correcto (con guion)
            "url_gcs": upload_result.get("public_url", ""),
            "blob_name": upload_result.get("blob_name", ""),
            "content_type": upload_result.get("content_type", ""),
            "tipo_documento": tipo_documento,
        }

        response = supabase_admin.get_table("documentos").insert(insert_data).execute()

        if not response.data:
            try:
                gcs_service.delete_file(upload_result["blob_name"])
            except Exception as e:
                logger.warning(f"[WARNING] GCS rollback failed: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando documento en BD",
            )

        documento = response.data[0]

        # 3b. Crear relación en documento_productos
        supabase_admin.get_table("documento_productos").insert(
            {
                "id_documento": str(documento["id_documento"]),
                "id_producto": str(producto_id),
            }
        ).execute()

        # 4. Procesar OCR en BACKGROUND (solo para boletas)
        # Importante: Pasar mime_type correcto
        supported_mimes = ["image/jpeg", "image/png", "application/pdf"]
        file_mime = upload_result.get("content_type", "")

        if (
            tipo_documento == "boleta"
            and settings.DOCUMENTAI_PROJECT_ID
            and file_mime in supported_mimes
        ):
            supabase_admin.get_table("documentos").update(
                {"estado_ocr": "pendiente"}
            ).eq("id_documento", str(documento["id_documento"])).execute()

            documento["estado_ocr"] = "pendiente"

            # Lanzar tarea con MIME type
            asyncio.create_task(
                background_process_ocr(
                    documento_id=str(documento["id_documento"]),
                    gcs_uri=upload_result["gcs_uri"],
                    mime_type=file_mime,
                    user_id=str(user_id),
                )
            )

        return DocumentoUploadResponse(
            message="Documento subido exitosamente. Escaneo OCR en progreso.",
            documento=DocumentoRead(**documento),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando documento. Por favor intenta más tarde.",
        )


@router.get(
    "/by-product/{producto_id}",
    response_model=List[DocumentoListItem],
    summary="Listar documentos de un producto",
)
async def get_documentos_by_producto(
    producto_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """Obtiene todos los documentos de un producto del usuario."""
    try:
        # Obtener IDs de documentos
        relaciones_response = (
            supabase_admin.get_table("documento_productos")
            .select("id_documento")
            .eq("id_producto", str(producto_id))
            .execute()
        )

        documento_ids = [rel["id_documento"] for rel in relaciones_response.data or []]

        if not documento_ids:
            return []

        # Obtener documentos
        # ✅ Supabase devuelve 'nombre_archivo', y ahora el Schema también espera 'nombre_archivo'.
        # El mapeo es automático.
        response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .in_("id_documento", documento_ids)
            .execute()
        )

        documentos = response.data or []

        return [DocumentoListItem(**d) for d in documentos]

    except Exception as e:
        logger.error(f"[ERROR] Failed to read documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo documentos. Por favor intenta más tarde.",
        )


@router.get(
    "/{documento_id}",
    response_model=DocumentoRead,
    summary="Obtener detalles de un documento",
)
async def get_documento(
    documento_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    try:
        response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .eq("id_documento", str(documento_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
            )

        return DocumentoRead(**response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to read document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo documento.",
        )


@router.get(
    "/{documento_id}/signed-url",
    response_model=SignedUrlResponse,
)
async def get_signed_url(
    documento_id: UUID,
    expiration_seconds: int = 3600,
    user_id: UUID = Depends(get_active_user_id),
):
    if not settings.gcs_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "GCS no configurado")

    try:
        doc_response = (
            supabase_admin.get_table("documentos")
            .select("url_gcs, blob_name")
            .eq("id_documento", str(documento_id))
            .single()
            .execute()
        )

        if not doc_response.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")

        documento = doc_response.data
        blob_name = (
            documento.get("blob_name")
            or documento.get("url_gcs", "").split(f"{settings.GCS_BUCKET_NAME}/")[-1]
        )

        url = get_gcs_service().get_signed_url(blob_name, expiration_seconds)

        return SignedUrlResponse(
            documento_id=documento_id,
            signed_url=url,
            expires_in_seconds=expiration_seconds,
        )
    except Exception as e:
        raise HTTPException(500, f"Error generando URL: {str(e)}")


@router.get(
    "/by-type/{tipo_documento}",
    response_model=List[DocumentoListItem],
)
async def get_documentos_by_type(
    tipo_documento: str,
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        # 🔧 CORREGIDO: Select explícito con nombre_archivo
        response = (
            supabase_admin.get_table("documentos")
            .select(
                "id_documento, nombre_archivo, tipo_documento, fecha_creacion, url_gcs, content_type"
            )
            .eq("id_usuario", str(user_id))
            .eq("tipo_documento", tipo_documento)
            .is_("fecha_eliminacion", "null")
            .order("fecha_creacion", desc=True)
            .execute()
        )
        return [DocumentoListItem(**doc) for doc in (response.data or [])]
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch documents by type: {e}")
        raise HTTPException(500, "Error al obtener documentos")


@router.post(
    "/associate-existing",
    response_model=DocumentoAssociateResponse,
)
async def associate_existing_documento(
    request: DocumentoAssociateRequest,
    user_id: UUID = Depends(get_active_user_id),
):
    try:
        # 🔧 CORREGIDO: Select con nombre_archivo
        doc_response = (
            supabase_admin.get_table("documentos")
            .select("id_documento, nombre_archivo, tipo_documento")
            .eq("id_documento", str(request.id_documento))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        if not doc_response.data:
            raise HTTPException(404, "Documento no encontrado")

        documento = doc_response.data

        # Verificar producto y duplicados... (lógica estándar)
        existing = (
            supabase_admin.get_table("documento_productos")
            .select("id_documento")
            .eq("id_documento", str(request.id_documento))
            .eq("id_producto", str(request.id_producto))
            .execute()
        )
        if existing.data:
            raise HTTPException(409, "Documento ya asociado")

        supabase_admin.get_table("documento_productos").insert(
            {
                "id_documento": str(request.id_documento),
                "id_producto": str(request.id_producto),
            }
        ).execute()

        return DocumentoAssociateResponse(
            id_documento=request.id_documento,
            id_producto=request.id_producto,
            nombre_archivo=documento["nombre_archivo"],  # ✅
            tipo_documento=documento["tipo_documento"],
            mensaje="Documento asociado exitosamente",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Association error: {e}")
        raise HTTPException(500, "Error al asociar documento")


@router.delete("/{documento_id}", status_code=204)
async def delete_documento(
    documento_id: UUID, user_id: UUID = Depends(get_active_user_id)
):
    if not settings.gcs_enabled:
        raise HTTPException(503, "GCS no configurado")

    try:
        from datetime import datetime, timezone
        from app.services.gcs_cleanup_service import (
            delete_gcs_file,
            register_deletion_history,
        )

        doc = (
            supabase_admin.get_table("documentos")
            .select("*")
            .eq("id_documento", str(documento_id))
            .single()
            .execute()
        )
        if not doc.data:
            raise HTTPException(404, "No encontrado")

        supabase_admin.get_table("documentos").update(
            {"fecha_eliminacion": datetime.now(timezone.utc).isoformat()}
        ).eq("id_documento", str(documento_id)).execute()

        await register_deletion_history("documentos", documento_id, doc.data, user_id)

        if doc.data.get("blob_name"):
            asyncio.create_task(delete_gcs_file(doc.data["blob_name"]))

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Delete error: {e}")
        raise HTTPException(500, "Error al eliminar")


@router.post(
    "/{documento_id}/process-ocr",
    summary="Procesar OCR síncrono de un documento",
)
async def process_document_ocr_sync(
    documento_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """Procesa OCR de forma síncrona para un documento ya subido."""
    try:
        # Obtener documento
        doc_response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .eq("id_documento", str(documento_id))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        if not doc_response.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")

        documento = doc_response.data
        gcs_uri = documento.get("url_gcs")
        mime_type = documento.get("content_type", "application/pdf")
        estado_ocr = documento.get("estado_ocr")
        metadata_ocr = documento.get("metadata_ocr")

        if not gcs_uri:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Documento sin URL en GCS")

        # ✅ CACHING: Si ya procesó, devuelve cached (AHORRO DE $$)
        if estado_ocr == "completado" and metadata_ocr:
            if settings.LOG_LEVEL == "DEBUG":
                logger.debug(f"[OCR CACHE HIT] documento {documento_id}")
            return _map_ocr_to_product_fields(metadata_ocr)

        # Procesar OCR de forma síncrona
        if settings.LOG_LEVEL == "DEBUG":
            logger.debug(f"[OCR SYNC] Procesando documento {documento_id}")
        ocr_result = await process_boleta_from_gcs_uri(gcs_uri, mime_type, str(user_id))

        # Actualizar documento con metadatos
        supabase_admin.get_table("documentos").update(
            {
                "estado_ocr": "completado",
                "metadata_ocr": ocr_result,
            }
        ).eq("id_documento", str(documento_id)).execute()

        # Retornar datos mapeados al frontend
        return _map_ocr_to_product_fields(ocr_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] OCR sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando documento",
        )


def _map_ocr_to_product_fields(ocr_result: dict) -> dict:
    """Mapea resultados OCR al formato esperado por el frontend para completar formulario."""
    if not ocr_result:
        return {}
    
    parsed = ocr_result.get("parsed_data", {})
    
    # Convertir fecha de DD/MM/AAAA o AAAA-MM-DD a ISO format
    fecha_ocr = parsed.get("fecha")
    fecha_iso = None
    if fecha_ocr:
        try:
            # Intentar parsear formatos comunes
            import re
            # Formato DD/MM/AAAA o DD-MM-AAAA
            match_dmyy = re.match(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", fecha_ocr)
            if match_dmyy:
                day, month, year = match_dmyy.groups()
                fecha_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                # Formato AAAA-MM-DD ya está correcto
                fecha_iso = fecha_ocr
        except:
            pass
    
    return {
        "nombre": parsed.get("comercio") or parsed.get("marca"),
        "marca": parsed.get("marca"),
        "modelo": parsed.get("modelo"),
        "tienda": parsed.get("comercio"),
        "precio": parsed.get("total"),
        "fecha_compra": fecha_iso,
        "duracion_garantia_meses": parsed.get("garantia"),
    }
