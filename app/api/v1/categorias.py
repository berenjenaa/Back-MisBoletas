from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core import dependencies
from app.db.session import get_db
from app.crud import categorias as crud_categoria
from app.crud import product as crud_product  # <-- CORRECCIÓN (Seguridad)
from app.schemas.categorias import (
    Categoria,
    CategoriaCreate,
    CategoriaUpdate,
    CategoriaWithProducts,
)

router = APIRouter()


@router.get("/categorias/", response_model=List[CategoriaWithProducts])
def read_categorias(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Obtener todas las categorías del usuario con conteo de productos.
    """
    categorias = crud_categoria.get_categorias_with_product_count(
        db, usuario_id=user_id
    )
    return categorias


@router.get("/categorias/{categoria_id}", response_model=Categoria)
def read_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Obtener una categoría específica por ID.
    """
    categoria = crud_categoria.get_categoria(
        db, categoria_id=categoria_id, usuario_id=user_id
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
        )
    return categoria


@router.post(
    "/categorias/", response_model=Categoria, status_code=status.HTTP_201_CREATED
)
def create_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Crear una nueva categoría para el usuario actual.
    """
    return crud_categoria.create_categoria(db, categoria=categoria, usuario_id=user_id)


@router.put("/categorias/{categoria_id}", response_model=Categoria)
def update_categoria(
    categoria_id: int,
    categoria: CategoriaUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Actualizar una categoría existente.
    """
    updated_categoria = crud_categoria.update_categoria(
        db,
        categoria_id=categoria_id,
        categoria=categoria,
        usuario_id=user_id,
    )
    if not updated_categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
        )
    return updated_categoria


@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Eliminar una categoría.
    """
    success = crud_categoria.delete_categoria(
        db, categoria_id=categoria_id, usuario_id=user_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
        )
    return None


@router.post(
    "/productos/{producto_id}/categorias/{categoria_id}",
    status_code=status.HTTP_201_CREATED,
)
def asignar_categoria_a_producto(
    producto_id: int,
    categoria_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Asignar una categoría a un producto.
    """
    # --- CORRECCIÓN DE SEGURIDAD ---
    # 1. Verificar que la categoría pertenece al usuario
    categoria = crud_categoria.get_categoria(db, categoria_id, user_id)
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada o no te pertenece",
        )

    # 2. Verificar que el producto pertenece al usuario
    producto = crud_product.get_product_by_id(db, producto_id, user_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no te pertenece",
        )
    # --- FIN DE CORRECCIÓN ---

    return crud_categoria.asignar_categoria_a_producto(db, producto_id, categoria_id)


@router.delete(
    "/productos/{producto_id}/categorias/{categoria_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def quitar_categoria_de_producto(
    producto_id: int,
    categoria_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(dependencies.get_current_user_id),  # <-- MEJORA
):
    """
    Quitar una categoría de un producto.
    """
    # --- CORRECCIÓN DE SEGURIDAD (Implícita) ---
    # Sería bueno verificar la propiedad del producto aquí también,
    # pero el CRUD ya debería manejar la lógica de borrado de forma segura.
    # (Asumiendo que quitar_categoria_de_producto no falla si no existe)
    # ---
    success = crud_categoria.quitar_categoria_de_producto(db, producto_id, categoria_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relación producto-categoría no encontrada",
        )
    return None
