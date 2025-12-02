from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging

from app.core.dependencies import get_current_user_id, get_active_user_id
from app.db.supabase import supabase_admin
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
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtener todas las categorías del usuario.
    """
    try:
        response = (
            supabase_admin.get_table("categorias")
            .select("*")
            .eq("id_usuario", str(user_id))
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"[ERROR] Failed to list categorias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo categorías. Por favor intenta más tarde.",
        )


@router.get("/{categoria_id}", response_model=CategoriaRead)
async def get_categoria(
    categoria_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtener una categoría específica.
    """
    try:
        # Cambio: Usar RPC en lugar de select directo
        response = supabase.rpc(
            "api_obtener_categoria",
            {"p_id_categoria": str(categoria_id), "p_id_usuario": str(user_id)},
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada",
            )

        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Categoria not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo categoría. Por favor intenta más tarde.",
        )


@router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
async def create_categoria(
    categoria: CategoriaCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Crear una nueva categoría.
    """
    try:
        # Cambio: Usar RPC en lugar de insert directo
        response = supabase.rpc(
            "api_crear_categoria",
            {
                "p_id_usuario": str(user_id),
                "p_nombre": categoria.nombre,
                "p_color": categoria.color,
            },
        ).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"[ERROR] Failed to create categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creando categoría. Por favor intenta más tarde.",
        )


@router.put("/{categoria_id}", response_model=CategoriaRead)
async def update_categoria(
    categoria_id: UUID,
    categoria: CategoriaCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Actualizar una categoría existente.
    """
    try:
        # Cambio: Usar RPC en lugar de update directo
        response = supabase.rpc(
            "api_actualizar_categoria",
            {
                "p_id_categoria": str(categoria_id),
                "p_id_usuario": str(user_id),
                "p_nombre": categoria.nombre,
                "p_color": categoria.color,
            },
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada",
            )

        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando categoría. Por favor intenta más tarde.",
        )


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_categoria(
    categoria_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Eliminar una categoría.
    """
    try:
        # Cambio: Usar RPC en lugar de delete directo
        response = supabase.rpc(
            "api_eliminar_categoria",
            {"p_id_categoria": str(categoria_id), "p_id_usuario": str(user_id)},
        ).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando categoría. Por favor intenta más tarde.",
        )
