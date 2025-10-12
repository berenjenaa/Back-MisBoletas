"""
CRUD para Categorías usando funciones PostgreSQL.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from typing import List, Optional
from app.schemas.categorias import CategoriaResponse

def create_categoria(
    db: Session,
    producto_id: int,
    user_id: int,
    categoria: str
) -> CategoriaResponse:
    """Crea una nueva categoría usando fn_createcategoria."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_createcategoria(:categoria, :producto_id, :user_id)
            """),
            {
                "categoria": categoria,
                "producto_id": producto_id,
                "user_id": user_id
            }
        )
        
        cat = result.fetchone()
        db.commit()
        
        if not cat:
            raise HTTPException(status_code=400, detail="Error al crear categoría")
            
        return CategoriaResponse(
            id=cat.id,
            productoid=cat.productoid,
            categoria=cat.categoria
        )
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "ya existe" in error_message:
            raise HTTPException(status_code=400, detail="Esta categoría ya existe para este producto")
        if "no encontrado" in error_message or "no autorizado" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=f"Error al crear categoría: {error_message}")

def get_categorias_by_product(
    db: Session,
    producto_id: int,
    user_id: int
) -> List[CategoriaResponse]:
    """Obtiene todas las categorías de un producto usando fn_getcategoriasbyproduct."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_getcategoriasbyproduct(:producto_id, :user_id)
            """),
            {
                "producto_id": producto_id,
                "user_id": user_id
            }
        )
        
        categorias = result.fetchall()
        
        return [
            CategoriaResponse(
                id=cat.id,
                productoid=cat.productoid,
                categoria=cat.categoria
            ) for cat in categorias
        ]
        
    except Exception as e:
        error_message = str(e)
        if "no encontrado" in error_message or "no autorizado" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=f"Error al obtener categorías: {error_message}")

def get_user_categorias(db: Session, user_id: int) -> List[dict]:
    """Obtiene todas las categorías únicas del usuario con su conteo usando fn_getuniqueusercategorias."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_getuniqueusercategorias(:user_id)
            """),
            {"user_id": user_id}
        )
        
        categorias = result.fetchall()
        
        return [
            {
                "categoria": cat.categoria,
                "count": cat.count
            } for cat in categorias
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener categorías del usuario: {str(e)}")

def delete_categoria(
    db: Session,
    categoria_id: int,
    user_id: int
) -> dict:
    """Elimina una categoría usando fn_deletecategoria."""
    try:
        result = db.execute(
            text("""
                SELECT fn_deletecategoria(:categoria_id, :user_id) as message
            """),
            {
                "categoria_id": categoria_id,
                "user_id": user_id
            }
        )
        
        response = result.fetchone()
        db.commit()
        
        if not response:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
            
        return {"message": response.message}
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "no encontrada" in error_message or "no autorizado" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=f"Error al eliminar categoría: {error_message}")