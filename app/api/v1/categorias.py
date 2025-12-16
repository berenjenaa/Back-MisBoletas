from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from datetime import datetime, timezone
import logging
from collections import Counter  # ✅ Nueva importación para contar rápido

from app.core.dependencies import get_current_user_id, get_active_user_id
from app.db.supabase import supabase_admin
from app.schemas.categorias import (
    CategoriaBase,
    CategoriaCreate,
    CategoriaRead,
)

router = APIRouter(prefix="/categorias")
logger = logging.getLogger(__name__)


@router.get("", response_model=List[CategoriaRead])
async def get_categorias(user_id: UUID = Depends(get_current_user_id)):
    """
    Obtiene categorías con el conteo de productos.
    ⚡️ OPTIMIZADO: Reduce N+1 consultas a solo 2 consultas.
    """
    try:
        # 1. Obtener todas las categorías del usuario
        response = (
            supabase_admin.get_table("categorias")
            .select("*")
            .eq("id_usuario", str(user_id))
            .is_("fecha_eliminacion", "null")
            .execute()
        )

        categorias = response.data or []

        if not categorias:
            return []

        # 2. OPTIMIZACIÓN: Traer todas las relaciones de una sola vez
        # Extraemos los IDs de las categorías encontradas
        cat_ids = [c["id_categoria"] for c in categorias]

        if cat_ids:
            # Consultamos la tabla intermedia filtrando por TODOS los IDs a la vez
            # Solo traemos la columna 'id_categoria' para que sea ligero
            counts_response = (
                supabase_admin.get_table("producto_categorias")
                .select("id_categoria")
                .in_("id_categoria", cat_ids)
                .execute()
            )

            raw_counts = counts_response.data or []

            # 3. Contar en memoria (Python es muy rápido para esto)
            # Counter crea un diccionario: {'uuid-cat-1': 5, 'uuid-cat-2': 3...}
            conteo_map = Counter([item["id_categoria"] for item in raw_counts])

            # 4. Asignar el conteo a cada categoría
            for cat in categorias:
                cat["numero_productos"] = conteo_map.get(cat["id_categoria"], 0)
        else:
            # Si no hay categorías, no hay nada que contar
            for cat in categorias:
                cat["numero_productos"] = 0

        return [CategoriaRead(**c) for c in categorias]

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return []


@router.get("/{categoria_id}", response_model=CategoriaRead)
async def get_categoria(
    categoria_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtener una categoría específica.
    """
    try:
        response = (
            supabase_admin.get_table("categorias")
            .select("*")
            .eq("id_categoria", str(categoria_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )

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


# ✅ SIN BARRA AL FINAL (Standard REST)
@router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
async def create_categoria(
    categoria: CategoriaCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Crear una nueva categoría.
    """
    try:
        payload = {
            "id_usuario": str(user_id),
            "nombre": categoria.nombre,
            "color": categoria.color,
        }
        logger.info(f"[INFO] Creating categoria: {payload}")
        response = supabase_admin.get_table("categorias").insert(payload).execute()

        if not response.data or len(response.data) == 0:
            logger.error(f"[ERROR] Insert returned empty data: {response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando categoría. Por favor intenta más tarde.",
            )

        logger.info(f"[INFO] Categoria created: {response.data}")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"[ERROR] Failed to create categoria: {e}", exc_info=True)
        if "42501" in error_str or "permission denied" in error_str:
            logger.warning(f"[WARNING] RLS blocked categoria creation")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para crear categorías.",
            )
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
        response = (
            supabase_admin.get_table("categorias")
            .update({"nombre": categoria.nombre, "color": categoria.color})
            .eq("id_categoria", str(categoria_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )

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
    Eliminar una categoría (Soft Delete).
    """
    try:
        response = (
            supabase_admin.get_table("categorias")
            .update({"fecha_eliminacion": datetime.now(timezone.utc).isoformat()})
            .eq("id_categoria", str(categoria_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando categoría. Por favor intenta más tarde.",
        )
