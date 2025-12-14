from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List, Optional
from uuid import UUID
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
from app.core.dependencies import get_active_user_id, get_current_user_id
from app.services.gcs_service import get_gcs_service
from app.services.ocr_service import background_process_ocr
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
    """Sube un documento a GCS y guarda la referencia en Supabase."""
    if not settings.gcs_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Google Cloud Storage no configurado"
        )

    gcs_service = get_gcs_service()

    # 1. Verificar producto
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
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    except Exception as e:
        logger.error(f"[ERROR] Product verification failed: {e}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    # 2. Upload GCS
    try:
        upload_result = await gcs_service.upload_file(
            file, str(user_id), str(producto_id)
        )
    except Exception as e:
        logger.error(f"[ERROR] Upload failed: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error subiendo archivo: {str(e)}"
        )

    # 3. Guardar en BD
    try:
        insert_data = {
            "id_usuario": str(user_id),
            "nombre_archivo": upload_result["filename"],
            "url_gcs": upload_result["public_url"],
            "blob_name": upload_result["blob_name"],
            "content_type": upload_result["content_type"],
            "tipo_documento": tipo_documento,
        }
        response = supabase_admin.get_table("documentos").insert(insert_data).execute()

        if not response.data:
            raise Exception("No data returned from insert")

        documento = response.data[0]

        # Relación
        supabase_admin.get_table("documento_productos").insert(
            {
                "id_documento": str(documento["id_documento"]),
                "id_producto": str(producto_id),
            }
        ).execute()

        # 4. OCR (Solo para boletas y archivos soportados)
        supported_mimes = ["image/jpeg", "image/png", "application/pdf"]
        file_mime = upload_result.get("content_type", "")

        if (
            tipo_documento == "boleta"
            and settings.DOCUMENTAI_PROJECT_ID
            and file_mime in supported_mimes
        ):
            # Marcar estado pendiente
            supabase_admin.get_table("documentos").update(
                {"estado_ocr": "pendiente"}
            ).eq("id_documento", str(documento["id_documento"])).execute()
            documento["estado_ocr"] = "pendiente"

            # Lanzar tarea con todos los datos necesarios
            asyncio.create_task(
                background_process_ocr(
                    documento_id=str(documento["id_documento"]),
                    gcs_uri=upload_result["gcs_uri"],
                    mime_type=file_mime,
                    user_id=str(user_id),
                )
            )

        return DocumentoUploadResponse(
            message="Documento subido exitosamente",
            documento=DocumentoRead(**documento),
        )
    except Exception as e:
        logger.error(f"[ERROR] DB Save failed: {e}")
        try:
            gcs_service.delete_file(upload_result["blob_name"])
        except:
            pass
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error guardando en base de datos"
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
        rel_response = (
            supabase_admin.get_table("documento_productos")
            .select("id_documento")
            .eq("id_producto", str(producto_id))
            .execute()
        )
        doc_ids = [r["id_documento"] for r in rel_response.data or []]

        if not doc_ids:
            return []

        response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .in_("id_documento", doc_ids)
            .execute()
        )

        result = []
        for d in response.data or []:
            try:
                # ✅ CORRECCIÓN AQUÍ: Usamos nombre_archivo (con guion bajo)
                doc_item = DocumentoListItem(
                    id_documento=d.get("id_documento"),
                    nombre_archivo=d.get("nombre_archivo")
                    or d.get("nombrearchivo")
                    or "Archivo",
                    tipo_documento=d.get("tipo_documento"),
                    fecha_creacion=d.get("fecha_creacion"),
                    url_gcs=d.get("url_gcs"),
                    content_type=d.get("content_type"),
                )
                result.append(doc_item)
            except Exception as field_error:
                logger.warning(
                    f"[WARNING] Skipping doc {d.get('id_documento')}: {field_error}"
                )
        return result

    except Exception as e:
        logger.error(f"[ERROR] Failed to read documents: {e}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error obteniendo documentos"
        )


@router.get("/{documento_id}", response_model=DocumentoRead)
async def get_documento(
    documento_id: UUID, user_id: UUID = Depends(get_active_user_id)
):
    try:
        response = (
            supabase_admin.get_table("documentos")
            .select("*")
            .eq("id_documento", str(documento_id))
            .single()
            .execute()
        )
        if not response.data:
            raise HTTPException(404, "No encontrado")
        return DocumentoRead(**response.data)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/{documento_id}/signed-url", response_model=SignedUrlResponse)
async def get_signed_url(
    documento_id: UUID,
    expiration_seconds: int = 3600,
    user_id: UUID = Depends(get_active_user_id),
):
    if not settings.gcs_enabled:
        raise HTTPException(503, "GCS no configurado")

    try:
        doc = (
            supabase_admin.get_table("documentos")
            .select("url_gcs, blob_name")
            .eq("id_documento", str(documento_id))
            .single()
            .execute()
        )
        if not doc.data:
            raise HTTPException(404, "No encontrado")

        blob_name = (
            doc.data.get("blob_name")
            or doc.data.get("url_gcs", "").split(f"{settings.GCS_BUCKET_NAME}/")[-1]
        )
        url = get_gcs_service().get_signed_url(blob_name, expiration_seconds)

        return SignedUrlResponse(
            documento_id=documento_id,
            signed_url=url,
            expires_in_seconds=expiration_seconds,
        )
    except Exception as e:
        raise HTTPException(500, f"Error URL firmada: {str(e)}")


@router.get("/by-type/{tipo_documento}", response_model=List[DocumentoListItem])
async def get_documentos_by_type(
    tipo_documento: str, user_id: UUID = Depends(get_current_user_id)
):
    try:
        # Usar nombre_archivo correcto
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

        return [DocumentoListItem(**d) for d in (response.data or [])]
    except Exception as e:
        logger.error(f"[ERROR] By type error: {e}")
        raise HTTPException(500, "Error obteniendo documentos")


@router.post("/associate-existing", response_model=DocumentoAssociateResponse)
async def associate_existing_documento(
    request: DocumentoAssociateRequest, user_id: UUID = Depends(get_active_user_id)
):
    try:
        # Usar nombre_archivo correcto
        doc = (
            supabase_admin.get_table("documentos")
            .select("id_documento, nombre_archivo, tipo_documento")
            .eq("id_documento", str(request.id_documento))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )
        if not doc.data:
            raise HTTPException(404, "Documento no encontrado")

        prod = (
            supabase_admin.get_table("productos")
            .select("id_producto")
            .eq("id_producto", str(request.id_producto))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )
        if not prod.data:
            raise HTTPException(404, "Producto no encontrado")

        existing = (
            supabase_admin.get_table("documento_productos")
            .select("*")
            .eq("id_documento", str(request.id_documento))
            .eq("id_producto", str(request.id_producto))
            .execute()
        )
        if existing.data:
            raise HTTPException(409, "Ya asociado")

        supabase_admin.get_table("documento_productos").insert(
            {
                "id_documento": str(request.id_documento),
                "id_producto": str(request.id_producto),
            }
        ).execute()

        return DocumentoAssociateResponse(
            id_documento=request.id_documento,
            id_producto=request.id_producto,
            nombre_archivo=doc.data["nombre_archivo"],
            tipo_documento=doc.data["tipo_documento"],
            mensaje="Asociado correctamente",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Association error: {e}")
        raise HTTPException(500, "Error al asociar")


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
