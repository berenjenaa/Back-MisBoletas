"""
Endpoints API simplificados para Documentos.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.schemas.documento import (
    DocumentoRead,
    DocumentoUploadResponse,
    DocumentoDelete,
    DocumentoListItem
)
from app.schemas.user import UserRead
from app.crud import documento as crud_documento
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.gcs_service import get_gcs_service
from app.core.config import settings

router = APIRouter()

# ===== UPLOAD DE DOCUMENTO =====
@router.post("/productos/{producto_id}/documentos", response_model=DocumentoUploadResponse, status_code=201)
async def upload_documento(
    producto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
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
            file=file,
            user_id=current_user.idUsuario,
            product_id=producto_id
        )
        
        # 2. Guardar en BD
        documento = crud_documento.create_documento(
            db=db,
            producto_id=producto_id,
            user_id=current_user.idUsuario,
            nombre_archivo=upload_result["filename"],
            url_gcs=upload_result["public_url"],
            blob_name=upload_result["blob_name"],
            content_type=upload_result["content_type"],
            size_bytes=upload_result["size_bytes"]
        )
        
        return DocumentoUploadResponse(
            message="Documento subido exitosamente",
            documento=DocumentoRead.model_validate(documento)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        # Limpiar GCS si falla BD
        if 'upload_result' in locals():
            try:
                gcs_service.delete_file(upload_result["blob_name"])
            except:
                pass
        raise HTTPException(500, f"Error: {str(e)}")

# ===== OBTENER DOCUMENTOS DE UN PRODUCTO =====
@router.get("/productos/{producto_id}/documentos", response_model=List[DocumentoListItem])
async def get_documentos_by_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Obtiene todos los documentos de un producto del usuario."""
    return crud_documento.get_documentos_by_producto(
        db=db,
        producto_id=producto_id,
        user_id=current_user.idUsuario
    )

# ===== OBTENER UN DOCUMENTO ESPECÍFICO =====
@router.get("/documentos/{documento_id}", response_model=DocumentoRead)
async def get_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Obtiene un documento específico por ID."""
    return crud_documento.get_documento_by_id(
        db=db,
        documento_id=documento_id,
        user_id=current_user.idUsuario
    )

# ===== ELIMINAR DOCUMENTO =====
@router.delete("/documentos/{documento_id}", response_model=DocumentoDelete)
async def delete_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
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
            db=db,
            documento_id=documento_id,
            user_id=current_user.idUsuario
        )
        
        # 2. Eliminar de GCS
        try:
            gcs_service.delete_file(delete_result["blob_name"])
        except Exception as e:
            print(f"Advertencia: No se pudo eliminar de GCS: {str(e)}")
        
        return DocumentoDelete(
            message="Documento eliminado exitosamente",
            documentoid=documento_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

# ===== OBTENER URL FIRMADA (OPCIONAL) =====
@router.get("/documentos/{documento_id}/signed-url")
async def get_signed_url(
    documento_id: int,
    expiration_seconds: int = 3600,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Genera una URL firmada temporal para acceder a un documento privado."""
    if not settings.gcs_enabled:
        raise HTTPException(503, "GCS no configurado")
    
    gcs_service = get_gcs_service()
    if not gcs_service:
        raise HTTPException(503, "Servicio GCS no disponible")
    
    # Obtener documento (verifica ownership)
    documento = crud_documento.get_documento_by_id(
        db=db,
        documento_id=documento_id,
        user_id=current_user.idUsuario
    )
    
    # Generar URL firmada
    signed_url = gcs_service.get_signed_url(
        blob_name=documento.BlobName,
        expiration_seconds=expiration_seconds
    )
    
    return {
        "documento_id": documento_id,
        "signed_url": signed_url,
        "expires_in_seconds": expiration_seconds
    }
