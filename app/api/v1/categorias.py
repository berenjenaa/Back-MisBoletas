"""
Endpoints de API para gestión de categorías.
Permite CRUD completo de categorías personalizadas por usuario.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api import dependencies
from app.crud import categorias as crud_categoria
from app.schemas.categorias import (
    Categoria, 
    CategoriaCreate, 
    CategoriaUpdate,
    CategoriaWithProducts
)
from app.models.user import Usuario
from app.schemas.user import UserRead

router = APIRouter()


@router.get("/categorias/", response_model=List[CategoriaWithProducts])
def read_categorias(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Obtener todas las categorías del usuario con conteo de productos.
    """
    categorias = crud_categoria.get_categorias_with_product_count(
        db, 
        usuario_id=current_user.idUsuario
    )
    return categorias


@router.get("/categorias/{categoria_id}", response_model=Categoria)
def read_categoria(
    categoria_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Obtener una categoría específica por ID.
    """
    categoria = crud_categoria.get_categoria(
        db, 
        categoria_id=categoria_id, 
        usuario_id=current_user.idUsuario
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    return categoria


@router.post("/categorias/", response_model=Categoria, status_code=status.HTTP_201_CREATED)
def create_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Crear una nueva categoría para el usuario actual.
    """
    return crud_categoria.create_categoria(
        db, 
        categoria=categoria, 
        usuario_id=current_user.idUsuario
    )


@router.put("/categorias/{categoria_id}", response_model=Categoria)
def update_categoria(
    categoria_id: int,
    categoria: CategoriaUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Actualizar una categoría existente.
    """
    updated_categoria = crud_categoria.update_categoria(
        db, 
        categoria_id=categoria_id, 
        categoria=categoria,
        usuario_id=current_user.idUsuario
    )
    if not updated_categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    return updated_categoria


@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(
    categoria_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Eliminar una categoría.
    """
    success = crud_categoria.delete_categoria(
        db, 
        categoria_id=categoria_id,
        usuario_id=current_user.idUsuario
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    return None


# Endpoints adicionales para gestionar relación Producto-Categoría

@router.post("/productos/{producto_id}/categorias/{categoria_id}", status_code=status.HTTP_201_CREATED)
def asignar_categoria_a_producto(
    producto_id: int,
    categoria_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Asignar una categoría a un producto.
    """
    # Verificar que la categoría pertenece al usuario
    categoria = crud_categoria.get_categoria(db, categoria_id, current_user.idUsuario)
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    
    # TODO: Verificar que el producto pertenece al usuario
    
    return crud_categoria.asignar_categoria_a_producto(db, producto_id, categoria_id)


@router.delete("/productos/{producto_id}/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_categoria_de_producto(
    producto_id: int,
    categoria_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: UserRead = Depends(dependencies.get_current_user)
):
    """
    Quitar una categoría de un producto.
    """
    success = crud_categoria.quitar_categoria_de_producto(db, producto_id, categoria_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relación producto-categoría no encontrada"
        )
    return None



