from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List, Optional
from uuid import UUID
import json
import logging

from app.schemas.documento import (
    DocumentoRead,
    DocumentoUploadResponse,
    DocumentoListItem,
    SignedUrlResponse,
)
from app.db.supabase import supabase_admin
from app.core.dependencies import get_current_user_id, get_active_user_id
from app.services.gcs_service import get_gcs_service
from app.services.ocr_service import process_boleta_from_gcs_uri
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
                .select("id")
                .eq("id", str(producto_id))
                .eq("user_id", str(user_id))
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
            "producto_id": str(producto_id),
            "nombre_archivo": upload_result["filename"],
            "url_gcs": upload_result.get("public_url", ""),
            "blob_name": upload_result.get("blob_name", ""),
            "content_type": upload_result.get("content_type", ""),
            "size_bytes": upload_result.get("size_bytes", 0),
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

        # 4. Procesar OCR si el archivo es imagen y Document AI está configurado
        ocr_metadata = None
        gcs_uri = upload_result.get("gcs_uri")  # gs://bucket/path

        if (
            settings.DOCUMENTAI_PROJECT_ID
            and settings.DOCUMENTAI_PROCESSOR_ID
            and gcs_uri
            and file.content_type
            in ["image/jpeg", "image/png", "image/pdf", "application/pdf"]
        ):
            try:
                logger.info(f"[INFO] Starting OCR for document {documento['id']}")
                ocr_result = await process_boleta_from_gcs_uri(
                    gcs_uri=gcs_uri, user_id=str(user_id)
                )

                # Guardar resultado OCR en Supabase
                supabase_admin.get_table("documentos").update(
                    {"metadata_ocr": json.dumps(ocr_result)}
                ).eq("id", str(documento["id"])).execute()

                documento["metadata_ocr"] = ocr_result
                logger.info(f"[OK] OCR completed for document {documento['id']}")

            except Exception as ocr_error:
                # No fallar si OCR falla - es opcional
                logger.warning(
                    f"[WARNING] OCR failed for document {documento['id']}: {ocr_error}. "
                    "Continuing without OCR."
                )

        return DocumentoUploadResponse(
            message="Documento subido exitosamente",
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
        # Cambio: Usar RPC en lugar de verificación + select
        response = supabase.rpc(
            "api_obtener_documentos_producto",
            {"p_id_producto": str(producto_id), "p_id_usuario": str(user_id)},
        ).execute()

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
        # Cambio: Usar RPC en lugar de select directo
        response = supabase.rpc(
            "api_obtener_documento",
            {"p_id_documento": str(documento_id), "p_id_usuario": str(user_id)},
        ).execute()

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
            .eq("id", str(documento_id))
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
        # 1. Obtener documento de Supabase
        doc_response = (
            supabase_admin.get_table("documentos")
            .select("blob_name, url_gcs")
            .eq("id", str(documento_id))
            .single()
            .execute()
        )

        documento = doc_response.data
        if not documento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
            )

        # 2. Extraer blob_name y eliminar de GCS
        blob_name = documento.get("blob_name")
        if not blob_name:
            url_gcs = documento.get("url_gcs", "")
            if url_gcs:
                blob_name = url_gcs.split(f"{settings.GCS_BUCKET_NAME}/")[-1]

        if blob_name:
            try:
                gcs_service.delete_file(blob_name)
            except Exception as e:
                logger.warning(f"[WARNING] GCS deletion failed: {e}")

        # 3. Eliminar de Supabase
        supabase_admin.get_table("documentos").delete().eq("id", str(documento_id)).execute()

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando documento. Por favor intenta más tarde.",
        )
