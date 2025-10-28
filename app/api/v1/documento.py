from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.schemas.documento import (
    DocumentoRead,
    DocumentoUploadResponse,
    DocumentoDelete,
    DocumentoListItem,
)
from app.crud import documento as crud_documento
from app.db.session import get_db

from app.core.dependencies import get_current_user_id  # <-- MEJORA
from app.services.gcs_service import get_gcs_service
from app.core.config import settings

router = APIRouter()


@router.post(
    "/productos/{producto_id}/documentos",
    response_model=DocumentoUploadResponse,
    status_code=201,
)
async def upload_documento(
    producto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # <-- MEJORA
):
    """Sube un documento a GCS y guarda la referencia en BD."""
    if not settings.gcs_enabled:
        raise HTTPException(503, "GCS no configurado")

    gcs_service = get_gcs_service()
    if not gcs_service:
        raise HTTPException(503, "Servicio GCS no disponible")

    try:
        # 1. Subir a GCS
        upload_result = await gcs_service.upload_file(
            file=file, user_id=user_id, product_id=producto_id
        )

        # 2. Guardar en BD
        documento = crud_documento.create_documento(
            db=db,
            producto_id=producto_id,
            user_id=user_id,
            nombre_archivo=upload_result["filename"],
            url_gcs=upload_result["public_url"],
            blob_name=upload_result["blob_name"],
            content_type=upload_result["content_type"],
            size_bytes=upload_result["size_bytes"],
        )

        return DocumentoUploadResponse(
            message="Documento subido exitosamente",
            documento=DocumentoRead.model_validate(documento),
        )

    except HTTPException:
        raise
    except Exception as e:
        # Rollback GCS upload on database error
        if "upload_result" in locals() and "blob_name" in upload_result:
            try:
                # Asegurarse de que gcs_service está inicializado
                if gcs_service:
                    gcs_service.delete_file(upload_result["blob_name"])
                # Log para registrar que el archivo fue eliminado tras un error
                print(
                    f"INFO: Rollback de GCS completado para el blob: {upload_result['blob_name']}"
                )
            except Exception as gcs_error:
                # Log para registrar si el rollback de GCS falla
                print(
                    f"CRITICAL: Fallo el rollback de GCS para el blob: {upload_result.get('blob_name')}. Error: {gcs_error}"
                )

        # Registrar el error detallado para depuración interna
        print(f"Error interno del servidor al subir documento: {e}")

        # Enviar una respuesta genérica y segura al cliente
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al procesar el archivo. Por favor, inténtalo de nuevo más tarde.",
        )


@router.get(
    "/productos/{producto_id}/documentos", response_model=List[DocumentoListItem]
)
async def get_documentos_by_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # <-- MEJORA
):
    """Obtiene todos los documentos de un producto del usuario."""
    return crud_documento.get_documentos_by_producto(
        db=db, producto_id=producto_id, user_id=user_id
    )


@router.get("/documentos/{documento_id}", response_model=DocumentoRead)
async def get_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # <-- MEJORA
):
    """Obtiene un documento específico por ID."""
    return crud_documento.get_documento_by_id(
        db=db, documento_id=documento_id, user_id=user_id
    )


@router.delete("/documentos/{documento_id}", response_model=DocumentoDelete)
async def delete_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # <-- MEJORA
):
    """Elimina un documento de BD y GCS."""
    if not settings.gcs_enabled:
        raise HTTPException(503, "GCS no configurado")

    gcs_service = get_gcs_service()
    if not gcs_service:
        raise HTTPException(503, "Servicio GCS no disponible")

    try:
        # 1. Eliminar de BD
        delete_result = crud_documento.delete_documento(
            db=db, documento_id=documento_id, user_id=user_id
        )

        # 2. Eliminar de GCS
        try:
            gcs_service.delete_file(delete_result["blob_name"])
        except Exception as e:
            print(f"Advertencia: No se pudo eliminar de GCS: {str(e)}")

        return DocumentoDelete(
            message="Documento eliminado exitosamente", documentoid=documento_id
        )

    except HTTPException:
        raise
    except Exception as e:
        # Registrar el error detallado para depuración interna
        print(f"Error interno del servidor al eliminar documento: {e}")

        # Enviar una respuesta genérica y segura al cliente
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado al eliminar el archivo. Por favor, inténtalo de nuevo más tarde.",
        )


@router.get("/documentos/{documento_id}/signed-url")
async def get_signed_url(
    documento_id: int,
    expiration_seconds: int = 3600,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # <-- MEJORA
):
    """Genera una URL firmada temporal para acceder a un documento privado."""
    if not settings.gcs_enabled:
        raise HTTPException(503, "GCS no configurado")

    gcs_service = get_gcs_service()
    if not gcs_service:
        raise HTTPException(503, "Servicio GCS no disponible")

    # Obtener documento (verifica ownership)
    documento = crud_documento.get_documento_by_id(
        db=db, documento_id=documento_id, user_id=user_id
    )

    # Generar URL firmada
    signed_url = gcs_service.get_signed_url(
        blob_name=documento.BlobName, expiration_seconds=expiration_seconds
    )

    return {
        "documento_id": documento_id,
        "signed_url": signed_url,
        "expires_in_seconds": expiration_seconds,
    }
