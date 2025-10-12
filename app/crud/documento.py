"""
CRUD para Documentos usando funciones PostgreSQL.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from typing import List, Optional
from app.schemas.documento import DocumentoCreate, DocumentoResponse

def create_documento(
    db: Session,
    producto_id: int,
    user_id: int,
    nombre_archivo: str,
    ruta_archivo: str
) -> DocumentoResponse:
    """Crea un nuevo documento usando fn_createdocument."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_createdocument(
                    :producto_id, :nombre_archivo, :ruta_archivo, :user_id
                )
            """),
            {
                "producto_id": producto_id,
                "nombre_archivo": nombre_archivo,
                "ruta_archivo": ruta_archivo,
                "user_id": user_id
            }
        )
        
        documento = result.fetchone()
        db.commit()
        
        if not documento:
            raise HTTPException(status_code=400, detail="Error al crear documento")
            
        return DocumentoResponse(
            documentoid=documento.documentoid,
            productoid=documento.productoid,
            nombrearchivo=documento.nombrearchivo,
            rutaarchivo=documento.rutaarchivo
        )
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "no encontrado" in error_message or "no autorizado" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=f"Error al crear documento: {error_message}")

def get_documentos_by_product(
    db: Session,
    producto_id: int,
    user_id: int
) -> List[DocumentoResponse]:
    """Obtiene todos los documentos de un producto usando fn_getdocumentsbyproduct."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_getdocumentsbyproduct(:producto_id, :user_id)
            """),
            {
                "producto_id": producto_id,
                "user_id": user_id
            }
        )
        
        documentos = result.fetchall()
        
        return [
            DocumentoResponse(
                documentoid=doc.documentoid,
                productoid=doc.productoid,
                nombrearchivo=doc.nombrearchivo,
                rutaarchivo=doc.rutaarchivo
            ) for doc in documentos
        ]
        
    except Exception as e:
        error_message = str(e)
        if "no encontrado" in error_message or "no autorizado" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=f"Error al obtener documentos: {error_message}")

def delete_documento(
    db: Session,
    documento_id: int,
    user_id: int
) -> dict:
    """Elimina un documento usando fn_deletedocument."""
    try:
        result = db.execute(
            text("""
                SELECT fn_deletedocument(:documento_id, :user_id) as message
            """),
            {
                "documento_id": documento_id,
                "user_id": user_id
            }
        )
        
        response = result.fetchone()
        db.commit()
        
        if not response:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
            
        return {"message": response.message}
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "no encontrado" in error_message or "no autorizado" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=f"Error al eliminar documento: {error_message}")