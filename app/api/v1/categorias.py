from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging

from app.core.dependencies import get_current_user_id
from app.core.config import supabase
from app.schemas.categorias import (
    CategoriaBase,
    CategoriaCreate,
    CategoriaRead,
    CategoriaWithProducts,
)

router = APIRouter(prefix="/categorias", tags=["categorias"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[CategoriaRead])
async def list_categorias(
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Obtener todas las categorías del usuario.
    """
    try:
        response = (
            supabase.table("categorias")
            .select("*")
            .eq("id_usuario", str(user_id))
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"[ERROR] Failed to list categorias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching categories",
        )


@router.get("/{categoria_id}", response_model=CategoriaRead)
async def get_categoria(
    categoria_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Obtener una categoría específica.
    """
    try:
        response = (
            supabase.table("categorias")
            .select("*")
            .eq("id_categoria", str(categoria_id))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"[ERROR] Categoria not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )


@router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
async def create_categoria(
    categoria: CategoriaCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Crear una nueva categoría.
    """
    try:
        data = {
            "id_usuario": str(user_id),
            "nombre": categoria.nombre,
            "color": categoria.color,
        }
        response = supabase.table("categorias").insert(data).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"[ERROR] Failed to create categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating category",
        )


@router.put("/{categoria_id}", response_model=CategoriaRead)
async def update_categoria(
    categoria_id: UUID,
    categoria: CategoriaCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Actualizar una categoría existente.
    """
    try:
        # Verify ownership
        response = (
            supabase.table("categorias")
            .select("*")
            .eq("id_categoria", str(categoria_id))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada",
            )

        update_data = {
            "nombre": categoria.nombre,
            "color": categoria.color,
        }
        result = (
            supabase.table("categorias")
            .update(update_data)
            .eq("id", str(categoria_id))
            .execute()
        )
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating category",
        )


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_categoria(
    categoria_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Eliminar una categoría.
    """
    try:
        # Verify ownership first
        response = (
            supabase.table("categorias")
            .select("*")
            .eq("id_categoria", str(categoria_id))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada",
            )

        supabase.table("categorias").delete().eq(
            "id_categoria", str(categoria_id)
        ).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting category",
        )
