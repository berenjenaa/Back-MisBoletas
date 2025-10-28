"""
CRUD simplificado para Documentos usando SQLAlchemy.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
from app.models.documento import Documento
from app.models.producto import Producto


# ===== CREAR DOCUMENTO =====
def create_documento(
    db: Session,
    producto_id: int,
    user_id: int,
    nombre_archivo: str,
    url_gcs: str,
    blob_name: str,
    content_type: Optional[str],
    size_bytes: Optional[int],
) -> Documento:
    """Crea un nuevo documento."""
    # Verificar ownership del producto
    producto = (
        db.query(Producto)
        .filter(Producto.ProductoID == producto_id, Producto.UsuarioID == user_id)
        .first()
    )

    if not producto:
        raise HTTPException(404, "Producto no encontrado o sin permisos")

    # Crear documento
    documento = Documento(
        ProductoID=producto_id,
        NombreArchivo=nombre_archivo,
        URL_GCS=url_gcs,
        BlobName=blob_name,
        ContentType=content_type,
        SizeBytes=size_bytes,
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)
    return documento


# ===== OBTENER DOCUMENTOS DE UN PRODUCTO =====
def get_documentos_by_producto(
    db: Session, producto_id: int, user_id: int
) -> List[Documento]:
    """Obtiene todos los documentos de un producto."""
    # Verificar ownership
    producto = (
        db.query(Producto)
        .filter(Producto.ProductoID == producto_id, Producto.UsuarioID == user_id)
        .first()
    )

    if not producto:
        raise HTTPException(404, "Producto no encontrado o sin permisos")

    return (
        db.query(Documento)
        .filter(Documento.ProductoID == producto_id)
        .order_by(Documento.FechaSubida.desc())
        .all()
    )


# ===== OBTENER UN DOCUMENTO POR ID =====
def get_documento_by_id(db: Session, documento_id: int, user_id: int) -> Documento:
    """Obtiene un documento específico por ID."""
    documento = (
        db.query(Documento)
        .join(Producto)
        .filter(Documento.DocumentoID == documento_id, Producto.UsuarioID == user_id)
        .first()
    )

    if not documento:
        raise HTTPException(404, "Documento no encontrado o sin permisos")

    return documento


# ===== ELIMINAR DOCUMENTO =====
def delete_documento(db: Session, documento_id: int, user_id: int) -> dict:
    """Elimina un documento."""
    documento = (
        db.query(Documento)
        .join(Producto)
        .filter(Documento.DocumentoID == documento_id, Producto.UsuarioID == user_id)
        .first()
    )

    if not documento:
        raise HTTPException(404, "Documento no encontrado o sin permisos")

    blob_name = documento.BlobName
    db.delete(documento)
    db.commit()

    return {"message": "Documento eliminado exitosamente", "blob_name": blob_name}
