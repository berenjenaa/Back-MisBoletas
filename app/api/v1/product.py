# En app/api/v1/product.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging

from app.schemas.product import ProductRead, ProductCreate, ProductUpdate
from app.db.supabase import supabase_admin
from app.core.dependencies import get_current_user_id, get_active_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=List[ProductRead], summary="Listar mis productos")
async def get_products(
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtiene todos los productos del usuario autenticado (sin eliminados)."""
    try:
        response = (
            supabase_admin.get_table("productos")
            .select("*")
            .eq("id_usuario", str(user_id))
            .is_("fecha_eliminacion", "null")
            .execute()
        )
        productos = response.data or []
        return [ProductRead(**p) for p in productos]
    except Exception as e:
        error_msg = str(e)
        # Si es error de RLS (permission denied), retornar lista vacía
        if "permission denied" in error_msg.lower() or "42501" in error_msg:
            logger.warning(
                f"[WARNING] RLS blocked query - returning empty list: {error_msg}"
            )
            return []
        logger.error(f"[ERROR] Failed to list products: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener productos",
        )


@router.get(
    "/{product_id}", response_model=ProductRead, summary="Obtener un producto por ID"
)
async def get_product(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtiene un producto específico por ID."""
    try:
        response = (
            supabase_admin.get_table("productos")
            .select("*")
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .is_("fecha_eliminacion", "null")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )
        return ProductRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to read product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
        )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo producto",
)
async def create_product(
    product_data: ProductCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """Crea un nuevo producto."""
    try:
        payload = {
            "id_usuario": str(user_id),
            "nombre": product_data.nombre,
            "fecha_compra": (
                str(product_data.fecha_compra) if product_data.fecha_compra else None
            ),
            "duracion_garantia_meses": product_data.duracion_garantia_meses,
            "marca": product_data.marca,
            "modelo": product_data.modelo,
            "tienda": product_data.tienda,
            "notas": product_data.notas,
            "precio": int(product_data.precio) if product_data.precio else None,
        }

        response = supabase_admin.get_table("productos").insert(payload).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al crear producto",
            )
        return ProductRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear producto. Por favor intenta más tarde.",
        )


@router.put(
    "/{product_id}", response_model=ProductRead, summary="Actualizar un producto"
)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    user_id: UUID = Depends(get_active_user_id),
):
    """Actualiza un producto existente."""
    try:
        payload = {
            "nombre": product_data.nombre,
            "fecha_compra": (
                str(product_data.fecha_compra) if product_data.fecha_compra else None
            ),
            "duracion_garantia_meses": product_data.duracion_garantia_meses,
            "marca": product_data.marca,
            "modelo": product_data.modelo,
            "tienda": product_data.tienda,
            "notas": product_data.notas,
            "precio": int(product_data.precio) if product_data.precio else None,
        }

        response = (
            supabase_admin.get_table("productos")
            .update(payload)
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )
        return ProductRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar producto",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un producto (Soft Delete)",
)
async def delete_product(
    product_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """Realiza un Soft Delete de un producto."""
    try:
        from datetime import datetime

        response = (
            supabase_admin.get_table("productos")
            .update({"fecha_eliminacion": datetime.now().isoformat()})
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar producto",
        )
