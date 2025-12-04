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
)
from app.db.supabase import supabase_admin
from app.core.dependencies import get_current_user_id, get_active_user_id
from app.services.gcs_service import get_gcs_service
from app.services.ocr_service import background_process_ocr
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documentos", tags=["documentos"])


# =======================================================================
# === ENDPOINTS DE DOCUMENTOS (SUPABASE + GCS)
# =======================================================================


@router.post(
    "/upload/{producto_id}",
    response_model=DocumentoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir documento a un producto",
)
async def upload_documento(
    producto_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Sube un documento a GCS y guarda la referencia en Supabase.

    Flujo:
    1. Verifica que el producto pertenece al usuario
    2. Sube el archivo a GCS
    3. Guarda metadatos en Supabase
    4. Procesa OCR si está configurado
    """
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
        try:
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
        except Exception as e:
            logger.error(f"[ERROR] Product verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        # 2. Subir archivo a GCS
        upload_result = await gcs_service.upload_file(
            file=file, user_id=str(user_id), product_id=str(producto_id)
        )

        # 3. Guardar documento en Supabase
        insert_data = {
            "id_usuario": str(user_id),
            "nombre_archivo": upload_result["filename"],
            "url_gcs": upload_result.get("public_url", ""),
            "blob_name": upload_result.get("blob_name", ""),
            "content_type": upload_result.get("content_type", ""),
        }

        response = supabase_admin.get_table("documentos").insert(insert_data).execute()

        if not response.data:
            # Rollback: eliminar de GCS si falla inserción en Supabase
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
        try:
            relacion_data = {
                "id_documento": str(documento["id_documento"]),
                "id_producto": str(producto_id),
            }
            supabase_admin.get_table("documento_productos").insert(relacion_data).execute()
        except Exception as e:
            logger.warning(f"[WARNING] Failed to create documento_productos relation: {e}")

        # 4. Procesar OCR en BACKGROUND (no bloquea la respuesta HTTP)
        gcs_uri = upload_result.get("gcs_uri")  # gs://bucket/path

        if (
            settings.DOCUMENTAI_PROJECT_ID
            and settings.DOCUMENTAI_PROCESSOR_ID
            and gcs_uri
            and file.content_type
            in ["image/jpeg", "image/png", "image/pdf", "application/pdf"]
        ):
            # Guardar estado_ocr como 'pendiente' antes de lanzar background task
            supabase_admin.get_table("documentos").update(
                {"estado_ocr": "pendiente"}
            ).eq("id_documento", str(documento["id_documento"])).execute()

            # Actualizar documento local con estado pendiente
            documento["estado_ocr"] = "pendiente"
            documento["error_ocr"] = None

            # Lanzar OCR en background (no espera la respuesta)
            logger.info(
                f"[INFO] Launching background OCR for document {documento['id_documento']}"
            )
            asyncio.create_task(
                background_process_ocr(
                    documento_id=str(documento["id_documento"]),
                    gcs_uri=gcs_uri,
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
        # Obtener IDs de documentos a través de documento_productos
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
        response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .in_("id_documento", documento_ids)
            .execute()
        )

        documentos = response.data or []
        return [DocumentoListItem(**d) for d in documentos]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to read documents: {e}")
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
    """Obtiene un documento específico por ID."""
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

        documento = response.data[0]
        return DocumentoRead(**documento)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to read document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo documento. Por favor intenta más tarde.",
        )


@router.get(
    "/{documento_id}/signed-url",
    response_model=SignedUrlResponse,
    summary="Generar URL firmada para acceder al documento",
)
async def get_signed_url(
    documento_id: UUID,
    expiration_seconds: int = 3600,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Genera una URL firmada temporal para acceder a un documento privado en GCS.

    Args:
        documento_id: ID del documento
        expiration_seconds: Segundos de validez de la URL (default: 1 hora)
    """
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
        # 1. Obtener documento (verifica ownership)
        doc_response = (
            supabase_admin.get_table("documentos")
            .select("url_gcs, blob_name")
            .eq("id_documento", str(documento_id))
            .single()
            .execute()
        )

        documento = doc_response.data
        if not documento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
            )

        # 2. Usar blob_name directamente si está disponible, sino extraer de URL
        blob_name = documento.get("blob_name")
        if not blob_name:
            url_gcs = documento.get("url_gcs", "")
            if not url_gcs:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="URL de GCS no disponible",
                )
            blob_name = url_gcs.split(f"{settings.GCS_BUCKET_NAME}/")[-1]

        # 3. Generar URL firmada
        signed_url = gcs_service.get_signed_url(
            blob_name=blob_name, expiration_seconds=expiration_seconds
        )

        return SignedUrlResponse(
            documento_id=documento_id,
            signed_url=signed_url,
            expires_in_seconds=expiration_seconds,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to generate signed URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando URL. Por favor intenta más tarde.",
        )


@router.delete(
    "/{documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un documento",
)
async def delete_documento(
    documento_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """Elimina un documento de Supabase y GCS."""
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
        import asyncio
        from datetime import datetime, timezone
        from app.services.gcs_cleanup_service import (
            delete_gcs_file,
            register_deletion_history,
        )

        # 1. Obtener documento
        doc_response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .eq("id_documento", str(documento_id))
            .single()
            .execute()
        )

        documento = doc_response.data
        if not documento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
            )

        # 2. Soft delete en BD
        supabase_admin.get_table("documentos").update(
            {"fecha_eliminacion": datetime.now(timezone.utc).isoformat()}
        ).eq("id_documento", str(documento_id)).execute()

        # 3. Registrar documento_id para usar después
        documento_id_to_delete = documento.get("id_documento") or documento_id

        logger.info(f"[OK] Document soft deleted: {documento_id}")

        # 3. Registrar en historial
        await register_deletion_history(
            tabla="documentos",
            id_registro=documento_id,
            datos_antiguos=documento,
            id_usuario=user_id,
        )

        # 4. Borrar archivo de GCS en background (sin bloquear respuesta)
        blob_name = documento.get("blob_name")
        if blob_name:
            asyncio.create_task(delete_gcs_file(blob_name))

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando documento. Por favor intenta más tarde.",
        )
